"""Server-to-server adapter for the existing private audio apps."""
import hashlib
import http.client
import json
import re
import shutil
import time
import uuid
from urllib.parse import quote, urlsplit

from audio_core.engines import Cancelled, UserError, ffmpeg, integer, number, qa, render_selection

ROUTES = {
    "separation": ("/", "/status/{}", "/download/{}/final_stems", "audio_file"),
    "mastering": ("/master", "/status/mastering/{}", "/download/mastering/{}", "target_audio"),
    "transcription": ("/transcribe", "/status/transcription/{}", "/download/transcription/{}", "audio_file"),
    "enhancement": ("/upload/enhancement", "/status/enhancement/{}", "/download/enhancement/{}", "audio"),
    "generation": ("/", "/status/{}", "/download/{}/output", None),
    "audiosr": ("/", "/status/{}", "/download/{}/output", None),
}


class SubmissionUnknown(ValueError):
    pass


class OutputUnconfirmed(ValueError):
    pass


class CloudHTTPError(ValueError):
    def __init__(self, tool, status):
        self.status = status
        super().__init__(f"Privater Dienst {tool} meldet HTTP {status}.")


def call(config, tool, path, method="GET", fields=None, source=None, destination=None, body=None):
    host = urlsplit(config["services"][tool]).hostname
    headers = {"Modal-Key": config["token_id"], "Modal-Secret": config["token_secret"]}
    connection = http.client.HTTPSConnection(host, timeout=150)
    try:
        if fields is None:
            if body is not None:
                headers["Content-Type"] = "application/json" if isinstance(body, dict) else "application/octet-stream"
                if isinstance(body, dict):
                    body = json.dumps(body).encode()
            connection.request(method, path, body=body, headers=headers)
        else:
            boundary = uuid.uuid4().hex
            segments = [
                f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode()
                for key, value in fields.items()
            ]
            size = 0
            if source:
                segments.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{ROUTES[tool][3]}"; filename="input.wav"\r\nContent-Type: audio/wav\r\n\r\n'.encode())
                size = source.stat().st_size
            end = (b"\r\n" if source else b"") + f"--{boundary}--\r\n".encode()
            connection.putrequest(method, path)
            for key, value in headers.items():
                connection.putheader(key, value)
            connection.putheader("Content-Type", "multipart/form-data; boundary=" + boundary)
            connection.putheader("Content-Length", sum(map(len, segments)) + size + len(end))
            connection.endheaders()
            for segment in segments:
                connection.send(segment)
            if source:
                with source.open("rb") as file:
                    connection.send(file)
            connection.send(end)
        with connection.getresponse() as response:
            if response.status != 200:
                raise CloudHTTPError(tool, response.status)
            if destination:
                limit = 450 * 1024 * 1024
                with destination.open("wb") as file:
                    while chunk := response.read(65536):
                        limit -= len(chunk)
                        if limit < 0:
                            raise UserError("Das Cloud-Ergebnis ist zu groß.")
                        file.write(chunk)
                return None
            return json.loads(response.read(1024 * 1024))
    except (OSError, http.client.HTTPException) as error:
        raise ConnectionError(f"Der private Dienst {tool} ist vorübergehend nicht erreichbar.") from error
    finally:
        connection.close()


def workspace_capability(config, tool):
    try:
        info = call(config, tool, "/workspace/capabilities")
    except CloudHTTPError as error:
        if error.status not in (404, 405):
            raise
        return None
    if info.get("protocol") != 1 or not 256 * 1024 <= info.get("chunk_size", 0) <= 8 * 1024 * 1024:
        raise UserError("Der private Dienst meldet einen unbekannten Transfervertrag.")
    return info


def stage(config, tool, source, chunk_size, update, cancelled):
    sha = hashlib.sha256()
    chunks = []
    if not source:
        return {"size": 0, "chunks": chunks, "sha256": sha.hexdigest()}
    with source.open("rb") as file:
        while chunk := file.read(chunk_size):
            sha.update(chunk)
            chunks.append(hashlib.sha256(chunk).hexdigest())
    total = source.stat().st_size
    checksum = sha.hexdigest()
    upload_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"artist-workspace-audio:{checksum}"))
    route = f"/workspace/stage/{upload_id}"
    try:
        existing = set(call(config, tool, route)["chunks"])
        with source.open("rb") as file:
            for index, chunk_hash in enumerate(chunks):
                if cancelled():
                    raise Cancelled()
                chunk = file.read(chunk_size)
                if f"{index}-{chunk_hash}" not in existing:
                    call(config, tool, f"{route}/{index}/{chunk_hash}", "PUT", body=chunk)
                update(phase="Audio wird geschützt übertragen", progress=int(100 * file.tell() / total))
    except CloudHTTPError as error:
        if error.status < 500:
            raise
        raise ConnectionError("Upload wird mit den bereits bestätigten Teilen fortgesetzt.") from error
    return {"size": total, "chunks": chunks, "sha256": checksum, "upload_id": upload_id}


def render(config, job, inputs, directory, update, cancelled, project):
    tool, params = job["tool"], job["params"]
    upload, status_route, downloads, _ = ROUTES[tool]
    fields = {"workspace_job_id": job["id"]}
    wanted, source = set(), None
    if tool == "separation":
        stems = params.get("stems", ["vocals", "drums", "bass", "other"])
        if not isinstance(stems, list) or not stems or not set(stems) <= {"vocals", "drums", "bass", "other", "instrumental"}:
            raise UserError("Mindestens einen gültigen Stem auswählen.")
        wanted = {stem + ".wav" for stem in stems}
        fields |= {"selected_stems": ",".join(sorted(set(stems) - {"instrumental"})) or "vocals",
                   "use_tta": str(bool(params.get("tta"))).lower(),
                   "extract_instrumental": str("instrumental" in stems).lower(),
                   "coherent": str(bool(params.get("coherent")) and "instrumental" not in stems).lower()}
    if tool == "mastering":
        wanted = {"mastered_24bit.wav"}
        intensity = params.get("intensity", "medium")
        if intensity not in ("low", "medium", "high"):
            raise UserError("Ungültige Mastering-Intensität.")
        fields |= {"mastering_intensity": intensity, "output_formats": "24bit",
                   "bass_mono_making": "false", "lufs_targeting": "false"}
    if tool == "transcription":
        tasks = params.get("tasks", ["melody", "drums", "chords", "beat"])
        if not isinstance(tasks, list) or not tasks or not set(tasks) <= {"melody", "drums", "chords", "beat"}:
            raise UserError("Bitte passende Analysen auswählen.")
        fields |= {name: str(name in tasks).lower() for name in ("melody", "drums", "chords", "beat")}
    if tool == "enhancement":
        fields["enhancement_options"] = json.dumps({
            "noise_reduction": True, "volume_normalization": False, "filler_word_removal": False,
            "silence_trimming": False, "cough_click_removal": False, "quality_enhancement": False,
            "loudness_targeting": False, "speech_suggestions": bool(params.get("suggestions")),
            "disturbance_suggestions": bool(params.get("disturbances")),
        })
    if tool == "audiosr":
        fields["seed"] = integer(params.get("seed", 42), 0, 2147483647, "Seed")
        wanted = {"bandwidth.wav"}
    if tool == "generation":
        prompt = str(params.get("prompt", "")).strip()
        negative = str(params.get("negative", "")).strip()
        if not 1 <= len(prompt) <= 800 or len(negative) > 800:
            raise UserError("Prompt benötigt 1–800 Zeichen. Negativprompt maximal 800 Zeichen.")
        fields |= {"prompt": prompt, "negative_prompt": negative,
                   "audio_length": number(params.get("seconds", 8), 1, 47, "Dauer"),
                   "num_inference_steps": integer(params.get("steps", 50), 10, 100, "Schritte"),
                   "guidance_scale": number(params.get("guidance", 7), 1, 12, "Guidance"),
                   "seed": integer(params["seed"], 0, 2147483647, "Seed"), "output_format": "wav"}
        wanted = {"generated_audio.wav"}
    remote = job["remote_id"]
    recovered_start = job["phase"] == "Cloud-Start gesendet"
    modern = remote == job["id"]
    if not remote:
        capability = workspace_capability(config, tool)
        modern = capability is not None
        if recovered_start:
            if not modern:
                raise UserError("Cloud-Start unklar. Der Dienst kann den früheren Start nicht zuordnen.")
            recovered = call(config, tool, f"/workspace/jobs/{job['id']}")
            if recovered["status"] == "unknown":
                raise ConnectionError("Cloud-Start unklar. Der Auftrag wurde zur Vermeidung von Doppelstarts nicht wiederholt.")
            remote = job["id"]
            update(remote_id=remote, call_id=recovered["call_id"])
        else:
            if not modern and tool == "separation" and fields["coherent"] == "true":
                raise UserError("Die geschützte Separation unterstützt den SCNet-Modus nach dem Workspace-Update.")
            if tool == "audiosr" and not modern:
                raise UserError("AudioSR Basic benötigt den privaten Workspace-Dienst.")
            if inputs:
                source = directory / "input.wav"
                limit = capability["max_size"] if modern else (50 if tool == "mastering" else 100) * 1024 * 1024
                opts = (["-ar", 44100, "-ac", 2] if tool == "separation" else
                        ["-ar", 48000, "-ac", 1] if tool == "enhancement" else [])
                raw_input = inputs[0][0]
                if tool == "audiosr":
                    raw_input = directory / "Auswahl.wav"
                    render_selection(inputs[0][0], raw_input, inputs[0][1]["meta"], params, cancelled)
                    opts = ["-ar", 48000, "-ac", 1]
                ffmpeg("-i", raw_input, *opts, "-c:a", "pcm_s24le", source, cancelled=cancelled)
                if source.stat().st_size > limit:
                    raise UserError(f"Die konvertierte Datei überschreitet das Dienstlimit von {limit // (1024 * 1024)} MB.")
            if modern:
                payload = stage(config, tool, source, capability["chunk_size"], update, cancelled)
                payload["options"] = {
                    key: value == "true" if value in ("true", "false") and key not in ("prompt", "negative_prompt") else value
                    for key, value in fields.items() if key != "workspace_job_id"
                }
            if cancelled():
                raise Cancelled()
            update(phase="Cloud-Start gesendet", progress=None)
            try:
                start = (call(config, tool, f"/workspace/jobs/{job['id']}", "POST", body=payload)
                         if modern else call(config, tool, upload, "POST", fields, source))
                remote = str(uuid.UUID(start["job_id"]))
            except (ConnectionError, KeyError, ValueError) as error:
                if isinstance(error, CloudHTTPError) and error.status < 500:
                    raise
                if modern:
                    start = call(config, tool, f"/workspace/jobs/{job['id']}")
                    if start["status"] != "unknown":
                        remote = job["id"]
                if not remote:
                    raise ConnectionError("Cloud-Start wird über die Auftrags-ID geprüft.") from error
            update(remote_id=remote, call_id=start.get("call_id"), phase="Cloud-Auftrag angenommen")
    deadline = time.monotonic() + 2400
    poll_route = f"/workspace/jobs/{remote}" if modern else status_route.format(remote)
    while time.monotonic() < deadline:
        state = call(config, tool, poll_route)
        status = state["status"]
        if state.get("call_id"):
            update(call_id=state["call_id"])
        if status in ("completed", "partial"):
            break
        if status == "cancelled":
            raise Cancelled()
        if status == "error":
            raise UserError("Der private Dienst hat die Verarbeitung abgebrochen. Prüfe die Eingabe und versuche es erneut.")
        if cancelled():
            if modern:
                result = call(config, tool, f"/workspace/cancel/{remote}", "POST")
                if result["status"] == "cancelled":
                    raise Cancelled()
            else:
                update(cancel_requested=0, phase="Dieser Modal-Stand unterstützt keinen Einzelabbruch. Auftrag läuft weiter.")
        if status == "submission_unknown":
            update(phase="Cloud-Start unbestätigt", progress=None)
        else:
            progress = state.get("progress")
            update(phase=str(state.get("phase") or status)[:200],
                   progress=min(99, max(0, int(progress))) if progress is not None else None)
        time.sleep(2)
    else:
        if status in ("submission_unknown", "unknown"):
            raise SubmissionUnknown("Der private Dienst hat den Start nicht bestätigt. Der Auftrag wird nicht erneut gesendet.")
        raise OutputUnconfirmed("Der private Dienst hat innerhalb des Zeitlimits keine vollständige Ausgabe gemeldet.")
    files = state.get("files") or []
    if tool == "enhancement":
        if (params.get("suggestions") or params.get("disturbances")) and not files.get("suggestions"):
            state.setdefault("failed_tasks", {})["speech_suggestions"] = "Schnittvorschläge fehlen"
        files = [files[key] for key in ("enhanced", "suggestions") if files.get(key)]
    available = {name for name in files if isinstance(name, str) and re.fullmatch(r"[A-Za-z0-9_. -]{1,120}", name)
                 and name.lower().endswith((".wav", ".mid", ".json", ".txt"))}
    missing = wanted - available
    task_errors = state.get("failed_tasks") or {}
    if missing or task_errors or status == "partial":
        update(state="partial", error="Fehlende Ergebnisse: " + ", ".join(sorted(missing | set(task_errors))))
    if wanted:
        available &= wanted
    if not available:
        raise UserError("Der private Dienst hat keine nutzbaren Dateien geliefert.")
    for name in sorted(available):
        output = directory / name
        try:
            call(config, tool, downloads.format(remote) + "/" + quote(name, safe=""), destination=output)
        except CloudHTTPError as error:
            if error.status < 500:
                raise OutputUnconfirmed(f"Gemeldete Ausgabe {name} ist nicht abrufbar.") from error
            raise ConnectionError("Cloud-Ausgabe wird erneut abgefragt.") from error
        details = {"engine": {"separation": "SCNet XL IHF / Mel-Band RoFormer",
                              "generation": "Stable Audio Open 1.0", "transcription": "MuScriptor / Beat This! / Essentia",
                              "mastering": "Automatisches Mastering (Modal)", "enhancement": "MossFormer",
                              "audiosr": "AudioSR Basic"}[tool],
                   "remote_job": remote, "model_details": state.get("model_info")}
        if tool == "separation" and (state.get("model_info") or {}).get("name") == "SCNet XL IHF":
            details["engine"] = "SCNet XL IHF"
        if output.suffix == ".mid":
            role = "midi"
        elif output.suffix != ".wav":
            role = "analysis"
        elif tool == "separation":
            role = "stem"
            details |= {"group": job["id"], "stem": output.stem}
        elif tool == "generation":
            role = "take"
            details["seed"] = params["seed"]
        else:
            role = "variant"
        if tool == "audiosr":
            details |= {"experiment": True, "seed": fields["seed"], "preview_render": True,
                        "source_start": params.get("start", 0), "source_rate": inputs[0][1]["meta"]["rate"],
                        "channel_mapping": "mono, 48 kHz"}
        if tool == "mastering":
            target = number(params.get("lufs", -14), -30, -8, "LUFS-Ziel")
            peak = number(params.get("true_peak", -1), -6, -0.1, "True-Peak-Grenze")
            tuned = directory / "Master.wav"
            ffmpeg("-i", output, "-af", f"loudnorm=I={target}:TP={peak}:LRA=11",
                   "-ar", project["rate"], "-c:a", "pcm_f32le", tuned, cancelled=cancelled)
            output = tuned
            details |= qa(output, cancelled) | {"target_lufs": target, "target_true_peak": peak}
        yield output, role, details


def acknowledge(config, tool, job):
    if job["remote_id"] == job["id"]:
        return call(config, tool, f"/workspace/jobs/{job['id']}/ack", "POST")


def health(config, tool):
    return call(config, tool, "/health")
