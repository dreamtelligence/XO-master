"""Loopback-only FastAPI entry point for Dreamtelligence Artist Workspace."""

import argparse
import asyncio
import contextlib
import re
import secrets
import tempfile
import threading
from pathlib import Path
from typing import Any, Literal
from urllib.parse import unquote
from uuid import UUID

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool

from audio_core import engines
from dev_server import CONFIG_PATH, ROOT, create_server, load_config
from studio import modal_adapter
from studio.store import AUDIO, BUDGET, MAX_UPLOAD, MIB, RESERVE, TOOLS, Problem, Store, data_path

MEDIA = {".wav": "audio/wav", ".mp3": "audio/mpeg", ".flac": "audio/flac", ".m4a": "audio/mp4",
         ".ogg": "audio/ogg", ".aac": "audio/aac", ".aiff": "audio/aiff", ".webm": "audio/webm",
         ".mid": "audio/midi", ".json": "application/json", ".txt": "text/plain", ".zip": "application/zip"}
CSP = ("default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
       "font-src 'self'; media-src 'self' blob:; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; "
       "form-action 'self'; object-src 'none'")


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class ProjectCreate(Model):
    name: str = Field(default="Neues Projekt", max_length=140)
    rate: Literal[44100, 48000] = 48000
    bpm: float = Field(default=120, ge=30, le=300)
    template: Literal["empty", "remix", "mix", "speech", "generate"] = "empty"
    purpose: Literal["private", "release"] = "private"


class ProjectPatch(Model):
    revision: int = Field(ge=0)
    name: str | None = Field(default=None, max_length=140)
    rate: Literal[44100, 48000] | None = None
    bpm: float | None = Field(default=None, ge=30, le=300)
    meter: str | None = None
    purpose: Literal["private", "release"] | None = None
    draft: dict[str, Any] | None = None
    archived: bool | None = None


class AssetPatch(Model):
    name: str | None = Field(default=None, max_length=140)
    role: Literal["original", "reference", "variant"] | None = None
    hidden: bool | None = None


class Run(Model):
    id: UUID
    tool: str = Field(max_length=32)
    inputs: list[UUID] = Field(default_factory=list, max_length=256)
    params: dict[str, Any] = Field(default_factory=dict)
    count: int = Field(default=1, ge=1, le=3)
    draft_revision: int | None = Field(default=None, ge=0)


class RecipeStep(Model):
    tool: str = Field(max_length=32)
    params: dict[str, Any] = Field(default_factory=dict)
    feed: Literal["result", "input", "initial"] = "result"
    output: str = Field(default="", max_length=140)
    extra_inputs: list[UUID] = Field(default_factory=list, max_length=4)


class RecipeRun(Model):
    id: UUID
    draft_revision: int = Field(ge=0)
    inputs: list[UUID] = Field(default_factory=list, max_length=24)
    steps: list[RecipeStep] = Field(min_length=2, max_length=8)


def failure(status, message, code):
    return JSONResponse({"code": code, "detail": message, "retry_safe": status in (404, 422, 503)}, status_code=status)


def create_app(root=None, config_path=CONFIG_PATH, *, port=8765, dev=False, legacy=False):
    token = secrets.token_urlsafe(40)
    hosts = {f"localhost:{port}", f"127.0.0.1:{port}"}
    if dev:
        hosts |= {"localhost:5173", "127.0.0.1:5173"}
    @contextlib.asynccontextmanager
    async def lifespan(app):
        app.state.store = Store(root or data_path(), load_config(config_path))
        old = None
        try:
            if legacy:
                old = create_server(8766, config_path)
                threading.Thread(target=old.serve_forever, daemon=True).start()
            yield
        finally:
            if old:
                old.shutdown()
                old.server_close()
            app.state.store.close()

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None, redirect_slashes=False)

    @app.middleware("http")
    async def loopback(request, next_handler):
        host = request.headers.get("host")
        origin = request.headers.get("origin")
        fetch = request.headers.get("sec-fetch-site")
        raw_path = unquote(request.scope.get("raw_path", b"").decode("ascii", "replace"))
        if host not in hosts or (origin and origin != f"http://{host}") or fetch not in (None, "none", "same-origin"):
            return failure(403, "Nur Anfragen aus diesem lokalen Arbeitsbereich sind erlaubt.", "origin")
        if "\\" in raw_path or any(part in (".", "..") for part in raw_path.split("/")):
            return failure(400, "Ungültiger Dateipfad.", "path")
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            supplied = request.headers.get("x-workspace-session", "")
            if not secrets.compare_digest(supplied, token):
                return failure(403, "Die lokale Sitzung ist abgelaufen. Bitte neu laden.", "session")
            length = request.headers.get("content-length", "")
            binary = request.method == "POST" and request.url.path.endswith(("/assets", "/import-package"))
            limit = 2 * 1024 * MIB if request.url.path.endswith("/import-package") else MAX_UPLOAD if binary else MIB
            if (not length.isascii() or not length.isdecimal() or len(length) > 12
                    or request.headers.get("transfer-encoding")):
                return failure(411, "Content-Length ist für diese Anfrage erforderlich.", "length")
            if int(length) > limit:
                return failure(413, "Diese Datei oder Anfrage ist zu groß.", "size")
        response = await next_handler(request)
        response.headers.update({"Content-Security-Policy": CSP, "X-Content-Type-Options": "nosniff",
                                 "Cross-Origin-Resource-Policy": "same-origin", "X-Frame-Options": "DENY",
                                 "Referrer-Policy": "no-referrer", "Cache-Control": "no-store"})
        return response

    @app.exception_handler(Problem)
    async def invalid_problem(_request, error):
        return failure(error.status, str(error), error.code)

    @app.exception_handler(engines.UserError)
    async def audio_input_error(_request, error):
        return failure(422, str(error), "invalid")

    @app.exception_handler(ValueError)
    async def invalid_value(_request, _error):
        return failure(422, "Die Eingabe konnte nicht verarbeitet werden.", "invalid")

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_request, error):
        fields = [str(item["loc"][-1]) for item in error.errors()]
        return failure(422, "Ungültige Felder: " + ", ".join(fields), "validation")

    def store():
        return app.state.store

    @app.get("/api/session")
    def session():
        return {"session": token}

    @app.get("/api/capabilities")
    def capabilities():
        statuses = {key: "needs_setup" if not store().engines[engine] else "experimental" if key == "audiosr" else "ready"
                    for key, engine in TOOLS.items()}
        return {"tools": statuses, "rates": [44100, 48000], "upload_bytes": MAX_UPLOAD, "generation_seconds": 47,
                "batch_variants": 3, "duration_limit": 1800, "storage_bytes": BUDGET, "reserve_bytes": RESERVE,
                "used_bytes": store().usage(), "legacy": legacy}

    @app.get("/api/storage")
    def storage():
        return {"used_bytes": store().usage(), "preview_bytes": store().usage("listen"),
                "budget_bytes": BUDGET, "reserve_bytes": RESERVE}

    @app.post("/api/storage/clear-previews")
    def clear_previews():
        return {"preview_bytes": store().clear_listen()}

    @app.get("/api/projects")
    def projects():
        return store().projects()

    @app.post("/api/projects", status_code=201)
    def create(body: ProjectCreate):
        return store().create(body.model_dump())

    @app.get("/api/projects/{id}")
    def get_project(id: UUID):
        return store().contents(str(id))

    @app.patch("/api/projects/{id}")
    def patch_project(id: UUID, body: ProjectPatch):
        return store().patch(str(id), body.model_dump(exclude_none=True))

    @app.post("/api/projects/{id}/duplicate", status_code=201)
    def duplicate_project(id: UUID):
        return store().duplicate(str(id))

    async def streamed(request, use):
        size = int(request.headers["content-length"])
        if size == 0:
            raise Problem("Die Datei ist leer.")
        await run_in_threadpool(store().require_space, size * 2)
        with tempfile.TemporaryDirectory(dir=store().root / "work") as tmp:
            target = Path(tmp) / "upload"
            received = 0
            with target.open("xb") as file:
                async for chunk in request.stream():
                    received += len(chunk)
                    if received > size:
                        raise Problem("Upload überschreitet die angegebene Länge.", 413)
                    await run_in_threadpool(file.write, chunk)
            if received != size:
                raise Problem("Die Datei wurde nicht vollständig übertragen.")
            return await run_in_threadpool(use, target)

    @app.post("/api/projects/import-package", status_code=201)
    async def restore(request: Request):
        return await streamed(request, store().restore)

    @app.post("/api/projects/{id}/assets", status_code=201)
    async def import_asset(id: UUID, request: Request, filename: str, role: Literal["original", "reference"] = "original"):
        await run_in_threadpool(store().project, str(id))
        return await streamed(request, lambda path: store().import_audio(str(id), path, filename, role))

    @app.get("/api/projects/{id}/assets/{asset}")
    def get_asset(id: UUID, asset: UUID):
        return store().asset(str(id), str(asset))

    @app.patch("/api/projects/{id}/assets/{asset}")
    def edit_asset(id: UUID, asset: UUID, body: AssetPatch):
        return store().asset_patch(str(id), str(asset), body.model_dump(exclude_none=True))

    @app.get("/api/projects/{id}/assets/{asset}/peaks")
    def get_peaks(id: UUID, asset: UUID):
        meta = store().asset(str(id), str(asset))["meta"]
        return {"peaks": meta.get("peaks", []), "seconds": meta.get("seconds"), "samples": meta.get("samples")}

    @app.get("/api/projects/{id}/assets/{asset}/window")
    def audio_window(id: UUID, asset: UUID, request: Request, seconds: float, start: float = 0):
        item = store().asset(str(id), str(asset))
        if item["role"] not in AUDIO:
            raise Problem("Dieses Asset enthält kein Audio.", 404)
        start = float(request.query_params.get("from", start))
        engines.number(start, 0, item["meta"]["seconds"], "Start")
        engines.number(seconds, 0.00001, 80, "Fenster")
        # Browser windows are downsampled and bounded independently from DAW audio.
        seconds = min(seconds, item["meta"]["seconds"] - start)
        if seconds <= 0:
            raise Problem("Das Hörfenster liegt hinter dem Signalende.", 416, "window")
        with tempfile.TemporaryDirectory(dir=store().root / "work") as tmp:
            wav = Path(tmp) / "window.wav"
            engines.ffmpeg("-ss", start, "-i", store().path(item), "-t", seconds, "-ar", "32000",
                           "-c:a", "pcm_s16le", wav)
            return Response(wav.read_bytes(), media_type="audio/wav")

    @app.api_route("/api/projects/{id}/assets/{asset}/{kind}", methods=["GET", "HEAD"])
    def asset_file(id: UUID, asset: UUID, kind: Literal["listen", "audio", "download"]):
        item = store().asset(str(id), str(asset))
        if kind != "download" and item["role"] not in AUDIO:
            raise Problem("Dieses Asset enthält kein Audio.", 404)
        file = store().path(item, preview=kind == "listen")
        if kind == "listen" and not file.is_file():
            file = store().path(item)
            kind = "audio"
        if not file.is_file():
            raise Problem("Datei wurde im lokalen Speicher nicht gefunden.", 404)
        suffix = item["suffix"]
        if kind != "download":
            return FileResponse(file, media_type=MEDIA.get(".mp3" if kind == "listen" else suffix, "application/octet-stream"))
        display = item["name"]
        if not display.lower().endswith(suffix):
            display += suffix
        return FileResponse(file, media_type=MEDIA.get(suffix, "application/octet-stream"), filename=display)

    @app.post("/api/projects/{id}/runs/validate")
    def validate(id: UUID, body: Run):
        data = body.model_dump(mode="json")
        assets = store().validate(store().project(str(id)), body.tool, data["inputs"], body.params)
        return {"valid": True, "assets": [item["id"] for item in assets],
                "execution": "cloud" if body.tool in modal_adapter.ROUTES else "local"}

    @app.post("/api/projects/{id}/runs", status_code=202)
    def run(id: UUID, body: Run):
        return {"jobs": store().enqueue(str(id), body.model_dump(mode="json"))}

    @app.post("/api/projects/{id}/recipe-runs", status_code=202)
    def execute_recipe(id: UUID, body: RecipeRun):
        return {"jobs": store().enqueue_recipe(str(id), body.model_dump(mode="json"))}

    @app.post("/api/projects/{id}/exports", status_code=202)
    def export(id: UUID, body: Run):
        return {"jobs": store().enqueue(str(id), body.model_dump(mode="json") | {"tool": "export"})}

    @app.get("/api/projects/{id}/jobs/{job}")
    def get_job(id: UUID, job: UUID):
        return store().job(str(id), str(job))

    @app.post("/api/projects/{id}/jobs/{job}/cancel")
    def cancel(id: UUID, job: UUID):
        return store().cancel(str(id), str(job))

    @app.post("/api/projects/{id}/jobs/{job}/reconcile")
    def reconcile(id: UUID, job: UUID):
        return store().reconcile(str(id), str(job))

    @app.api_route("/api/{path:path}", methods=["GET", "POST", "HEAD", "PATCH"])
    def api_missing(path: str):
        if path in ("credits", "paywall", "webhook", "create-checkout-session"):
            return failure(410, "Zahlungen und Credits sind deaktiviert.", "disabled")
        return failure(404, "API-Route nicht gefunden.", "not_found")

    @app.api_route("/", methods=["GET", "HEAD"])
    def homepage():
        index = ROOT / "web/dist/index.html"
        if not index.is_file():
            return failure(503, "Frontend zuerst mit npm run build erstellen.", "build_required")
        return FileResponse(index)

    @app.api_route("/favicon.png", methods=["GET", "HEAD"])
    def favicon():
        return FileResponse(ROOT / "web/public/favicon.png", media_type="image/png")

    @app.api_route("/assets/{filename}", methods=["GET", "HEAD"])
    def static_asset(filename: str):
        file = ROOT / "web/dist/assets" / filename
        if not re.fullmatch(r"[A-Za-z0-9_-]+\.(?:js|css|woff2)", filename) or not file.is_file():
            return failure(404, "Datei nicht gefunden.", "not_found")
        return FileResponse(file)

    return app


if __name__ == "__main__":
    import uvicorn
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument("--data", type=Path, default=data_path())
    parser.add_argument("--dev", action="store_true")
    parser.add_argument("--legacy", action="store_true")
    args = parser.parse_args()
    uvicorn.run(create_app(args.data, args.config, port=args.port, dev=args.dev, legacy=args.legacy),
                host="127.0.0.1", port=args.port, workers=1, access_log=False)
