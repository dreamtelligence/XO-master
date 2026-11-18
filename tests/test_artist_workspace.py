"""Local security, timing and workflow checks using generated audio only."""

import io
import json
import math
import sqlite3
import struct
import tempfile
import time
import unittest
import uuid
import wave
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from audio_core import engines
from studio.app import HostedWorkspace, create_app


def wav(rate=48000, duration=4):
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setparams((2, 2, rate, 0, "NONE", "not compressed"))
        samples = bytearray()
        for index in range(rate * duration):
            t = index / rate
            attack = 0.3 * math.exp(-60 * (t % (60 / 123))) * math.sin(2 * math.pi * 92 * t)
            samples += struct.pack("<hh", round(32767 * (0.18 * math.sin(2 * math.pi * 220 * t) + attack)),
                                   round(32767 * (0.16 * math.sin(2 * math.pi * 330 * t) + attack)))
        handle.writeframes(samples)
    return buffer.getvalue()


class WorkspaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = wav()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.root = root
        self.app = create_app(root / "project-store", root / "missing.json")
        self.client = TestClient(self.app, base_url="http://localhost:8765")
        self.client.__enter__()
        self.token = self.client.get("/api/session").json()["session"]
        self.headers = {"X-Workspace-Session": self.token}
        self.project = self.create()
        self.route = "/api/projects/" + self.project["id"]

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.temp.cleanup()

    def create(self):
        response = self.client.post("/api/projects", headers=self.headers, json={"name": "Grid 123", "bpm": 123})
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def upload(self, route=None, content=None, filename="Stereo.wav", role="original"):
        return self.client.post((route or self.route) + "/assets", headers=self.headers,
                                params={"filename": filename, "role": role},
                                content=self.fixture if content is None else content)

    def job(self, tool, inputs, params=None, key=None, state="completed"):
        request = {"id": key or str(uuid.uuid4()), "tool": tool, "inputs": inputs, "params": params or {}}
        response = self.client.post(self.route + "/runs", headers=self.headers, json=request)
        self.assertEqual(response.status_code, 202, response.text)
        job = response.json()["jobs"][0]
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            work = self.client.get(self.route).json()
            record = next(item for item in work["jobs"] if item["id"] == job)
            if record["state"] in {"completed", "failed", "partial", "cancelled"}:
                self.assertEqual(record["state"], state, record)
                return request, record, [item for item in work["assets"] if item["job"] == job]
            time.sleep(0.15)
        self.fail(f"{tool} did not finish")

    def test_loopback_csrf_isolation_and_format(self):
        for headers in ({"Host": "example.org"}, {"Origin": "https://example.org"}, {"Sec-Fetch-Site": "cross-site"}):
            self.assertEqual(self.client.get("/api/session", headers=headers).status_code, 403)
        self.assertEqual(self.client.post("/api/projects", json={}).status_code, 403)
        self.assertEqual(self.client.post("/api/credits", headers=self.headers, json={}).status_code, 410)
        self.assertEqual(self.client.get("/.git/config").status_code, 404)
        self.assertEqual(self.client.get("/api/modal/separation/health").status_code, 404)
        self.assertEqual(self.client.get("/api/capabilities").json()["tools"]["separation"], "needs_setup")
        self.assertEqual(self.upload(content=b"not audio").status_code, 422)

    def test_live_effect_changes_on_same_socket_and_ticket_is_single_use(self):
        if not self.client.get("/api/capabilities").json()["live_effects"]:
            self.skipTest("Pedalboard benötigt")
        asset = self.upload().json()
        path = self.route + "/assets/" + asset["id"] + "/fx-live"
        start = {"start": 0, "end": 4096, "position": 0, "chain": [{"effect": "Gain", "gain_db": 0}]}
        self.assertEqual(self.client.post(path, json=start).status_code, 403)
        session = self.client.post(path, headers=self.headers, json=start).raise_for_status().json()
        args = {"subprotocols": ["xo-fx", session["ticket"]]}
        with self.assertRaises(WebSocketDisconnect):
            with self.client.websocket_connect(session["url"], headers={"Origin": "https://other.example"}, **args):
                self.fail("Foreign origin redeemed a live ticket")
        headers = {"Origin": "http://localhost:8765"}
        with self.client.websocket_connect(session["url"], headers=headers, **args) as socket:
            self.assertEqual(socket.receive_json(), {"ready": True})
            socket.send_json({"loop": True})
            first = socket.receive_bytes()
            self.assertEqual(struct.unpack_from("<II", first), (0, 2048))
            self.assertEqual(first[8:8200], first[8200:])
            socket.send_json({"loop": True, "chain": [{"effect": "Gain", "gain_db": -12}]})
            second = socket.receive_bytes()
            self.assertEqual(struct.unpack_from("<II", second), (2048, 2048))
            dry, wet = struct.unpack_from("<4096h", second, 8), struct.unpack_from("<4096h", second, 8200)
            self.assertAlmostEqual(max(wet) / max(dry), 10 ** (-12 / 20), places=3)
            socket.send_json({"loop": True})
            self.assertEqual(struct.unpack_from("<II", socket.receive_bytes()), (0, 2048))
        with self.assertRaises(WebSocketDisconnect):
            with self.client.websocket_connect(session["url"], headers=headers, **args):
                self.fail("Live ticket reused")

    def test_compact_listening_windows_and_live_packets(self):
        import audioop

        asset = self.upload().json()
        path = self.route + "/assets/" + asset["id"]
        opus = self.client.get(path + "/window", params={"seconds": 1, "format": "opus"}).raise_for_status()
        self.assertEqual(opus.headers["content-type"], "audio/ogg")
        self.assertTrue(opus.content.startswith(b"OggS"))
        if not self.client.get("/api/capabilities").json()["live_effects"]:
            self.skipTest("Pedalboard benötigt")
        start = {"start": 0, "end": 4097, "position": 0, "codec": "adpcm", "chain": [{"effect": "Gain"}]}
        session = self.client.post(path + "/fx-live", headers=self.headers, json=start).raise_for_status().json()
        self.assertEqual(session["codec"], "adpcm")
        with self.client.websocket_connect(session["url"], headers={"Origin": "http://localhost:8765"},
                                           subprotocols=["xo-fx", session["ticket"]]) as socket:
            self.assertEqual(socket.receive_json(), {"ready": True})
            socket.send_json({"loop": False, "blocks": 3})
            batch = socket.receive_bytes()
            cursor = 0
            for expected_offset, expected in ((0, 2048), (2048, 2048), (4096, 1)):
                offset, count = struct.unpack_from("<II", batch, cursor)
                self.assertEqual(offset, expected_offset)
                stride = 3 + (count + 1) // 2
                size = 8 + 4 * stride
                packet = batch[cursor:cursor + size]
                cursor += size
                self.assertEqual(count, expected)
                stride = 3 + (count + 1) // 2
                self.assertEqual(len(packet), 8 + 4 * stride)
                channels = []
                for channel in range(4):
                    base = 8 + channel * stride
                    state = struct.unpack_from("<hB", packet, base)
                    data = packet[base + 3:base + stride]
                    samples, _ = audioop.adpcm2lin(data, 2, state)
                    channels.append(samples[:count * 2])
                self.assertEqual(channels[:2], channels[2:])
                if offset == 0:
                    self.assertGreater(audioop.max(channels[0], 2), 100)
            self.assertEqual(cursor, len(batch))
            socket.send_json({"loop": False})
            self.assertEqual(socket.receive_json(), {"end": True})

    def test_hosted_workspace_protects_reads_and_checkpoints_mutations(self):
        origin = "https://studio.example.test"
        password = "test_password_for_isolated_workspace_0123"
        catalog = self.root / "runtime" / "workspace.sqlite3"
        checkpoint = self.root / "snapshot.sqlite3"

        def backup(database):
            with sqlite3.connect(database) as active, sqlite3.connect(checkpoint) as snapshot:
                active.backup(snapshot)

        app = create_app(self.root / "online", self.root / "missing.json", hosted=HostedWorkspace(
            origin=origin, password=password, catalog=catalog, work=self.root / "scratch",
            plugins=self.root / "plugins", persist=backup,
        ))
        with TestClient(app, base_url=origin) as client:
            for path in ("/", "/favicon.png", "/api/projects", "/api/storage", "/api/session"):
                response = client.get(path)
                self.assertEqual(response.status_code, 401, path)
                self.assertIn("Basic", response.headers["WWW-Authenticate"])
            auth = ("studio", password)
            self.assertEqual(client.get("/api/projects", auth=("studio", "falsch")).status_code, 401)
            self.assertEqual(client.get("/api/projects", auth=auth, headers={"Origin": "https://other.example"}).status_code, 403)
            self.assertEqual(client.post("/api/projects", auth=auth, json={"name": "Titel"}).status_code, 403)
            token = client.get("/api/session", auth=auth).json()["session"]
            response = client.post("/api/projects", auth=auth, headers={"Origin": origin, "X-Workspace-Session": token}, json={"name": "Titel"})
            self.assertEqual(response.status_code, 201, response.text)
            self.assertEqual(response.headers["X-Robots-Tag"], "noindex, nofollow")
            with sqlite3.connect(checkpoint) as saved:
                self.assertEqual(saved.execute("SELECT name FROM projects").fetchone(), ("Titel",))
        self.assertEqual(self.upload(content=b"#EXTM3U\nfile:///etc/passwd\n").status_code, 422)
        asset = self.upload().json()
        other = self.create()
        self.assertEqual(self.client.get(f"/api/projects/{other['id']}/assets/{asset['id']}/audio").status_code, 404)
        audio = f"{self.route}/assets/{asset['id']}/audio"
        part = self.client.get(audio, headers={"Range": "bytes=0-31"})
        self.assertEqual((part.status_code, len(part.content)), (206, 32))
        self.assertIn("bytes 0-31/", part.headers["Content-Range"])
        self.assertEqual(self.client.get(audio, headers={"Range": "bytes=99999999-"}).status_code, 416)
        self.assertEqual(self.client.head(audio).headers["content-length"], str(len(self.fixture)))

    def test_job_history_hides_old_worker_diagnostics(self):
        asset = self.upload().json()
        _, job, _ = self.job("qa", [asset["id"]])
        self.app.state.store.update(job["id"], state="failed",
                                    error='python: File "/Users/ozi/private.py", line 6, in render')
        for route in (self.route, f"{self.route}/jobs/{job['id']}"):
            response = self.client.get(route)
            self.assertNotIn(b"/Users/ozi/", response.content)
            self.assertNotIn(b"python:", response.content)
            self.assertIn("Auftrag ist fehlgeschlagen", response.text)

    @unittest.skipUnless(engines.capabilities()["reference"], "Matchering fehlt")
    def test_reference_rejects_equal_audio_from_different_files(self):
        original = self.upload().json()
        reference = self.upload(content=self.fixture + b"JUNK\x04\x00\x00\x00test",
                                filename="Referenz.wav", role="reference").json()
        self.assertNotEqual(original["hash"], reference["hash"])
        _, job, _ = self.job("reference", [original["id"], reference["id"]], state="failed")
        self.assertEqual(job["error"], "Mix und Referenz enthalten dasselbe Audio. Wähle eine andere Referenzspur.")

    def test_import_cut_idempotency_cache_export_restore(self):
        response = self.upload()
        self.assertEqual(response.status_code, 201, response.text)
        asset = response.json()
        self.assertEqual((asset["meta"]["rate"], asset["meta"]["channels"], asset["meta"]["samples"]), (48000, 2, 192000))
        self.assertEqual(asset["id"], self.upload().json()["id"])
        project = self.client.patch(self.route, headers=self.headers, json={"name": "New name", "revision": 0}).json()
        self.assertEqual(project["revision"], 1)
        self.assertEqual(self.client.patch(self.route, headers=self.headers, json={"revision": 0}).status_code, 409)
        request, job, outputs = self.job("loop", [asset["id"]], {"start": 300, "end": 48300})
        rendered = outputs[0]
        self.assertEqual((rendered["role"], rendered["meta"]["samples"], rendered["meta"]["source_start"]), ("loop", 48000, 300))
        self.assertEqual(self.client.post(self.route + "/runs", headers=self.headers, json=request).json()["jobs"], [job["id"]])
        self.assertEqual(self.client.post(self.route + "/runs", headers=self.headers, json=request | {"params": {"end": 300}}).status_code, 409)
        _, reused, copies = self.job("loop", [asset["id"]], request["params"])
        self.assertIn("Vorhandenes", reused["phase"])
        self.assertEqual(rendered["hash"], copies[0]["hash"])
        _, _, checks = self.job("qa", [asset["id"]])
        self.assertIsInstance(checks[0]["meta"]["report"]["true_peak"], float)
        _, _, bundles = self.job("export", [asset["id"], rendered["id"]], {"format": "pcm24", "align": True})
        path = f"{self.route}/assets/{bundles[0]['id']}/download"
        package = self.client.get(path)
        with zipfile.ZipFile(io.BytesIO(package.content)) as file:
            data = json.loads(file.read("manifest.json"))
            self.assertEqual(data["format"], "pcm24")
            self.assertEqual(len(data["assets"]), 2)
            self.assertIsInstance(data["assets"][0]["qa"]["lufs"], float)
            exported = self.root / "export-check.wav"
            exported.write_bytes(file.read(data["assets"][0]["file"]))
            measure = engines.probe(exported)
            self.assertEqual((measure["channels"], measure["bits"]), (2, 24))
        _, _, backups = self.job("export", [asset["id"], rendered["id"]], {"package": True})
        bundle = self.client.get(f"{self.route}/assets/{backups[0]['id']}/download").content
        restore = self.client.post("/api/projects/import-package", headers=self.headers, content=bundle)
        self.assertEqual(restore.status_code, 201, restore.text)
        created = self.client.get("/api/projects/" + restore.json()["id"]).json()
        original = next(item for item in created["assets"] if item["role"] == "original")
        loop = next(item for item in created["assets"] if item["role"] == "loop")
        self.assertEqual(original["hash"], asset["hash"])
        self.assertEqual(loop["parents"], [original["id"]])
        broken = io.BytesIO()
        with zipfile.ZipFile(broken, "w") as bad:
            bad.writestr("../escape", b"unsafe")
        self.assertEqual(self.client.post("/api/projects/import-package", headers=self.headers,
                                          content=broken.getvalue()).status_code, 422)

    def test_recipe_snapshots_and_uses_preceding_asset(self):
        asset = self.upload().json()
        group = str(uuid.uuid4())
        request = {"id": group, "draft_revision": 0, "inputs": [asset["id"]],
                   "steps": [{"tool": "loop", "params": {"start": 200, "end": 48200}},
                             {"tool": "qa", "feed": "result"}]}
        route = self.route + "/recipe-runs"
        submit = self.client.post(route, headers=self.headers, json=request)
        self.assertEqual(submit.status_code, 202, submit.text)
        first, second = submit.json()["jobs"]
        self.assertEqual(first, group)
        self.assertEqual(self.client.post(route, headers=self.headers, json=request).json()["jobs"], [first, second])
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            result = self.client.get(self.route).json()
            latest = next(job for job in result["jobs"] if job["id"] == second)
            if latest["state"] in {"completed", "failed"}:
                self.assertEqual(latest["state"], "completed", latest)
                loop = next(item for item in result["assets"] if item["job"] == first)
                check = next(item for item in result["assets"] if item["job"] == second)
                self.assertEqual(check["parents"], [loop["id"]])
                self.assertEqual(latest["snapshot"]["inputs"][0]["sha256"], loop["hash"])
                break
            time.sleep(.15)
        else:
            self.fail("Recipe did not finish")

    def test_restart_preserves_import_and_original_bytes(self):
        asset = self.upload().json()
        self.client.__exit__(None, None, None)
        self.client = TestClient(create_app(self.root / "project-store", self.root / "missing.json"), base_url="http://localhost:8765")
        self.client.__enter__()
        response = self.client.get(f"{self.route}/assets/{asset['id']}/audio")
        self.assertEqual(response.content, self.fixture)

    def test_effect_audition_preserves_source_bounds_and_tail(self):
        if not engines.capabilities()["effects"]:
            self.skipTest("Pedalboard benötigt")
        asset = self.upload().json()
        start, end, tail = 12000, 108000, 1.5
        _, _, previews = self.job("effects", [asset["id"]], {
            "preview": True, "start": start, "end": end, "tail": tail,
            "chain": [{"effect": "Delay", "mix": .4}],
        })
        preview = previews[0]
        self.assertEqual(preview["parents"], [asset["id"]])
        self.assertEqual((preview["meta"]["source_start"], preview["meta"]["source_end"]), (start, end))
        self.assertEqual(preview["meta"]["samples"], end - start + round(tail * asset["meta"]["rate"]))
        self.assertEqual(len(preview["meta"]["comparison_lufs"]), 2)

        for invalid in ("ChowTape", "/tmp/Unbekannt.vst3"):
            response = self.client.post(self.route + "/runs/validate", headers=self.headers, json={
                "id": str(uuid.uuid4()), "tool": "effects", "inputs": [asset["id"]],
                "params": {"chain": [{"effect": invalid}]},
            })
            self.assertEqual(response.status_code, 422, response.text)

    def test_key_detection_and_same_tempo_transposition(self):
        available = engines.capabilities()
        if not available["samples"] or not available["rubberband"]:
            self.skipTest("librosa und Rubber Band benötigt")
        import numpy as np

        rate = 22050
        t = np.arange(2 * rate) / rate
        envelope = np.minimum(1, 80 * np.minimum(t, 2 - t))

        def progression(chords):
            return np.concatenate([envelope * sum((0.14 if i == 0 else 0.08) * np.sin(2 * np.pi * 261.625565 * 2 ** (note / 12) * t)
                                                 for i, note in enumerate(notes)) for notes in chords])

        minor = progression(((-15, -3, 0, 4), (-10, 2, 5, 9), (-8, 4, 8, 11), (-15, -3, 0, 4)))
        self.assertEqual(engines.estimate_key(minor, rate), {"tonic": 9, "mode": "minor"})
        self.assertIsNone(engines.estimate_key(np.zeros(2 * rate), rate))
        major = progression(((-12, 0, 4, 7), (-7, 5, 9, 12), (-5, 7, 11, 14), (-12, 0, 4, 7)))
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as handle:
            handle.setparams((1, 2, rate, 0, "NONE", "not compressed"))
            handle.writeframes((major * 32767).astype("<i2").tobytes())
        asset = self.upload(content=buffer.getvalue(), filename="Kadenz.wav").json()
        _, _, reports = self.job("detect", [asset["id"]], {"mode": "key"})
        source_key = reports[0]["meta"]["report"]["key"]
        self.assertEqual(source_key, {"tonic": 0, "mode": "major"})
        _, _, variants = self.job("stretch", [asset["id"]], {"pitch": 2, "source_key": source_key})
        render = variants[0]
        target = {"tonic": 2, "mode": "major"}
        self.assertEqual(render["meta"]["key"], target)
        self.assertEqual(render["meta"]["samples"], asset["meta"]["samples"])
        self.assertEqual(render["parents"], [asset["id"]])
        _, _, reports = self.job("detect", [render["id"]], {"mode": "key"})
        self.assertEqual(reports[0]["meta"]["report"]["key"], target)

    def test_cut_mapping_and_selected_local_engines(self):
        asset = self.upload().json()
        _, _, cuts = self.job("cut", [asset["id"]], {"cuts": [{"start": 100, "end": 500}]})
        self.assertEqual(cuts[0]["meta"]["samples"], 191600)
        self.assertEqual(cuts[0]["meta"]["edit_map"][1], {"source_start": 500, "source_end": 192000, "result_start": 100})
        _, _, bounced = self.job("mix", [asset["id"]], {"tracks": {asset["id"]: {"offset": 480, "gain": -3}}})
        self.assertEqual(bounced[0]["meta"]["samples"], 192480)
        if engines.capabilities()["rubberband"]:
            _, _, stretched = self.job("stretch", [asset["id"]], {"source_bpm": 123, "target_bpm": 150, "pitch": 2})
            self.assertEqual(stretched[0]["meta"]["samples"], 157440)
            self.assertEqual(stretched[0]["meta"]["channels"], 2)
        if engines.capabilities()["effects"]:
            _, _, rendered = self.job("effects", [asset["id"]], {"chain": [{"effect": "Gain", "gain_db": -6}, {"effect": "Delay", "bypass": True}]})
            self.assertEqual(rendered[0]["meta"]["bits"], 32)
            self.assertAlmostEqual(rendered[0]["meta"]["sample_peak"], asset["meta"]["sample_peak"] - 6, places=1)
        if engines.capabilities()["midi"]:
            target = self.root / "known.mid"
            engines.write_midi(target, {"tracks": [{"program": 0, "drums": False, "name": "Bass",
                                                     "notes": [[.20, .83, 52, 92]], "bends": [[.40, 100]]}]},
                               123, "6/8", {"ratio": 123/150, "transpose": 2})
            view = engines.notes_from_file(target)
            self.assertAlmostEqual(view["tempo"][0][1], 123, places=2)
            self.assertEqual(view["signatures"][0], [0.0, 6, 8])
            self.assertEqual(view["tracks"][0]["notes"][0][2], 54)
            self.assertAlmostEqual(view["tracks"][0]["notes"][0][0], .20 * 123/150, places=3)


if __name__ == "__main__":
    unittest.main()
