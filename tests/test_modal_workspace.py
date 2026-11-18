import ast
import asyncio
import concurrent.futures
import importlib.util
import io
import json
import sys
import tempfile
import threading
import types
import unittest
import uuid
import wave
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

try:
    from fastapi import FastAPI
except ImportError:
    FastAPI = None

ROOT = Path(__file__).resolve().parents[1]


class Response:
    def __init__(self, messages):
        self.status_code = messages[0]["status"]
        self.body = b"".join(message.get("body", b"") for message in messages[1:])

    def json(self):
        return json.loads(self.body)

    def raise_for_status(self):
        if self.status_code != 200:
            raise RuntimeError(self.status_code, self.body)


class TestClient:
    def __init__(self, app, raise_server_exceptions=True):
        self.app = app
        self.raise_server_exceptions = raise_server_exceptions

    def request(self, method, path, json_data=None, content=b""):
        async def invoke():
            messages = []
            body = json.dumps(json_data).encode() if json_data is not None else content
            headers = [(b"content-length", str(len(body)).encode())]
            if json_data is not None:
                headers.append((b"content-type", b"application/json"))

            async def receive():
                return {"type": "http.request", "body": body}

            async def send(message):
                messages.append(message)

            scope = {"type": "http", "method": method, "path": path, "query_string": b"",
                     "headers": headers, "http_version": "1.1", "scheme": "http"}
            try:
                await self.app(scope, receive, send)
            except Exception:
                if self.raise_server_exceptions or not messages:
                    raise
            return Response(messages)
        return asyncio.run(invoke())

    def get(self, url):
        return self.request("GET", url)

    def post(self, url, json=None):
        return self.request("POST", url, json_data=json)

    def put(self, url, **kwargs):
        return self.request("PUT", url, **kwargs)


class Volume:
    def __init__(self):
        self.files = {}
        self.lock = threading.Lock()

    def read_file(self, name):
        try:
            yield self.files[name]
        except KeyError as error:
            raise FileNotFoundError(name) from error

    def remove_file(self, path):
        try:
            del self.files[path]
        except KeyError as error:
            raise FileNotFoundError(path) from error

    def listdir(self, directory):
        return [types.SimpleNamespace(path=path) for path in self.files if path.startswith(directory + "/")]

    @contextmanager
    def batch_upload(self):
        items = {}
        yield types.SimpleNamespace(put_file=lambda source, name: items.update({name: source.read()}))
        with self.lock:
            if self.files.keys() & items.keys():
                raise FileExistsError()
            self.files.update(items)


@unittest.skipIf(FastAPI is None, "Workspace HTTP dependencies unavailable")
class WorkspaceRoutes(unittest.TestCase):
    def setUp(self):
        self.volume = Volume()
        self.cancelled = []
        self.calls = []
        self.results = {}
        lock = threading.Lock()
        claims = {}

        def claim(key, value, skip_if_exists):
            self.assertTrue(skip_if_exists)
            with lock:
                if key in claims:
                    return False
                claims[key] = value
                return True
        self.claims = claims
        sdk = types.SimpleNamespace(
            Volume=types.SimpleNamespace(from_name=lambda *a, **k: self.volume),
            Dict=types.SimpleNamespace(from_name=lambda *a, **k: types.SimpleNamespace(put=claim, get=claims.get)),
            FunctionCall=types.SimpleNamespace(from_id=lambda id: types.SimpleNamespace(cancel=lambda: self.cancelled.append(id))),
            current_function_call_id=lambda: "fc-worker",
        )
        spec = importlib.util.spec_from_file_location("modal_workspace_for_test", ROOT / "modal_workspace.py")
        self.ws = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"modal": sdk, "modal.exception": types.SimpleNamespace(NotFoundError=FileNotFoundError)}):
            spec.loader.exec_module(self.ws)
        web = FastAPI()

        async def result(id):
            return self.results.get(id, {"status": "unknown"})

        def spawn(*args):
            self.calls.append(args)
            return types.SimpleNamespace(object_id="fc-submitted")

        self.ws.register(web, "transcription", 50 * 1024 * 1024, types.SimpleNamespace(spawn=spawn),
                         lambda job_id, options: (job_id, options), result)
        self.api = TestClient(web)
        self.job = str(uuid.uuid4())
        self.route = f"/workspace/jobs/{self.job}"
        self.stage = f"/workspace/stage/{self.job}"
        source = io.BytesIO()
        with wave.open(source, "wb") as wav:
            wav.setparams((1, 3, 8000, 0, "NONE", "not compressed"))
            wav.writeframes(b"\x00" * 3000)
        self.data = source.getvalue()
        self.sha = self.ws.digest(self.data)
        self.payload = {"size": len(self.data), "sha256": self.sha, "chunks": [self.sha],
                        "options": {"melody": True, "drums": False, "chords": False, "beat": False}}

    def test_stage_conflicts_and_bad_body(self):
        self.assertEqual(self.api.post(self.route, json=self.payload).status_code, 409)
        self.assertEqual(self.api.put(self.stage + f"/0/{self.sha}", content=b"bad").status_code, 400)
        for _ in range(2):
            self.assertEqual(self.api.put(self.stage + f"/0/{self.sha}", content=self.data).status_code, 200)
        self.assertEqual(self.api.get(self.stage).json(), {"chunks": [f"0-{self.sha}"]})
        other = self.data + b"other"
        self.assertEqual(self.api.put(self.stage + f"/0/{self.ws.digest(other)}", content=other).status_code, 409)
        self.assertEqual(self.calls, [])

    def test_reuses_staged_bytes_across_job_ids(self):
        upload = uuid.uuid5(uuid.NAMESPACE_URL, f"artist-workspace-audio:{self.sha}")
        self.api.put(f"/workspace/stage/{upload}/0/{self.sha}", content=self.data).raise_for_status()
        payload = self.payload | {"upload_id": str(upload)}
        for job_id in (self.job, str(uuid.uuid4())):
            self.api.post(f"/workspace/jobs/{job_id}", json=payload).raise_for_status()
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(len(self.volume.listdir(f"uploads/{upload}")), 1)

    def test_start_is_atomic_and_cancel_targets_recovered_worker(self):
        self.api.put(self.stage + f"/0/{self.sha}", content=self.data).raise_for_status()
        with concurrent.futures.ThreadPoolExecutor(2) as executor:
            responses = list(executor.map(lambda _: self.api.post(self.route, json=self.payload), range(2)))
        self.assertEqual([response.status_code for response in responses], [200, 200])
        self.assertEqual(self.calls, [(self.job, self.payload["options"])])
        self.assertEqual(self.api.get(self.route).json()["call_id"], "fc-submitted")
        self.claims.clear()
        self.api.post(self.route, json=self.payload).raise_for_status()
        self.assertEqual(len(self.calls), 1)
        changed = self.payload | {"options": self.payload["options"] | {"beat": True}}
        self.assertEqual(self.api.post(self.route, json=changed).status_code, 409)
        self.assertTrue(self.ws.start_worker("transcription", self.job))
        self.assertEqual(self.api.post(f"/workspace/cancel/{self.job}").json()["status"], "cancelled")
        self.assertEqual(self.cancelled, ["fc-worker"])
        self.results[self.job] = {"status": "partial", "files": ["melody.mid"]}
        self.assertEqual(self.api.get(self.route).json(), {
            "job_id": self.job, "status": "partial", "call_id": "fc-worker", "files": ["melody.mid"]})

    def test_ack_clears_only_this_verified_input(self):
        self.api.put(self.stage + f"/0/{self.sha}", content=self.data).raise_for_status()
        self.api.post(self.route, json=self.payload).raise_for_status()
        self.assertEqual(self.api.post(self.route + "/ack").status_code, 409)
        self.results[self.job] = {"status": "completed", "files": ["melody.mid"]}
        prefix = f"jobs/transcription/{self.job}"
        self.assertIn(f"{prefix}/input-{self.sha}.wav", self.volume.files)
        self.assertEqual(self.api.post(self.route + "/ack").json(), {"input_released": True})
        self.assertEqual(self.api.post(self.route + "/ack").json(), {"input_released": True})
        self.assertNotIn(f"{prefix}/input-{self.sha}.wav", self.volume.files)
        self.assertIn(f"{prefix}/reserved.json", self.volume.files)
        self.assertIn(f"uploads/{self.job}/0-{self.sha}", self.volume.files)

    def test_lost_ack_and_call_id_recovery(self):
        web = FastAPI()

        def lost(*args):
            self.calls.append(args)
            raise ConnectionError("remote accepted, response lost")

        async def result(id):
            return {}

        self.ws.register(web, "generation", 0, types.SimpleNamespace(spawn=lost),
                         lambda job_id, options: (job_id,), result)
        api = TestClient(web, raise_server_exceptions=False)
        payload = {"size": 0, "sha256": self.ws.digest(b""), "chunks": [],
                   "options": {"prompt": "test", "negative_prompt": "", "audio_length": 1,
                               "num_inference_steps": 10, "guidance_scale": 3, "output_format": "wav", "seed": 42}}
        self.assertEqual(api.post(self.route, json=payload).status_code, 500)
        self.assertEqual(api.post(self.route, json=payload).json()["status"], "submission_unknown")
        self.assertEqual(api.post(f"/workspace/cancel/{self.job}").json()["status"], "cancel_requested")
        self.assertFalse(self.ws.start_worker("generation", self.job))
        self.assertEqual(api.get(self.route).json()["status"], "cancelled")
        self.assertEqual(self.calls, [(self.job,)])


class TranscriptionTiming(unittest.TestCase):
    def test_click_uses_detected_tempo_and_map_tracks_variable_beats(self):
        try:
            from mido import MidiFile, tempo2bpm
        except ImportError:
            self.skipTest("MIDI dependency unavailable")
        # DSP test uses the actual functions without importing the cloud SDK.
        file = ROOT / "modal_app_transcription.py"
        tree = ast.parse(file.read_text())
        selected = {"create_click_track_midi", "create_tempo_map_midi"}
        tree.body = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in selected]
        functions = {}
        exec(compile(tree, str(file), "exec"), functions)
        with tempfile.TemporaryDirectory() as directory:
            click = Path(directory) / "click.mid"
            tempo_map = Path(directory) / "tempo.mid"
            beats = [0.25, 0.95, 1.60, 2.35]
            functions["create_click_track_midi"](beats, [beats[0]], 90, click)
            functions["create_tempo_map_midi"](beats, 90, tempo_map)
            midi = MidiFile(click)
            self.assertAlmostEqual(tempo2bpm(midi.tracks[0][0].tempo), 90, places=3)
            elapsed = 0
            actual = []
            for event in midi:
                elapsed += event.time
                if event.type == "note_on":
                    actual.append(elapsed)
            self.assertEqual(len(actual), len(beats))
            for measured, expected in zip(actual, beats):
                self.assertAlmostEqual(measured, expected, delta=0.001)
            midi = MidiFile(tempo_map)
            self.assertEqual([message.tempo for message in midi.tracks[0] if message.type == "set_tempo"],
                             [666667, 700000, 650000, 750000])
            self.assertAlmostEqual(midi.length, beats[-1], delta=0.001)


if __name__ == "__main__":
    unittest.main()
