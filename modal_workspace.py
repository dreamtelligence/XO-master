"""Private workspace transfer and job control shared by all five Modal apps."""

import hashlib
import io
import json
import re
import subprocess
import tempfile
import uuid

import modal
from modal.exception import NotFoundError

CHUNK_SIZE = 4 * 1024 * 1024
TRACK_MAX_BYTES = 256 * 1024 * 1024
STAGING_PATH = "/workspace-staging"
staging = modal.Volume.from_name("artist-workspace-staging-v1", create_if_missing=True)
claims = modal.Dict.from_name("artist-workspace-claims-v1", create_if_missing=True)
HEX = re.compile("[a-f0-9]{64}")


def digest(value):
    return hashlib.sha256(value).hexdigest()


def read(path):
    try:
        return b"".join(staging.read_file(path))
    except (FileNotFoundError, NotFoundError):
        return None


def write(path, content):
    with staging.batch_upload() as batch:
        batch.put_file(io.BytesIO(content), path)


def receipt(prefix, key):
    value = read(f"{prefix}/{key}.json")
    return json.loads(value) if value is not None else None


def record(prefix, key, data):
    try:
        write(f"{prefix}/{key}.json", json.dumps(data, sort_keys=True).encode())
    except FileExistsError:
        existing = receipt(prefix, key)
        if existing != data:
            raise


def start_worker(tool, job_id):
    prefix = f"jobs/{tool}/{job_id}"
    record(prefix, "worker", {"call_id": modal.current_function_call_id()})
    if receipt(prefix, "cancel") is None:
        return True
    record(prefix, "cancelled", {"confirmed": True})
    return False


def load_input(source, destination, tool, job_id):
    """Legacy jobs still pass bytes. Workspace jobs pass an approved job reference."""
    if isinstance(source, bytes):
        destination.write_bytes(source)
        return True
    prefix = f"jobs/{tool}/{job_id}"
    if source != job_id or not start_worker(tool, job_id):
        return False
    ready = receipt(prefix, "ready")
    if not ready:
        raise RuntimeError("Staged audio has no ready receipt")
    sha = hashlib.sha256()
    received = 0
    with destination.open("wb") as output:
        for chunk in staging.read_file(f"{prefix}/input-{ready['sha256']}.wav"):
            sha.update(chunk)
            received += output.write(chunk)
    if received != ready["size"] or sha.hexdigest() != ready["sha256"]:
        destination.unlink()
        raise RuntimeError("Staged audio failed integrity verification")
    return True


def validate_options(tool, options):
    def bools(keys):
        if any(type(options[key]) is not bool for key in keys):
            raise ValueError("Boolean expected")

    if tool == "generation":
        for key, minimum, maximum in [("audio_length", 1, 47), ("num_inference_steps", 10, 100),
                                      ("guidance_scale", 1, 12), ("seed", 0, 2147483647)]:
            value = options[key]
            if type(value) not in (int, float) or not minimum <= value <= maximum:
                raise ValueError("Generation parameter out of bounds")
        if (type(options["seed"]) is not int or type(options["num_inference_steps"]) is not int
                or options["output_format"] != "wav" or not 1 <= len(options["prompt"].strip()) <= 800
                or len(options["negative_prompt"]) > 800):
            raise ValueError("Invalid generation options")
    elif tool == "audiosr":
        if options.keys() != {"seed"} or type(options["seed"]) is not int or not 0 <= options["seed"] <= 2147483647:
            raise ValueError("Invalid AudioSR seed")
    elif tool == "separation":
        bools(("use_tta", "extract_instrumental", "coherent"))
        if (not set(options["selected_stems"].split(",")) <= {"vocals", "drums", "bass", "other"}
                or options["coherent"] and options["extract_instrumental"]):
            raise ValueError("Invalid stems")
    elif tool == "mastering":
        bools(("bass_mono_making", "lufs_targeting"))
        if (options["mastering_intensity"] not in ("low", "medium", "high")
                or not set(options["output_formats"].split(",")) <= {"16bit", "24bit"}):
            raise ValueError("Invalid mastering selections")
    elif tool == "transcription":
        tasks = {"melody", "drums", "chords", "beat"}
        bools(tasks)
        if options.keys() != tasks or not any(options.values()):
            raise ValueError("Select at least one valid transcription task")
    elif tool == "enhancement":
        flags = json.loads(options["enhancement_options"])
        allowed = {"noise_reduction", "volume_normalization", "filler_word_removal",
                   "silence_trimming", "cough_click_removal", "quality_enhancement",
                   "loudness_targeting", "speech_suggestions", "disturbance_suggestions"}
        if (not isinstance(flags, dict) or flags.keys() not in (allowed, allowed - {"disturbance_suggestions"})
                or any(type(value) is not bool for value in flags.values())
                or any(flags[name] for name in ("silence_trimming", "filler_word_removal", "cough_click_removal"))):
            raise ValueError("Invalid enhancement selections")


def validate_audio(source):
    source.flush()
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=format_name:stream=codec_name,sample_rate,channels,duration_ts",
         "-of", "json", source.name],
        timeout=10, capture_output=True, check=True,
    )
    metadata = json.loads(probe.stdout)
    streams = metadata["streams"]
    if metadata["format"]["format_name"] != "wav" or len(streams) != 1:
        raise ValueError("Expected one WAV stream")
    stream = streams[0]
    rate = int(stream["sample_rate"])
    frames = int(stream["duration_ts"])
    if (stream["codec_name"] != "pcm_s24le" or not 8000 <= rate <= 192000
            or stream["channels"] not in (1, 2) or not 0 < frames <= rate * 1800):
        raise ValueError("Unsupported audio stream")
    source.seek(0)


def register(web_app, tool, max_size, worker, arguments, result_state):
    from fastapi import Body, HTTPException, Request

    def prefix(job_id):
        return f"jobs/{tool}/{job_id}"

    def state(job_id):
        job_path = prefix(job_id)
        reserved = receipt(job_path, "reserved")
        if reserved is None:
            return {"job_id": str(job_id), "status": "unknown", "call_id": None}
        worker_receipt = receipt(job_path, "worker")
        submitted = worker_receipt or receipt(job_path, "submitted")
        cancelled = receipt(job_path, "cancelled")
        cancel = cancelled or receipt(job_path, "cancel")
        status = ("cancelled" if cancelled else "cancel_requested" if cancel else
                  "processing" if worker_receipt else "queued" if submitted else "submission_unknown")
        return {"job_id": str(job_id), "status": status,
                "call_id": submitted["call_id"] if submitted else None}

    @web_app.get("/workspace/capabilities")
    def capabilities():
        return {"protocol": 1, "chunk_size": CHUNK_SIZE, "max_size": max_size}

    @web_app.get("/workspace/stage/{job_id}")
    def staged(job_id: uuid.UUID):
        try:
            return {"chunks": [item.path.rsplit("/", 1)[-1]
                               for item in staging.listdir(f"uploads/{job_id}")]}
        except (FileNotFoundError, NotFoundError):
            return {"chunks": []}

    @web_app.put("/workspace/stage/{job_id}/{index}/{sha256}")
    async def stage(job_id: uuid.UUID, index: int, sha256: str, request: Request):
        length = request.headers.get("Content-Length", "")
        if (not max_size or not 0 <= index < (max_size + CHUNK_SIZE - 1) // CHUNK_SIZE
                or not HEX.fullmatch(sha256) or not length.isdigit()
                or len(length) > 8 or not 1 <= int(length) <= CHUNK_SIZE):
            raise HTTPException(400, "Ungültiger Uploadteil")
        content = bytearray()
        async for part in request.stream():
            if len(part) + len(content) > int(length):
                raise HTTPException(400, "Uploadteil ist zu groß")
            content.extend(part)
        if len(content) != int(length) or digest(content) != sha256:
            raise HTTPException(400, "Uploadteil ist unvollständig oder beschädigt")
        from starlette.concurrency import run_in_threadpool

        def persist():
            directory = f"uploads/{job_id}"
            path = f"{directory}/{index}-{sha256}"
            if read(path) is not None:
                return
            try:
                existing = staging.listdir(directory)
            except (FileNotFoundError, NotFoundError):
                existing = []
            if any(item.path.rsplit("/", 1)[-1].startswith(f"{index}-") for item in existing):
                raise HTTPException(409, "Für diesen Index ist ein anderer Inhalt gespeichert")
            slot = f"{directory}/{index}"
            if not claims.put(slot, sha256, skip_if_exists=True) and claims.get(slot) != sha256:
                raise HTTPException(409, "Für diesen Index ist ein anderer Inhalt registriert")
            try:
                write(path, content)
            except FileExistsError:
                pass
        await run_in_threadpool(persist)
        return {"index": index, "sha256": sha256}

    @web_app.get("/workspace/jobs/{job_id}")
    async def job_state(job_id: uuid.UUID):
        from starlette.concurrency import run_in_threadpool

        control = await run_in_threadpool(state, job_id)
        if control["status"] == "unknown":
            return control
        try:
            result = await result_state(str(job_id))
        except HTTPException as error:
            if error.status_code != 404:
                raise
            result = {}
        if result.get("status") in ("completed", "partial", "error"):
            return control | result
        if control["status"] in ("cancelled", "cancel_requested"):
            return control
        if result.get("status") not in (None, "unknown"):
            return control | result
        return control

    @web_app.post("/workspace/jobs/{job_id}")
    def start(job_id: uuid.UUID, payload: dict = Body(...)):
        size = payload.get("size")
        parts = payload.get("chunks")
        sha = payload.get("sha256")
        options = payload.get("options")
        if (type(size) is not int or not (1 <= size <= max_size if max_size else size == 0)
                or not isinstance(parts, list) or len(parts) != (size + CHUNK_SIZE - 1) // CHUNK_SIZE
                or not all(isinstance(part, str) and HEX.fullmatch(part) for part in parts)
                or not isinstance(sha, str) or not HEX.fullmatch(sha) or not isinstance(options, dict)):
            raise HTTPException(400, "Ungültiger Auftragsinhalt")
        if not max_size and sha != digest(b""):
            raise HTTPException(400, "Unerwarteter Audioinhalt")
        try:
            validate_options(tool, options)
            args = arguments(str(job_id), options)
        except (AttributeError, KeyError, ValueError, TypeError) as error:
            raise HTTPException(400, "Ungültige Auftragsoptionen") from error
        upload_id = payload.get("upload_id", str(job_id))
        shared_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"artist-workspace-audio:{sha}"))
        if upload_id not in (str(job_id), shared_id):
            raise HTTPException(400, "Ungültige Upload-ID")
        job_path = prefix(job_id)
        request_hash = digest(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())
        reserved = receipt(job_path, "reserved")
        if reserved:
            if reserved["sha256"] != request_hash:
                raise HTTPException(409, "Auftrags-ID gehört zu einem anderen Auftrag")
            return state(job_id)
        if size and not receipt(job_path, "ready"):
            with tempfile.NamedTemporaryFile() as assembled:
                full_hash = hashlib.sha256()
                for index, part in enumerate(parts):
                    data = read(f"uploads/{upload_id}/{index}-{part}")
                    expected = min(CHUNK_SIZE, size - index * CHUNK_SIZE)
                    if data is None or len(data) != expected or digest(data) != part:
                        raise HTTPException(409, "Ein bestätigter Uploadteil fehlt")
                    full_hash.update(data)
                    assembled.write(data)
                if full_hash.hexdigest() != sha:
                    raise HTTPException(400, "Gesamtprüfsumme stimmt nicht")
                try:
                    validate_audio(assembled)
                except (ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
                    raise HTTPException(400, "Die WAVE-Eingabe überschreitet die Dienstgrenzen") from error
                try:
                    with staging.batch_upload() as batch:
                        batch.put_file(assembled, f"{job_path}/input-{sha}.wav")
                except FileExistsError:
                    pass
            try:
                record(job_path, "ready", {"sha256": sha, "size": size})
            except FileExistsError as error:
                raise HTTPException(409, "Auftrag hat bereits andere Eingabedaten") from error
        if size and receipt(job_path, "ready") != {"sha256": sha, "size": size}:
            raise HTTPException(409, "Auftrag hat bereits andere Eingabedaten")
        if not claims.put(job_path, request_hash, skip_if_exists=True):
            if claims.get(job_path) != request_hash:
                raise HTTPException(409, "Auftrags-ID gehört zu einem anderen Auftrag")
            return state(job_id)
        # A durable reservation remains even after the short-lived atomic claim expires.
        record(job_path, "reserved", {"sha256": request_hash})
        if receipt(job_path, "cancel") is None:
            invocation = worker.spawn(*args)
            record(job_path, "submitted", {"call_id": invocation.object_id})
        return state(job_id)

    @web_app.post("/workspace/jobs/{job_id}/ack")
    async def acknowledge(job_id: uuid.UUID):
        from starlette.concurrency import run_in_threadpool

        control = await run_in_threadpool(state, job_id)
        if control["status"] == "unknown":
            raise HTTPException(404, "Auftrag nicht gefunden")
        result = await result_state(str(job_id))
        if result.get("status") not in ("completed", "partial"):
            raise HTTPException(409, "Auftrag hat keine bestätigte Ausgabe")
        job_path = prefix(job_id)
        def release():
            if not receipt(job_path, "acknowledged"):
                ready = receipt(job_path, "ready")
                if ready:
                    try:
                        staging.remove_file(f"{job_path}/input-{ready['sha256']}.wav")
                    except (FileNotFoundError, NotFoundError):
                        pass
                record(job_path, "acknowledged", {"input_released": True})
        await run_in_threadpool(release)
        return {"input_released": True}

    @web_app.post("/workspace/cancel/{job_id}")
    def cancel(job_id: uuid.UUID):
        current = state(job_id)
        if current["status"] == "unknown":
            raise HTTPException(404, "Auftrag nicht gefunden")
        job_path = prefix(job_id)
        record(job_path, "cancel", {"requested": True})
        if current["call_id"] and current["status"] != "cancelled":
            modal.FunctionCall.from_id(current["call_id"]).cancel()
            record(job_path, "cancelled", {"confirmed": True})
        return state(job_id)
