"""Password-protected workspace UI and CPU renders on Modal."""

import contextlib
import os
import shutil
import sqlite3
import tempfile
import threading
from pathlib import Path

import modal


ROOT = Path(__file__).resolve().parent
DATA = Path("/xo-data")
PLUGINS = Path("/opt/xo-plugins")
NATIVE_DEPENDENCIES = (
    "ffmpeg", "rubberband-cli", "libsndfile1", "libgomp1", "libgl1", "libgtk-3-0", "libxcursor1",
    "libxinerama1", "libxrandr2", "libx11-6", "libxext6", "libfreetype6", "libfontconfig1", "xvfb", "xauth",
    "autoconf", "automake", "libtool", "build-essential", "curl", "xz-utils", "ca-certificates",
)

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install(*NATIVE_DEPENDENCIES)
    .pip_install_from_requirements(str(ROOT / "requirements-workspace.lock"), extra_options="--no-deps")
    .add_local_file(ROOT / "scripts/setup_workspace_linux.sh", "/opt/setup_workspace_linux.sh", copy=True)
    .run_commands("bash /opt/setup_workspace_linux.sh")
    .workdir("/opt/xo")
    .add_local_file(ROOT / "dev_server.py", "/opt/xo/dev_server.py")
    .add_local_dir(ROOT / "audio_core", "/opt/xo/audio_core", ignore=["**/__pycache__/**"])
    .add_local_dir(ROOT / "studio", "/opt/xo/studio", ignore=["**/__pycache__/**"])
    .add_local_dir(ROOT / "web/dist", "/opt/xo/web/dist")
    .add_local_file(ROOT / "web/public/favicon.png", "/opt/xo/web/public/favicon.png")
)
app = modal.App("artist-workspace-online")
volume = modal.Volume.from_name("dreamtelligence-artist-workspace-online-v1", create_if_missing=True, version=2)


@app.function(image=image, volumes={str(DATA): volume}, secrets=[
                  modal.Secret.from_name("artist-workspace-online-auth"),
                  modal.Secret.from_name("artist-workspace-online-password"),
              ],
              region="eu", routing_region="eu-west", cpu=(0.5, 2), memory=(1024, 4096),
              max_containers=1, scaledown_window=120, timeout=900)
@modal.concurrent(max_inputs=16)
@modal.asgi_app(label="artist-workspace-online")
def workspace():
    from studio.app import HostedWorkspace, create_app

    runtime = Path(tempfile.mkdtemp(prefix="xo-workspace-"))
    config = runtime / "model-workers.json"
    config.touch(mode=0o600, exist_ok=False)
    config.write_text(os.environ["XO_MODEL_WORKER_CONFIG"])
    catalog = runtime / "workspace.sqlite3"
    snapshot = DATA / "catalog.sqlite3"
    lock = threading.Lock()
    if snapshot.is_file():
        shutil.copyfile(snapshot, catalog)

    def checkpoint(database):
        with lock, tempfile.NamedTemporaryFile(dir=DATA, prefix=".catalog-", delete=False) as temporary:
            staged = Path(temporary.name)
            try:
                with contextlib.closing(sqlite3.connect(database, timeout=20)) as source, \
                        contextlib.closing(sqlite3.connect(staged)) as destination:
                    source.backup(destination)
                os.replace(staged, snapshot)
                volume.commit()
            finally:
                staged.unlink(missing_ok=True)

    return create_app(DATA, config, hosted=HostedWorkspace(
        origin=os.environ["XO_WEB_ORIGIN"], password=os.environ["XO_STUDIO_PASSWORD"],
        catalog=catalog, work=runtime / "work", plugins=PLUGINS, persist=checkpoint,
        public_origin="https://studio.dreamtelligence.de",
    ))
