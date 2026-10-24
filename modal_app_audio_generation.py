#!/usr/bin/env python3
"""
Klein Digital Solutions - Stable Audio Open Text-to-Audio Generation
Modal Serverless Deployment with A10G GPU

Features:
- Stable Audio Open 1.0 (stabilityai) - 44.1kHz stereo, up to 47 seconds
- Text-to-Audio Generation (sound effects, loops, production elements)
- Multiple audio formats (WAV, MP3)
- Model weights baked into the image, pipeline loaded once per container

License: Stability AI Community License (free for individuals and organisations
below USD 1M annual revenue). Weights are gated on Hugging Face, so the
"huggingface" Modal secret (HF_TOKEN) must belong to an account with access.
"""

import modal
from pathlib import Path
import uuid
import time
import json

# Status dictionary for job progress
job_status = {}

# Modal app instance
app = modal.App("audio-generation-stable-audio-open")

# Create persistent volume for file storage
volume = modal.Volume.from_name("audio-gen-files", create_if_missing=True)
storage_path = "/vol/audio_files"

MODEL_ID = "stabilityai/stable-audio-open-1.0"
HF_CACHE = "/opt/hf-cache"

AUDIO_CONFIG = {
    "model_id": MODEL_ID,
    "parameters": "1.2B",
    "min_audio_length": 1.0,
    "max_audio_length": 47.0,  # seconds (model limit)
    "sample_rate": 44100,
    "channels": 2,
    "license": "Stability AI Community License (non-commercial / < USD 1M revenue)"
}


def _prefetch_model():
    from huggingface_hub import snapshot_download
    snapshot_download(MODEL_ID, cache_dir=HF_CACHE)


audio_gen_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install(["ffmpeg", "libsndfile1"])
    .pip_install([
        "torch",
        "torchaudio",
        "diffusers",
        "transformers",
        "accelerate",
        "torchsde",
        "huggingface-hub",
        "soundfile",
        "numpy",
        "fastapi[standard]",
        "python-multipart",
    ])
    .env({"HF_HUB_CACHE": HF_CACHE})
    .run_function(_prefetch_model, secrets=[modal.Secret.from_name("huggingface")])
)


def save_job_status(job_id: str, status_data: dict):
    """Save job status to volume for persistence"""
    try:
        status_file = Path(storage_path) / f"status_{job_id}.json"
        with open(status_file, 'w') as f:
            json.dump(status_data, f)
        volume.commit()
        print(f"📊 Audio generation status saved for job {job_id}: {status_data.get('progress', 0)}% - {status_data.get('phase', 'Unknown')}")
    except Exception as e:
        print(f"⚠️ Error saving job status: {e}")


@app.cls(
    image=audio_gen_image,
    gpu="a10g",
    timeout=1200,
    memory=20480,
    volumes={storage_path: volume},
    scaledown_window=300  # Keep warm longer for large model
)
class AudioGenerator:
    @modal.enter()
    def load(self):
        import torch
        from diffusers import StableAudioPipeline

        print(f"🔄 Loading {MODEL_ID}...")
        self.pipe = StableAudioPipeline.from_pretrained(MODEL_ID, torch_dtype=torch.float16).to("cuda")
        self.sample_rate = self.pipe.vae.sampling_rate
        print(f"✅ Stable Audio Open loaded on GPU ({self.sample_rate} Hz)")

    @modal.method()
    def generate(
        self,
        prompt: str,
        job_id: str,
        audio_length: float = 10.0,
        num_inference_steps: int = 100,
        guidance_scale: float = 7.0,
        output_format: str = "wav",
        negative_prompt: str = "Low quality.",
        seed: int = 42
    ) -> dict:
        import subprocess
        import torch
        import soundfile as sf

        start_time = time.time()
        try:
            job_dir = Path(storage_path) / job_id
            output_dir = job_dir / "output"
            output_dir.mkdir(parents=True, exist_ok=True)

            print(f"🎵 Generating for job {job_id}: '{prompt}' ({audio_length}s, {num_inference_steps} steps)")
            job_status[job_id] = {
                "status": "generating",
                "progress": 40,
                "phase": "Audio wird generiert mit Stable Audio Open",
                "error": None,
                "processing_time": None
            }
            save_job_status(job_id, job_status[job_id])

            generator = torch.Generator(device="cuda").manual_seed(seed)
            result = self.pipe(
                prompt,
                negative_prompt=negative_prompt or None,
                num_inference_steps=num_inference_steps,
                audio_end_in_s=audio_length,
                guidance_scale=guidance_scale,
                num_waveforms_per_prompt=1,
                generator=generator,
            )
            # [channels, samples] -> [samples, channels]
            audio = result.audios[0].T.float().cpu().numpy()

            job_status[job_id] = {
                "status": "saving",
                "progress": 80,
                "phase": "Audio wird gespeichert",
                "error": None,
                "processing_time": None
            }
            save_job_status(job_id, job_status[job_id])

            output_files = []
            wav_path = output_dir / "generated_audio.wav"
            sf.write(str(wav_path), audio, self.sample_rate, subtype="PCM_16")
            output_files.append("generated_audio.wav")

            if output_format in ("mp3", "both"):
                mp3_path = output_dir / "generated_audio.mp3"
                subprocess.run(
                    ["ffmpeg", "-y", "-i", str(wav_path), "-b:a", "192k", str(mp3_path)],
                    check=True, capture_output=True, timeout=120
                )
                output_files.append("generated_audio.mp3")
                if output_format == "mp3":
                    wav_path.unlink()
                    output_files.remove("generated_audio.wav")

            processing_time = round(time.time() - start_time, 2)
            total_size = sum(f.stat().st_size for f in output_dir.glob("*"))

            job_status[job_id] = {
                "status": "completed",
                "progress": 100,
                "phase": "Fertig - Audio generiert",
                "error": None,
                "processing_time": processing_time,
                "files": output_files,
                "total_size_mb": round(total_size / (1024 * 1024), 1),
                "download_base_url": f"/download/{job_id}/output",
                "audio_info": {
                    "duration": round(len(audio) / self.sample_rate, 2),
                    "sample_rate": self.sample_rate,
                    "channels": int(audio.shape[1]) if audio.ndim == 2 else 1,
                    "format": output_format,
                    "prompt": prompt
                },
                "model_info": {
                    "name": "Stable Audio Open 1.0",
                    "parameters": AUDIO_CONFIG["parameters"],
                    "inference_steps": num_inference_steps,
                    "license": AUDIO_CONFIG["license"]
                }
            }
            save_job_status(job_id, job_status[job_id])
            print(f"🎉 Generation completed for job {job_id} in {processing_time}s")
            return {"success": True, "files": output_files, "job_id": job_id, "processing_time": processing_time}

        except Exception as e:
            error_msg = str(e)
            print(f"❌ Stable Audio generation failed: {error_msg}")
            job_status[job_id] = {
                "status": "error",
                "progress": 100,
                "phase": "Fehler bei Audio-Generierung",
                "error": error_msg,
                "processing_time": round(time.time() - start_time, 2)
            }
            save_job_status(job_id, job_status[job_id])
            return {"success": False, "error": error_msg, "job_id": job_id}


# FastAPI web application
def create_fastapi_app():
    from fastapi import FastAPI, Form, HTTPException
    from fastapi.responses import StreamingResponse
    from fastapi.middleware.cors import CORSMiddleware

    web_app = FastAPI(
        title="Stable Audio Open Text-to-Audio Generation",
        description="Text-to-audio generation using Stable Audio Open 1.0 (44.1kHz stereo)",
        version="3.0.0"
    )

    # CORS middleware
    web_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @web_app.post("/")
    async def generate_audio(
        prompt: str = Form(...),
        audio_length: float = Form(10.0),
        num_inference_steps: int = Form(100),
        guidance_scale: float = Form(7.0),
        output_format: str = Form("wav"),
        negative_prompt: str = Form("Low quality."),
        seed: int = Form(42)
    ):
        """Generate audio from a text prompt using Stable Audio Open"""
        if len(prompt.strip()) == 0:
            raise HTTPException(400, "Prompt cannot be empty")
        if not (AUDIO_CONFIG["min_audio_length"] <= audio_length <= AUDIO_CONFIG["max_audio_length"]):
            raise HTTPException(400, f"Audio length must be between {AUDIO_CONFIG['min_audio_length']} and {AUDIO_CONFIG['max_audio_length']} seconds")
        if not (10 <= num_inference_steps <= 200):
            raise HTTPException(400, "Inference steps must be between 10 and 200")
        if output_format not in ["wav", "mp3", "both"]:
            raise HTTPException(400, "Output format must be 'wav', 'mp3', or 'both'")

        job_id = str(uuid.uuid4())
        save_job_status(job_id, {
            "status": "queued",
            "progress": 5,
            "phase": "Stable Audio Open wird gestartet",
            "error": None,
            "processing_time": None
        })

        AudioGenerator().generate.spawn(
            prompt, job_id, audio_length, num_inference_steps, guidance_scale, output_format, negative_prompt, seed
        )

        return {
            "job_id": job_id,
            "status": "started",
            "message": f"Stable Audio Open generation started for: {prompt[:50]}...",
            "expected_duration": f"{audio_length}s audio"
        }

    @web_app.get("/status/{job_id}")
    async def get_status(job_id: str):
        """Get generation status"""
        volume.reload()
        status_file = Path(storage_path) / f"status_{job_id}.json"

        if status_file.exists():
            try:
                with open(status_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading status: {e}")

        status = job_status.get(job_id)
        if status:
            return status

        return {"status": "unknown", "progress": 0, "phase": "Job nicht gefunden", "error": "Job ID not found"}

    @web_app.get("/download/{job_id}/output/{filename}")
    async def download_file(job_id: str, filename: str):
        """Download generated audio file"""
        volume.reload()
        file_path = Path(storage_path) / job_id / "output" / Path(filename).name

        if not file_path.exists():
            raise HTTPException(404, f"File not found: {filename}")

        def file_iterator():
            with open(file_path, "rb") as f:
                while chunk := f.read(8192):
                    yield chunk

        media_type = "audio/wav" if filename.endswith(".wav") else "audio/mpeg"
        return StreamingResponse(
            file_iterator(),
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Access-Control-Allow-Origin": "*",
            }
        )

    @web_app.get("/health")
    async def health():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "service": "Stable Audio Open Text-to-Audio Generation",
            "model": "Stable Audio Open 1.0",
            "gpu": "A10G (24GB)",
            "capabilities": ["text-to-audio", "wav", "mp3"],
            "max_audio_length": f"{AUDIO_CONFIG['max_audio_length']} seconds",
            "sample_rate": f"{AUDIO_CONFIG['sample_rate']} Hz stereo",
            "license": AUDIO_CONFIG["license"]
        }

    return web_app


# Deploy FastAPI app
@app.function(image=audio_gen_image, volumes={storage_path: volume})
@modal.asgi_app()
def fastapi_app():
    return create_fastapi_app()


if __name__ == "__main__":
    print("🎵 Klein Digital Solutions - Stable Audio Open Text-to-Audio Generation")
    print("💡 Deploy: modal deploy modal_app_audio_generation.py")
