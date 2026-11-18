"""Private SQLite catalog and transactional workspace queue."""

import contextlib
import fcntl
import hashlib
import json
import os
import re
import shutil
import sqlite3
import tempfile
import threading
import time
import uuid
import zipfile
from pathlib import Path

from audio_core import engines
from studio import modal_adapter

MIB = 1024 ** 2
MAX_UPLOAD = 512 * MIB
BUDGET = 5120 * MIB
RESERVE = 2048 * MIB
KINDS = {"original", "reference", "stem", "variant", "loop", "oneshot", "midi", "take", "analysis", "export"}
AUDIO = KINDS - {"midi", "analysis", "export"}
TOOLS = {
    "qa": "ffmpeg", "detect": "samples", "loop": "ffmpeg", "oneshot": "ffmpeg", "stretch": "rubberband",
    "effects": "effects", "reference": "reference", "basic_pitch": "basic_pitch", "midi": "midi", "mix": "ffmpeg",
    "deepfilter": "deepfilter", "rnnoise": "rnnoise", "audiosr": "audiosr", "cut": "ffmpeg", "export": "ffmpeg",
    **{key: key for key in modal_adapter.ROUTES},
}
TERMINAL = {"completed", "partial", "failed", "cancelled", "submission_unknown", "output_unconfirmed"}
SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, rate INTEGER NOT NULL, bpm REAL NOT NULL, meter TEXT NOT NULL,
    purpose TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 0, archived INTEGER NOT NULL DEFAULT 0,
    draft TEXT NOT NULL DEFAULT '{}', updated REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS assets (
    id TEXT PRIMARY KEY, project TEXT NOT NULL REFERENCES projects(id), name TEXT NOT NULL,
    role TEXT NOT NULL, hash TEXT NOT NULL, suffix TEXT NOT NULL, meta TEXT NOT NULL,
    parents TEXT NOT NULL, job TEXT REFERENCES jobs(id), created REAL NOT NULL,
    hidden INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS assets_project ON assets(project, created);
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY, project TEXT NOT NULL REFERENCES projects(id), tool TEXT NOT NULL, inputs TEXT NOT NULL,
    params TEXT NOT NULL, snapshot TEXT NOT NULL, request_hash TEXT NOT NULL, cache_key TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'queued', phase TEXT NOT NULL DEFAULT 'Wartet', progress INTEGER,
    remote_id TEXT, call_id TEXT, cancel_requested INTEGER NOT NULL DEFAULT 0,
    error TEXT, retries INTEGER NOT NULL DEFAULT 0, retry_at REAL NOT NULL DEFAULT 0, created REAL NOT NULL, updated REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS jobs_project ON jobs(project, created);
CREATE INDEX IF NOT EXISTS jobs_queue ON jobs(state, created);
CREATE INDEX IF NOT EXISTS jobs_cache ON jobs(project, cache_key, state);
CREATE TABLE IF NOT EXISTS job_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT, job TEXT NOT NULL REFERENCES jobs(id), state TEXT NOT NULL,
    phase TEXT NOT NULL, created REAL NOT NULL
);
"""


class Problem(ValueError):
    def __init__(self, message, status=422, code="invalid"):
        super().__init__(message)
        self.status, self.code = status, code


def jsonstr(data):
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def hexhash(data):
    return hashlib.sha256(jsonstr(data).encode()).hexdigest()


def filehash(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def record(row):
    if row is None:
        raise Problem("Eintrag in diesem Projekt nicht gefunden.", 404, "not_found")
    result = dict(row)
    for key in ("draft", "meta", "parents", "params", "inputs", "snapshot"):
        if key in result:
            result[key] = json.loads(result[key])
    return result


def name(value, fallback="Unbenannt"):
    return "".join(char for char in str(value) if char.isprintable() and char not in "/\\").strip()[:140] or fallback


def data_path():
    return Path.home() / "Library/Application Support/Dreamtelligence XO"


class Store:
    def __init__(self, root, config, *, start=True):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.root.chmod(0o700)
        for dirname in ("blobs", "listen", "work"):
            (root / dirname).mkdir(mode=0o700, exist_ok=True)
        self.lock = (root / "workspace.lock").open("a")
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.lock.close()
            raise RuntimeError("Für dieses Datenverzeichnis läuft bereits ein Workspace.")
        self.config = config
        self.engines = engines.capabilities() | {
            service: bool(config and service in config["services"]) for service in modal_adapter.ROUTES
        }
        self.code_hash = hexhash({source.name: filehash(source) for source in (
            Path(__file__), Path(engines.__file__), Path(modal_adapter.__file__))})
        self.stop = threading.Event()
        self.threads = []
        with self.db() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            schema_version = conn.execute("PRAGMA user_version").fetchone()[0]
            if schema_version > 2:
                raise RuntimeError("Der lokale Katalog wurde mit einer neueren Workspace-Version erstellt.")
            if schema_version == 1:
                backup = sqlite3.connect(self.root / "workspace-v1-backup.sqlite3")
                try:
                    conn.backup(backup)
                finally:
                    backup.close()
            conn.executescript(SCHEMA)
            columns = {row["name"] for row in conn.execute("PRAGMA table_info(jobs)")}
            for key, definition in (("retries", "INTEGER"), ("retry_at", "REAL")):
                if key not in columns:
                    conn.execute(f"ALTER TABLE jobs ADD COLUMN {key} {definition} NOT NULL DEFAULT 0")
            conn.execute("PRAGMA user_version=2")
            conn.execute("""
                UPDATE jobs SET state='queued', phase=CASE WHEN phase='Cloud-Start gesendet' THEN phase ELSE 'Nach Neustart wieder aufgenommen' END
                WHERE state IN ('running','offline','finalizing')
            """)
        if start:
            for cloud in (False, True):
                thread = threading.Thread(target=self.worker, args=(cloud,), daemon=True)
                thread.start()
                self.threads.append(thread)

    @contextlib.contextmanager
    def db(self):
        conn = sqlite3.connect(self.root / "workspace.sqlite3", timeout=10)
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def close(self):
        self.stop.set()
        for thread in self.threads:
            thread.join(timeout=1)
        if not any(thread.is_alive() for thread in self.threads):
            self.lock.close()

    def usage(self, kind=None):
        if kind is None:
            return self.usage("blobs") + self.usage("listen")
        return sum(stat.st_size for file in (self.root / kind).iterdir() if (stat := self.file_stat(file)))

    @staticmethod
    def file_stat(file):
        try:
            return file.stat()
        except FileNotFoundError:
            return None

    def clear_listen(self):
        for file in (self.root / "listen").glob("*.mp3"):
            file.unlink(missing_ok=True)
        return self.usage("listen")

    def limit_listen(self):
        limit = 1024 * MIB
        amount = self.usage("listen")
        if amount > limit:
            candidates = [(stat.st_mtime, stat.st_size, path) for path in (self.root / "listen").glob("*.mp3")
                          if (stat := self.file_stat(path))]
            for _, length, path in sorted(candidates):
                if amount <= limit:
                    break
                path.unlink(missing_ok=True)
                amount -= length

    def require_space(self, size):
        if shutil.disk_usage(self.root).free - size < RESERVE or self.usage() + size > BUDGET:
            raise Problem("Speicherlimit erreicht. Prüfe das Projektbudget und den freien Speicher.", 413, "storage_limit")

    def projects(self):
        with self.db() as conn:
            return [record(row) for row in conn.execute("SELECT * FROM projects ORDER BY archived,updated DESC")]

    def create(self, data):
        id = str(uuid.uuid4())
        rate = data.get("rate", 48000)
        meter = data.get("meter", "4/4")
        purpose = data.get("purpose", "private")
        self.project_settings(rate, meter, purpose)
        bpm = engines.number(data.get("bpm", 120), 30, 300, "BPM")
        template = data.get("template", "empty")
        if template not in ("empty", "remix", "mix", "speech", "generate"):
            raise Problem("Unbekannte Projektvorlage.")
        with self.db() as conn:
            conn.execute("""
                INSERT INTO projects(id,name,rate,bpm,meter,purpose,draft,updated) VALUES(?,?,?,?,?,?,?,?)
            """, (id, name(data.get("name", "Neues Projekt")), rate, bpm, meter, purpose,
                  jsonstr({"template": template, "template_version": 1, "downbeat": 0}), time.time()))
        return self.project(id)

    @staticmethod
    def project_settings(rate, meter, purpose):
        if rate not in (44100, 48000) or meter not in ("2/4", "3/4", "4/4", "5/4", "6/8", "7/8", "9/8", "12/8") or purpose not in ("private", "release"):
            raise Problem("Projekt benötigt eine gültige Rate, Taktart und Nutzung.")

    def project(self, id):
        with self.db() as conn:
            return record(conn.execute("SELECT * FROM projects WHERE id=?", (id,)).fetchone())

    def patch(self, id, data):
        self.project(id)
        with self.db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            current = record(conn.execute("SELECT * FROM projects WHERE id=?", (id,)).fetchone())
            if data["revision"] != current["revision"]:
                raise Problem("Das Projekt wurde seit der letzten Ansicht geändert.", 409, "revision")
            rate, meter, purpose = (data.get(key, current[key]) for key in ("rate", "meter", "purpose"))
            self.project_settings(rate, meter, purpose)
            draft = data.get("draft", current["draft"])
            if not isinstance(draft, dict) or len(jsonstr(draft)) > MIB:
                raise Problem("Entwurf ist ungültig oder zu groß.")
            engines.number(draft.get("downbeat", 0), 0, 1800, "Erster Downbeat")
            conn.execute("""UPDATE projects SET name=?, rate=?, bpm=?, meter=?, purpose=?, archived=?, draft=?,
                         revision=revision+1, updated=? WHERE id=?""",
                         (name(data.get("name", current["name"])), rate,
                          engines.number(data.get("bpm", current["bpm"]), 30, 300, "BPM"), meter, purpose,
                          int(bool(data.get("archived", current["archived"]))), jsonstr(draft), time.time(), id))
        return self.project(id)

    def duplicate(self, id):
        original = self.project(id)
        target = self.create(original | {"name": original["name"] + " – Kopie"})
        with self.db() as conn:
            rows = [record(row) for row in conn.execute("SELECT * FROM assets WHERE project=?", (id,))]
            ids = {asset["id"]: str(uuid.uuid4()) for asset in rows}
            # User drafts can contain asset references. Restore them through the same ID mapping.
            def remap(value):
                if isinstance(value, dict):
                    return {ids.get(k, k): remap(v) for k, v in value.items()}
                if isinstance(value, list):
                    return [remap(v) for v in value]
                return ids.get(value, value) if isinstance(value, str) else value
            for asset in rows:
                conn.execute("""INSERT INTO assets(id,project,name,role,hash,suffix,meta,parents,created,hidden)
                             VALUES(?,?,?,?,?,?,?,?,?,?)""",
                             (ids[asset["id"]], target["id"], asset["name"], asset["role"], asset["hash"], asset["suffix"],
                              jsonstr(remap(asset["meta"])), jsonstr(remap(asset["parents"])), asset["created"], asset["hidden"]))
            conn.execute("UPDATE projects SET draft=? WHERE id=?", (jsonstr(remap(original["draft"])), target["id"]))
        return self.project(target["id"])

    def contents(self, id):
        project = self.project(id)
        with self.db() as conn:
            assets = [record(row) for row in conn.execute("SELECT * FROM assets WHERE project=? ORDER BY created DESC", (id,))]
            jobs = [record(row) for row in conn.execute("SELECT * FROM jobs WHERE project=? ORDER BY created DESC", (id,))]
        return {"project": project, "assets": assets, "jobs": jobs}

    def asset(self, project, id):
        with self.db() as conn:
            return record(conn.execute("SELECT * FROM assets WHERE id=? AND project=?", (id, project)).fetchone())

    def job(self, project, id):
        with self.db() as conn:
            return record(conn.execute("SELECT * FROM jobs WHERE id=? AND project=?", (id, project)).fetchone())

    def asset_patch(self, project, id, data):
        asset = self.asset(project, id)
        role = data.get("role") or asset["role"]
        if role != asset["role"] and (asset["role"], role) not in {("take", "variant"), ("reference", "original"), ("original", "reference")}:
            raise Problem("Diese Materialrolle kann hier nicht geändert werden.")
        with self.db() as conn:
            conn.execute("UPDATE assets SET name=?, role=?, hidden=? WHERE id=? AND project=?",
                         (name(data.get("name", asset["name"])), role, int(bool(data.get("hidden", asset["hidden"]))), id, project))
        return self.asset(project, id)

    def path(self, asset, preview=False):
        key = asset["hash"]
        if not re.fullmatch(r"[a-f0-9]{64}", key):
            raise Problem("Dateireferenz ungültig.", 404)
        return (self.root / "listen" / f"{key}.mp3") if preview else (self.root / "blobs" / key)

    def prepare(self, path, role, provenance, cancelled=lambda: False):
        digest = filehash(path)
        suffix = path.suffix.lower()
        meta = dict(provenance)
        if role in AUDIO:
            project_offset = meta.get("project_offset", 0)
            engines.integer(project_offset, 0, 48000 * 1800, "Projekt-Offset")
            measured = engines.probe(path)
            # Renaming an uploaded manifest to .wav cannot activate a file demuxer.
            accepted = {"wav", "aiff", "flac", "mp3", "aac", "ogg", "mov", "mp4", "m4a", "3gp", "3g2", "mj2", "matroska", "webm"}
            if not set(measured["container"].split(",")) & accepted:
                raise Problem("Audio-Container wird nicht unterstützt.")
            suffix = {"wav": ".wav", "aiff": ".aiff", "flac": ".flac", "mp3": ".mp3", "ogg": ".ogg",
                      "aac": ".aac", "mov": ".m4a", "matroska": ".webm"}.get(measured["container"].split(",")[0], ".audio")
            preview = path.parent / f"{digest}-preview.mp3"
            engines.peaks_and_listen(path, preview, measured, cancelled)
            meta |= measured
            if not (self.root / "listen" / f"{digest}.mp3").exists():
                self.require_space(preview.stat().st_size)
                os.replace(preview, self.root / "listen" / f"{digest}.mp3")
                self.limit_listen()
        elif role == "midi" and self.engines["midi"]:
            meta["midi"] = engines.notes_from_file(path)
        elif role == "analysis" and suffix == ".json" and path.stat().st_size <= 2 * MIB:
            meta["report"] = json.loads(path.read_text())
        destination = self.root / "blobs" / digest
        if not destination.exists():
            self.require_space(path.stat().st_size)
            os.replace(path, destination)
        return digest, suffix, meta

    def insert(self, conn, project, display, role, prepared, parents=(), job=None):
        digest, suffix, meta = prepared
        id = str(uuid.uuid4())
        conn.execute("""INSERT INTO assets(id,project,name,role,hash,suffix,meta,parents,job,created)
                     VALUES(?,?,?,?,?,?,?,?,?,?)""",
                     (id, project, name(display), role, digest, suffix, jsonstr(meta), jsonstr(parents), job, time.time()))
        return id

    def import_audio(self, project_id, path, filename, role):
        project = self.project(project_id)
        if project["archived"]:
            raise Problem("Archivierte Projekte können zuerst wieder aktiviert werden.", 409)
        if role not in ("original", "reference"):
            raise Problem("Importrolle muss Material oder Referenz sein.")
        prepared = self.prepare(path, role, {"engine": "Import"})
        with self.db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            duplicate = conn.execute("SELECT * FROM assets WHERE project=? AND hash=? AND role=? AND hidden=0",
                                     (project_id, prepared[0], role)).fetchone()
            if duplicate:
                return record(duplicate) | {"duplicate": True}
            id = self.insert(conn, project_id, filename, role, prepared)
        return self.asset(project_id, id)

    def validate(self, project, tool, ids, params):
        if project["archived"]:
            raise Problem("Archivierte Projekte können zuerst wieder aktiviert werden.", 409)
        if tool not in TOOLS or not self.engines[TOOLS[tool]]:
            raise Problem("Dieses Werkzeug benötigt eine konfigurierte Engine.", 503, "engine_unavailable")
        if project["purpose"] == "release" and tool in modal_adapter.ROUTES:
            raise Problem("Die Cloud-Modelle sind im Projektprofil Veröffentlichung für diesen Stand nicht freigegeben.", 422, "license_restricted")
        limit = 256 if tool == "export" else 24
        if len(ids) != len(set(ids)) or len(ids) > limit:
            raise Problem(f"Bitte höchstens {limit} unterschiedliche Assets angeben.")
        assets = [self.asset(project["id"], id) for id in ids]
        roles = [asset["role"] for asset in assets]
        if tool == "generation":
            if roles:
                raise Problem("Text-zu-Audio benötigt einen Prompt als Eingang.")
            if not isinstance(params.get("prompt"), str) or not 1 <= len(params["prompt"].strip()) <= 800:
                raise Problem("Der Prompt benötigt 1–800 Zeichen.")
        elif not assets:
            raise Problem("Bitte zuerst passendes Projektmaterial auswählen.")
        elif tool == "midi" and roles != ["midi"]:
            raise Problem("Bitte genau eine MIDI-Datei auswählen.")
        elif tool == "reference" and (len(roles) != 2 or roles[0] not in AUDIO or roles[1] != "reference"):
            raise Problem("Bitte Mix und eine Referenzspur auswählen.")
        elif tool == "stretch" and (roles[0] not in AUDIO or any(role not in AUDIO | {"midi"} for role in roles)):
            raise Problem("Bitte Audio und optional dazugehöriges MIDI auswählen.")
        elif tool == "mix" and any(role not in AUDIO for role in roles):
            raise Problem("Ein Mix benötigt ausschließlich Audiospuren.")
        elif tool not in ("midi", "export", "stretch", "mix", "reference") and (len(roles) != 1 or roles[0] not in AUDIO):
            raise Problem("Dieses Werkzeug benötigt genau eine Audiodatei.")
        if tool == "generation":
            engines.number(params.get("seconds", 8), 1, 47, "Dauer")
            engines.integer(params.get("steps", 50), 10, 100, "Schritte")
            engines.number(params.get("guidance", 7), 1, 12, "Guidance")
            if params.get("seed") is not None:
                engines.integer(params["seed"], 0, 2147483647, "Seed")
            if not isinstance(params.get("negative", ""), str) or len(params.get("negative", "")) > 800:
                raise Problem("Negativprompt benötigt höchstens 800 Zeichen.")
        if tool in ("loop", "oneshot", "cut"):
            regions = params.get("cuts") if tool == "cut" else params.get("regions", [params])
            if not isinstance(regions, list) or not 1 <= len(regions) <= 128 or not all(isinstance(x, dict) for x in regions):
                raise Problem("Bitte 1–128 gültige Regionen auswählen.")
            for choice in regions:
                engines.region(assets[0]["meta"], choice)
        if tool == "stretch":
            for key, label in (("source_bpm", "Quelltempo"), ("target_bpm", "Zieltempo")):
                engines.number(params.get(key, project["bpm"]), 30, 300, label)
            engines.number(params.get("pitch", 0), -12, 12, "Halbtöne")
        if tool == "mastering":
            engines.number(params.get("lufs", -14), -30, -8, "LUFS-Ziel")
            engines.number(params.get("true_peak", -1), -6, -0.1, "True-Peak-Grenze")
        if tool == "reference" and assets[0]["hash"] == assets[1]["hash"]:
            raise Problem("Mix und Referenz müssen unterschiedliche Audiodateien sein.")
        if tool == "audiosr" and not params.get("preview"):
            raise Problem("AudioSR benötigt eine ausdrücklich gewählte Auswahl bis 15 Sekunden.")
        if params.get("preview") and assets and roles[0] in AUDIO:
            a, b = engines.region(assets[0]["meta"], params)
            limit = 15 if tool == "audiosr" else 30
            if (b - a) / assets[0]["meta"]["rate"] > limit + 0.001:
                raise Problem(f"Bitte eine Vorschau von maximal {limit} Sekunden auswählen.")
        estimated = sum(asset["meta"].get("samples", 0) * asset["meta"].get("channels", 0) * 4
                        for asset in assets)
        self.require_space(max(10 * MIB, estimated * (7 if tool == "separation" else 3)))
        return assets

    def enqueue(self, project_id, request):
        project = self.project(project_id)
        ids, tool, params = request["inputs"], request["tool"], request["params"]
        key = request["id"]
        count = request.get("count", 1)
        if not 1 <= count <= (3 if tool == "generation" else 1):
            raise Problem("Ein Generierungsbatch enthält höchstens drei Takes.")
        digest = hexhash({"tool": tool, "inputs": ids, "params": params, "count": count, "draft_revision": request.get("draft_revision")})
        group = [key] + [str(uuid.uuid5(uuid.UUID(key), str(i))) for i in range(1, count)]
        with self.db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            prior = conn.execute("SELECT project,request_hash FROM jobs WHERE id=?", (key,)).fetchone()
            if prior:
                if prior["project"] != project_id or prior["request_hash"] != digest:
                    raise Problem("Auftrags-ID wurde bereits für einen anderen Auftrag verwendet.", 409, "idempotency")
                return group
            project = record(conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone())
            if request.get("draft_revision") not in (None, project["revision"]):
                raise Problem("Die Projektrevision hat sich geändert. Bitte neu laden.", 409, "revision")
            assets = self.validate(project, tool, ids, params)
            snapshots = [{"id": item["id"], "sha256": item["hash"], "role": item["role"]} for item in assets]
            if tool == "generation":
                if params.get("seed") is None:
                    params = params | {"seed": uuid.uuid4().int % (2 ** 31 - 3)}
                engines.integer(params["seed"], 0, 2 ** 31 - count, "Seed")
            for i, job_id in enumerate(group):
                effective = params if tool != "generation" else params | {"seed": params["seed"] + i}
                key_hash = self.cache_key(tool, snapshots, effective, project)
                conn.execute("""INSERT INTO jobs(id,project,tool,inputs,params,snapshot,request_hash,cache_key,created,updated)
                             VALUES(?,?,?,?,?,?,?,?,?,?)""",
                             (job_id, project_id, tool, jsonstr(ids), jsonstr(effective),
                              jsonstr({"project": project, "inputs": snapshots}), digest, key_hash, time.time(), time.time()))
                conn.execute("INSERT INTO job_events(job,state,phase,created) VALUES(?,?,?,?)",
                             (job_id, "queued", "Wartet", time.time()))
        return group

    def enqueue_recipe(self, project_id, request):
        key, steps, initial = request["id"], request["steps"], request["inputs"]
        ids = [key] + [str(uuid.uuid5(uuid.UUID(key), str(index))) for index in range(1, len(steps))]
        digest = hexhash({"recipe": request})
        with self.db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            current = conn.execute("SELECT project,request_hash FROM jobs WHERE id=?", (key,)).fetchone()
            if current:
                if current["project"] != project_id or current["request_hash"] != digest:
                    raise Problem("Auftrags-ID wurde bereits für einen anderen Auftrag verwendet.", 409, "idempotency")
                return ids
            project = record(conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone())
            if request["draft_revision"] != project["revision"]:
                raise Problem("Die Projektrevision hat sich geändert. Bitte neu laden.", 409, "revision")
            if not 2 <= len(steps) <= 8:
                raise Problem("Eine Bearbeitungsfolge enthält 2–8 Schritte.")
            for step in steps:
                tool = step["tool"]
                if tool not in TOOLS or not self.engines[TOOLS[tool]]:
                    raise Problem(f"Für {tool} fehlt eine konfigurierte Engine.", 503, "engine_unavailable")
                if tool in modal_adapter.ROUTES and project["purpose"] != "private":
                    raise Problem("Diese Cloud-Engine ist nur im privaten Profil freigegeben.")
            for index, (job_id, step) in enumerate(zip(ids, steps)):
                tool = step["tool"]
                params = step["params"]
                if tool == "generation" and params.get("seed") is None:
                    params = params | {"seed": uuid.uuid4().int % (2 ** 31 - 3)}
                inputs = ([] if tool == "generation" else initial) + step["extra_inputs"] if not index else []
                inputs = list(dict.fromkeys(inputs))
                assets = self.validate(project, tool, inputs, params) if not index else []
                references = [{"id": item["id"], "sha256": item["hash"], "role": item["role"]} for item in assets]
                snapshot = {"project": project, "inputs": references, "recipe": key}
                if index:
                    snapshot |= {"dependency": ids[index - 1], "feed": step["feed"], "output": step["output"],
                                 "initial": initial, "extra_inputs": step["extra_inputs"]}
                phase = "Wartet auf vorherigen Schritt" if index else "Wartet"
                state = "blocked" if index else "queued"
                cache_key = self.cache_key(tool, references, params, project)
                now = time.time()
                conn.execute("""INSERT INTO jobs(id,project,tool,inputs,params,snapshot,request_hash,
                             cache_key,state,phase,created,updated) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                             (job_id, project_id, tool, jsonstr(inputs), jsonstr(params), jsonstr(snapshot), digest,
                              cache_key, state, phase, now, now))
                conn.execute("INSERT INTO job_events(job,state,phase,created) VALUES(?,?,?,?)",
                             (job_id, state, phase, now))
        return ids

    def cache_key(self, tool, references, params, project):
        return hexhash({"schema": 1, "code": self.code_hash, "tool": tool, "inputs": references, "params": params,
                        "rate": project["rate"], "bpm": project["bpm"], "meter": project["meter"]})

    def advance_recipes(self, conn):
        ready = conn.execute("""
            SELECT child.*, parent.state AS dependency_state, parent.inputs AS dependency_inputs,
                   parent.cancel_requested AS dependency_cancelled
            FROM jobs child JOIN jobs parent ON parent.id=json_extract(child.snapshot,'$.dependency')
            WHERE child.state='blocked' AND parent.state IN ('completed','partial','failed','cancelled',
                                                             'submission_unknown','output_unconfirmed')
            ORDER BY child.created
        """).fetchall()
        for row in ready:
            job = record(row)
            snapshot = job["snapshot"]
            state, phase, error = "queued", "Vorheriger Schritt übernommen", None
            inputs = []
            if job["dependency_cancelled"] or job["dependency_state"] == "cancelled":
                state, phase = "cancelled", "Vorheriger Schritt abgebrochen"
            elif job["dependency_state"] not in ("completed", "partial"):
                state, phase, error = "failed", "Vorheriger Schritt nicht verfügbar", "Bearbeitungsfolge am Fehler angehalten."
            else:
                try:
                    if job["tool"] != "generation":
                        feed = snapshot["feed"]
                        if feed == "initial":
                            inputs = snapshot["initial"]
                        elif feed == "input":
                            inputs = json.loads(job["dependency_inputs"])
                        else:
                            candidates = [record(candidate) for candidate in conn.execute(
                                "SELECT * FROM assets WHERE project=? AND job=? ORDER BY created",
                                (job["project"], snapshot["dependency"]))]
                            candidates = [item for item in candidates if item["role"] not in {"analysis", "export"}
                                          and (not snapshot["output"] or item["name"] == snapshot["output"])]
                            if len(candidates) != 1:
                                raise Problem("Der vorherige Schritt braucht eine eindeutige Ausgabedatei für diesen Eingang.")
                            inputs = [candidates[0]["id"]]
                    inputs = list(dict.fromkeys(inputs + snapshot["extra_inputs"]))
                    assets = self.validate(snapshot["project"], job["tool"], inputs, job["params"])
                    snapshot["inputs"] = [{"id": item["id"], "sha256": item["hash"], "role": item["role"]} for item in assets]
                except (ValueError, KeyError, TypeError) as problem:
                    state, phase, error = "failed", "Eingang der Bearbeitungsfolge fehlt", str(problem)[:400]
            now = time.time()
            conn.execute("""UPDATE jobs SET state=?, phase=?, error=?, inputs=?, snapshot=?, cache_key=?,updated=? WHERE id=?""",
                         (state, phase, error, jsonstr(inputs), jsonstr(snapshot),
                          self.cache_key(job["tool"], snapshot["inputs"], job["params"], snapshot["project"]), now, job["id"]))
            conn.execute("INSERT INTO job_events(job,state,phase,created) VALUES(?,?,?,?)", (job["id"], state, phase, now))

    def cancel(self, project, id):
        self.job(project, id)
        with self.db() as conn:
            conn.execute("""UPDATE jobs SET cancel_requested=1,state=CASE WHEN state IN ('blocked','queued') AND remote_id IS NULL
                         AND phase!='Cloud-Start gesendet' THEN 'cancelled' ELSE state END, updated=?
                         WHERE project=? AND id=? AND state IN ('blocked','queued','running','offline','finalizing')""", (time.time(), project, id))
        return self.job(project, id)

    def reconcile(self, project, id):
        job = self.job(project, id)
        if job["tool"] not in modal_adapter.ROUTES or not (job["remote_id"] or job["state"] == "submission_unknown"):
            raise Problem("Für diesen Auftrag fehlt eine Cloud-Referenz.", 409, "no_remote_job")
        with self.db() as conn:
            cursor = conn.execute("""UPDATE jobs SET state='queued', retries=0, retry_at=0, error=NULL,
                                     phase=CASE WHEN remote_id IS NULL THEN 'Cloud-Start gesendet' ELSE 'Cloud-Status wird abgeglichen' END, updated=?
                                     WHERE id=? AND project=? AND state IN ('failed','submission_unknown','output_unconfirmed')""",
                                  (time.time(), id, project))
            if not cursor.rowcount:
                raise Problem("Dieser Auftrag wird bereits verarbeitet oder ist abgeschlossen.", 409, "not_reconcilable")
        return self.job(project, id)

    def update(self, id, **data):
        with self.db() as conn:
            current = conn.execute("SELECT state,phase FROM jobs WHERE id=?", (id,)).fetchone()
            conn.execute("UPDATE jobs SET " + ",".join(f"{key}=?" for key in data) + ",updated=? WHERE id=?",
                         (*data.values(), time.time(), id))
            state, phase = (data.get(key, current[key]) for key in ("state", "phase"))
            if (state, phase) != (current["state"], current["phase"]):
                conn.execute("INSERT INTO job_events(job,state,phase,created) VALUES(?,?,?,?)", (id, state, phase, time.time()))

    def worker(self, cloud):
        cloud_tools = tuple(modal_adapter.ROUTES)
        while not self.stop.is_set():
            with self.db() as conn:
                conn.execute("BEGIN IMMEDIATE")
                self.advance_recipes(conn)
                sql = "IN" if cloud else "NOT IN"
                row = conn.execute(f"""SELECT * FROM jobs WHERE state IN ('queued','offline') AND retry_at<=? AND tool {sql}
                                    ({','.join('?' for _ in cloud_tools)}) ORDER BY created LIMIT 1""",
                                   (time.time(), *cloud_tools)).fetchone()
                if row:
                    conn.execute("UPDATE jobs SET state='running',updated=? WHERE id=?", (time.time(), row["id"]))
            if not row:
                self.stop.wait(0.35)
                continue
            job = record(row)
            try:
                self.execute(job, cloud)
            except (modal_adapter.SubmissionUnknown, modal_adapter.OutputUnconfirmed) as error:
                state = "submission_unknown" if isinstance(error, modal_adapter.SubmissionUnknown) else "output_unconfirmed"
                self.update(job["id"], state=state, error=str(error), progress=None)
            except engines.Cancelled:
                if not self.stop.is_set():
                    self.update(job["id"], state="cancelled", phase="Abgebrochen", progress=None)
            except (ConnectionError, TimeoutError) as error:
                current = self.job(job["project"], job["id"])
                retries = current["retries"] + 1
                if retries <= 3:
                    self.update(job["id"], state="offline", retries=retries, retry_at=time.time() + 2 ** (retries + 1),
                                error=str(error)[:400])
                else:
                    if current["remote_id"]:
                        state, phase = "output_unconfirmed", "Cloud-Ausgabe unbestätigt"
                    elif current["phase"] == "Cloud-Start gesendet":
                        state, phase = "submission_unknown", "Cloud-Start unbestätigt"
                    else:
                        state, phase = "failed", "Transfer nicht abgeschlossen"
                    self.update(job["id"], state=state, phase=phase, error=str(error)[:400], progress=None)
            except Exception as error:
                message = str(error).replace(str(self.root), "[lokaler Speicher]")[:500]
                self.update(job["id"], state="failed", phase="Verarbeitung fehlgeschlagen",
                            error=message or type(error).__name__, progress=None)

    def execute(self, job, cloud):
        id, project_id, tool, params = (job[key] for key in ("id", "project", "tool", "params"))
        project = job["snapshot"]["project"]
        def cancelled():
            return self.job(project_id, id)["cancel_requested"] or (self.stop.is_set() and not cloud)
        inputs = []
        for expected in job["snapshot"]["inputs"]:
            asset = self.asset(project_id, expected["id"])
            if asset["hash"] != expected["sha256"]:
                raise Problem("Eingangsversion wurde verändert.")
            inputs.append((self.path(asset), asset))
        if not cloud and tool != "export" and self.cached(job, cancelled):
            return
        with tempfile.TemporaryDirectory(dir=self.root / "work", prefix=id + "-") as tmp:
            directory = Path(tmp)
            partial = {}
            if cloud:
                def publish(**data):
                    if data.get("state") == "partial":
                        partial.update(data)
                        self.update(id, state="finalizing", phase="Teilergebnisse werden lokal geprüft")
                    else:
                        self.update(id, **data)
                outputs = modal_adapter.render(self.config, job, inputs, directory, publish, cancelled, project)
            else:
                if cancelled():
                    raise engines.Cancelled()
                self.update(id, phase="Lokaler Render", error=None)
                outputs = (self.export(inputs, params, project, directory, cancelled) if tool == "export"
                           else self.render_local(job, inputs, directory, cancelled))
            results = []
            for file, role, provenance in outputs:
                if self.stop.is_set() or (not cloud and cancelled()):
                    raise engines.Cancelled()
                display = file.name
                provenance = provenance | {"operation": {"tool": tool, "parameters": params,
                                                           "workspace_revision": project["revision"],
                                                           "code": self.code_hash}}
                prepared = self.prepare(file, role, provenance, cancelled if not cloud else lambda: self.stop.is_set())
                results.append((display, role, prepared))
            if not results:
                raise Problem("Der Auftrag hat keine verwendbaren Ergebnisse erzeugt.")
            with self.db() as conn:
                conn.execute("BEGIN IMMEDIATE")
                row = conn.execute("SELECT state,cancel_requested FROM jobs WHERE id=?", (id,)).fetchone()
                if row["cancel_requested"] and not cloud:
                    raise engines.Cancelled()
                for display, role, prepared in results:
                    self.insert(conn, project_id, display, role, prepared, job["inputs"], id)
                state = "partial" if partial else "completed"
                phase = "Teilergebnisse gespeichert" if state == "partial" else "Ergebnisse gespeichert"
                conn.execute("UPDATE jobs SET state=?, phase=?, error=?, progress=100, updated=? WHERE id=?",
                             (state, phase, partial.get("error"), time.time(), id))
                conn.execute("INSERT INTO job_events(job,state,phase,created) VALUES(?,?,?,?)", (id, state, phase, time.time()))
            if cloud:
                try:
                    modal_adapter.acknowledge(self.config, tool, self.job(project_id, id))
                except modal_adapter.CloudHTTPError as error:
                    if error.status not in (404, 405):
                        self.update(id, phase=phase + " · Cloud-Eingabe noch nicht freigegeben")
                except ConnectionError:
                    self.update(id, phase=phase + " · Cloud-Eingabe noch nicht freigegeben")

    def cached(self, job, cancelled):
        with self.db() as conn:
            previous = conn.execute("""SELECT id FROM jobs WHERE project=? AND cache_key=? AND state='completed'
                                       ORDER BY updated DESC LIMIT 1""", (job["project"], job["cache_key"])).fetchone()
            if not previous:
                return False
            assets = [record(row) for row in conn.execute("SELECT * FROM assets WHERE job=?", (previous["id"],))]
        if not assets or any(not self.path(item).is_file() or filehash(self.path(item)) != item["hash"] for item in assets):
            return False
        if cancelled():
            raise engines.Cancelled()
        with self.db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            if conn.execute("SELECT cancel_requested FROM jobs WHERE id=?", (job["id"],)).fetchone()[0]:
                raise engines.Cancelled()
            for asset in assets:
                self.insert(conn, job["project"], asset["name"], asset["role"],
                            (asset["hash"], asset["suffix"], asset["meta"]), job["inputs"], job["id"])
            conn.execute("UPDATE jobs SET state='completed', phase=?, progress=100, updated=? WHERE id=?",
                         ("Vorhandenes, geprüftes Ergebnis übernommen", time.time(), job["id"]))
            conn.execute("INSERT INTO job_events(job,state,phase,created) VALUES(?,?,?,?)",
                         (job["id"], "completed", "Vorhandenes, geprüftes Ergebnis übernommen", time.time()))
        return True

    def render_local(self, job, inputs, directory, cancelled):
        import sys
        description = directory / "work.json"
        description.write_text(jsonstr({"tool": job["tool"], "inputs": [[str(path), asset] for path, asset in inputs],
                                        "params": job["params"], "project": job["snapshot"]["project"]}))
        raw, _ = engines.run([sys.executable, "-m", "studio.worker", description], cancelled)
        outputs = json.loads(raw)
        for filename, role, metadata in outputs:
            yield Path(filename), role, metadata

    def export(self, inputs, params, project, directory, cancelled):
        fmt = params.get("format", "pcm24")
        formats = {"pcm16": "pcm_s16le", "pcm24": "pcm_s24le", "float32": "pcm_f32le", "mp3": "libmp3lame"}
        if fmt not in formats:
            raise Problem("Unbekanntes Exportformat.")
        aligned = params.get("align", True)
        package = bool(params.get("package"))
        rate = project["rate"]
        tracks = [asset for _, asset in inputs if asset["role"] in AUDIO - {"reference"} and not asset["meta"].get("compact")]
        tempos = {asset["meta"].get("bpm", project["bpm"]) for _, asset in inputs if asset["role"] in (AUDIO - {"reference"}) | {"midi"}}
        if aligned and not package and len(tempos) > 1:
            raise Problem("Die Auswahl enthält verschiedene BPM. Passe die Zeitbasis an oder exportiere ohne Ausrichtung.")
        common = max((round(a["meta"]["samples"] * rate / a["meta"]["rate"]) + a["meta"].get("project_offset", 0)
                      for a in tracks), default=0)
        payload = {"schema": 1, "type": "workspace" if package else "daw",
                   "project": {key: project[key] for key in ("name", "rate", "bpm", "meter", "purpose", "draft")},
                   "aligned": bool(aligned and not package), "format": fmt, "assets": []}
        archive = directory / f"{name(project['name'])} – {'Projekt' if package else 'DAW'}.zip"
        with zipfile.ZipFile(archive, "w", allowZip64=True) as zip_file:
            for index, (source, asset) in enumerate(inputs, 1):
                if cancelled():
                    raise engines.Cancelled()
                if asset["role"] == "export" or (asset["role"] == "reference" and not package):
                    continue
                metadata = asset["meta"]
                audio = asset["role"] in AUDIO
                suffix = asset["suffix"] if package or not audio else ".mp3" if fmt == "mp3" else ".wav"
                archive_name = f"audio/{index:02d}_{name(Path(asset['name']).stem)}{suffix}"
                metrics, export_format = None, None
                if audio and not package:
                    output = directory / f"export-{index}{suffix}"
                    filters = [f"aresample={rate}"]
                    if fmt in ("pcm16", "pcm24"):
                        output_bits = 16 if fmt == "pcm16" else 24
                        filters = [f"aresample={rate}:dither_method=triangular:output_sample_bits={output_bits}"]
                    if aligned and asset in tracks:
                        filters += [f"adelay={metadata.get('project_offset',0)}S:all=1", f"apad=whole_len={common}", f"atrim=end_sample={common}"]
                    engines.ffmpeg("-i", source, "-af", ",".join(filters), "-c:a", formats[fmt], output, cancelled=cancelled)
                    export_format = engines.probe(output)
                    metrics = engines.qa(output, cancelled)
                    target = metadata.get("target_true_peak")
                    limit_lufs = metadata.get("target_lufs")
                    warnings = []
                    if target is not None and (metrics["true_peak"] is None or metrics["true_peak"] > target + 0.2):
                        warnings.append("True-Peak-Ziel überschritten")
                    if limit_lufs is not None and (metrics["lufs"] is None or abs(metrics["lufs"] - limit_lufs) > 1):
                        warnings.append("LUFS-Ziel außerhalb ±1 LU")
                    if metrics["true_peak"] is not None and metrics["true_peak"] >= 0:
                        warnings.append("True Peak erreicht 0 dBTP")
                    metrics["warnings"] = warnings
                    if warnings and params.get("strict"):
                        raise Problem(f"{asset['name']}: " + ", ".join(warnings))
                    source = output
                zip_file.write(source, archive_name)
                payload["assets"].append({"id": asset["id"], "file": archive_name, "name": asset["name"],
                                          "role": asset["role"], "sha256": filehash(source), "meta": metadata,
                                          "parents": asset["parents"], "output": export_format, "qa": metrics})
            if not payload["assets"]:
                raise Problem("Im Exportkorb befindet sich kein verwendbares Asset.")
            zip_file.writestr("manifest.json", json.dumps(payload, ensure_ascii=False, indent=2))
            zip_file.writestr("ABLETON-LOGIC.txt", f"""Importe Audio und MIDI aus diesem Archiv.
Projekt: {project['bpm']:g} BPM, {project['meter']}, {rate} Hz.
Ausgerichtete Audiospuren starten gemeinsam an der DAW-Nullposition.
Loops sind kompakte Dateien. Quelloffset und tatsächlich gemessene Ausgabewerte stehen in manifest.json.
Beim Ausrichten in der DAW automatisches Warping/Flex gezielt prüfen.
""")
        yield archive, "export", {"engine": "FFmpeg / ZIP", "files": len(payload["assets"]),
                                  "qa_warnings": sum(len((entry["qa"] or {}).get("warnings", [])) for entry in payload["assets"])}

    def restore(self, path):
        try:
            with zipfile.ZipFile(path) as archive:
                self._check_package(archive)
                manifest = json.loads(archive.read("manifest.json"))
                if manifest.get("type") != "workspace" or manifest.get("schema") != 1:
                    raise Problem("Bitte ein Workspace-Projektpaket der Version 1 wählen.")
                items = manifest["assets"]
                if not isinstance(items, list) or not 1 <= len(items) <= 256:
                    raise Problem("Ungültige Anzahl Paketdateien.")
                settings = manifest["project"]
                self.project_settings(settings["rate"], settings["meter"], settings["purpose"])
                ids, ready = {}, []
                with tempfile.TemporaryDirectory(dir=self.root / "work") as tmp:
                    directory = Path(tmp)
                    used = set()
                    for index, item in enumerate(items):
                        entry = item["file"]
                        if entry in used or item["id"] in ids or not entry.startswith("audio/") or item["role"] not in KINDS - {"export"}:
                            raise Problem("Paket enthält mehrdeutige oder unzulässige Asset-Referenzen.")
                        used.add(entry)
                        suffix = Path(entry).suffix.lower()
                        if (item["role"] == "midi" and suffix != ".mid") or (item["role"] == "analysis" and suffix not in (".txt", ".json")):
                            raise Problem("Paket enthält einen ungültigen Artefakttyp.")
                        target = directory / (str(index) + suffix)
                        with archive.open(entry) as source, target.open("xb") as output:
                            shutil.copyfileobj(source, output, 1024 ** 2)
                        if filehash(target) != item["sha256"]:
                            raise Problem("Ein Datei-Hash im Projektpaket stimmt nicht überein.")
                        prepared = self.prepare(target, item["role"], item["meta"])
                        ids[item["id"]] = str(uuid.uuid4())
                        ready.append((item, prepared))
                    return self._restore_catalog(settings, ids, ready)
        except (zipfile.BadZipFile, KeyError, TypeError, AttributeError) as exc:
            raise Problem("Das Projektpaket ist unvollständig oder beschädigt.") from exc

    def _check_package(self, archive):
        import stat
        entries = archive.infolist()
        if len(entries) > 258 or len({entry.filename for entry in entries}) != len(entries):
            raise Problem("Projektpaket hat zu viele oder doppelte Dateien.")
        for entry in entries:
            parts = entry.filename.split("/")
            if (len(parts) > 2 or any(part in ("", ".", "..") for part in parts) or "\\" in entry.filename
                    or ":" in entry.filename or stat.S_ISLNK(entry.external_attr >> 16)
                    or entry.file_size > MAX_UPLOAD or (entry.flag_bits & 1)):
                raise Problem("Projektpaket enthält einen unzulässigen ZIP-Eintrag.")
        if archive.getinfo("manifest.json").file_size > 8 * MIB:
            raise Problem("Projektmanifest ist zu groß.")
        self.require_space(sum(entry.file_size for entry in entries) * 2)

    def _restore_catalog(self, settings, ids, ready):
        project_id = str(uuid.uuid4())
        def remap(value):
            if isinstance(value, dict):
                return {ids.get(key, key): remap(inner) for key, inner in value.items()}
            if isinstance(value, list):
                return [remap(inner) for inner in value]
            return ids.get(value, value) if isinstance(value, str) else value
        with self.db() as conn:
            conn.execute("""INSERT INTO projects(id,name,rate,bpm,meter,purpose,draft,updated)
                         VALUES(?,?,?,?,?,?,?,?)""",
                         (project_id, name(settings["name"]), settings["rate"],
                          engines.number(settings["bpm"], 30, 300, "BPM"), settings["meter"], settings["purpose"],
                          jsonstr(remap(settings.get("draft", {}))), time.time()))
            for item, (digest, suffix, meta) in ready:
                conn.execute("""INSERT INTO assets(id,project,name,role,hash,suffix,meta,parents,created)
                             VALUES(?,?,?,?,?,?,?,?,?)""",
                             (ids[item["id"]], project_id, name(item["name"]), item["role"], digest, suffix,
                              jsonstr(remap(meta)), jsonstr([ids[p] for p in item["parents"] if p in ids]), time.time()))
        return self.project(project_id)
