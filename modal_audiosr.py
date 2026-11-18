"""Opt-in AudioSR Basic worker, isolated from the five existing Modal images."""

import hashlib
import tempfile
from pathlib import Path

import modal

import modal_workspace as workspace

app = modal.App("artist-workspace-audiosr")
ARTIFACT = "haoheliu/audiosr_basic"
REVISION = "74a47f49061a1e788e968cc43ad45c0b6243f37d"
SHA256 = "8a3506b9619ed32435ce2c115604750c7bddb5ad8502be7b1a3131bde878aa01"
CACHE = "/opt/audiosr-cache"
mount = {workspace.STAGING_PATH: workspace.staging}
api_image = (modal.Image.debian_slim(python_version="3.11").apt_install("ffmpeg")
             .pip_install("fastapi==0.135.1").add_local_python_source("modal_workspace"))
def prefetch_basic():
    from huggingface_hub import hf_hub_download
    path = hf_hub_download(ARTIFACT, "pytorch_model.bin", revision=REVISION)
    with open(path, "rb") as checkpoint:
        if hashlib.file_digest(checkpoint, "sha256").hexdigest() != SHA256:
            raise RuntimeError("AudioSR checkpoint hash mismatch")


model_image = (modal.Image.debian_slim(python_version="3.11")
               .apt_install("ffmpeg", "libsndfile1", "espeak-ng")
               .pip_install("audiosr==0.0.7", "numpy==1.23.5", "scipy==1.15.3",
                            "torch==2.6.0", "torchaudio==2.6.0", "torchvision==0.21.0",
                            "huggingface-hub==0.32.4", "timm==0.9.16", "matplotlib==3.8.4")
               .env({"HF_HUB_CACHE": CACHE, "HF_HUB_DISABLE_TELEMETRY": "1"})
               .add_local_python_source("modal_workspace", copy=True)
               .run_function(prefetch_basic, timeout=1200))


@app.cls(image=model_image, gpu="L40S", memory=24576, timeout=1000, scaledown_window=45,
         volumes=mount, max_containers=1)
class AudioSR:
    def load(self):
        import torch
        from audiosr import pipeline, utils
        from huggingface_hub import hf_hub_download

        path = hf_hub_download(ARTIFACT, "pytorch_model.bin", revision=REVISION, local_files_only=True)
        original_lowpass = utils.lowpass

        def lowpass(data, highcut, fs, **options):
            # AudioSR 0.0.7 uses Nyquist as its own no-filter marker.
            return data if highcut >= fs / 2 else original_lowpass(data, highcut, fs, **options)

        utils.lowpass = lowpass
        configuration = pipeline.default_audioldm_config("basic")
        configuration["model"]["params"]["device"] = "cuda:0"
        model = pipeline.LatentDiffusion(**configuration["model"]["params"])
        # The upstream training checkpoint may contain more than tensor weights.
        checkpoint = torch.load(path, map_location="cpu", weights_only=False)
        model.load_state_dict(checkpoint["state_dict"], strict=False)
        self.model = model.eval().to("cuda:0")

    @modal.method()
    def render(self, job_id, seed):
        prefix = f"jobs/audiosr/{job_id}"
        try:
            import numpy as np
            import soundfile as sf
            with tempfile.TemporaryDirectory() as directory:
                source = Path(directory) / "input.wav"
                if not workspace.load_input(job_id, source, "audiosr", job_id):
                    return
                metadata = sf.info(source)
                if not 0 < metadata.duration <= 15.001 or metadata.channels != 1:
                    raise ValueError("AudioSR Basic requires a mono selection of up to 15 seconds")
                if not hasattr(self, "model"):
                    self.load()
                from audiosr import pipeline
                output = Path(directory) / "bandwidth.wav"
                waveform = np.asarray(pipeline.super_resolution(self.model, str(source), seed=seed, ddim_steps=30)).reshape(-1)
                length = round(metadata.duration * 48000)
                if len(waveform) < length or not np.all(np.isfinite(waveform[:length])):
                    raise ValueError("AudioSR returned incomplete samples")
                sf.write(output, waveform[:length], 48000, subtype="FLOAT")
                with workspace.staging.batch_upload() as transfer:
                    transfer.put_file(output, f"{prefix}/bandwidth.wav")
            workspace.record(prefix, "result", {"status": "completed", "files": ["bandwidth.wav"],
                                               "model_info": {"name": "AudioSR Basic", "revision": REVISION, "sha256": SHA256}})
        except Exception:
            workspace.record(prefix, "result", {"status": "error", "error": "AudioSR konnte diese Auswahl nicht verarbeiten."})
            raise


@app.function(image=api_image, volumes=mount)
@modal.asgi_app(requires_proxy_auth=True)
def audio_sr_api():
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import StreamingResponse
    from uuid import UUID

    api = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @api.get("/health")
    async def health():
        return {"status": "healthy", "model": "AudioSR Basic", "max_seconds": 15}

    @api.get("/status/{job_id}")
    async def status(job_id: UUID):
        return await result_state(str(job_id)) or {"status": "unknown"}

    @api.get("/download/{job_id}/output/bandwidth.wav")
    def download(job_id: UUID):
        prefix = f"jobs/audiosr/{job_id}"
        if (workspace.receipt(prefix, "result") or {}).get("status") != "completed":
            raise HTTPException(404, "Keine Ausgabe")
        return StreamingResponse(workspace.staging.read_file(f"{prefix}/bandwidth.wav"), media_type="audio/wav")

    async def result_state(job_id):
        from starlette.concurrency import run_in_threadpool
        return await run_in_threadpool(workspace.receipt, f"jobs/audiosr/{job_id}", "result") or {}

    workspace.register(api, "audiosr", 5 * 1024 * 1024, AudioSR().render,
                       lambda job_id, options: (job_id, options["seed"]), result_state)
    return api
