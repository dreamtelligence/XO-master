#!/usr/bin/env python3
"""
Klein Digital Solutions - Music AI Separator
ZFTurbo Music-Source-Separation-Training Complete Implementation
Modal Serverless Deployment with A10G GPU

Features:
- SCNet XL IHF (Multisong SDR avg 9.92dB) for drums / bass / other / vocals
- Mel-Band RoFormer (KimberleyJensen edition, SDR vocals 10.98dB) for vocals + instrumental
- Model weights baked into the image (no download per job)
- Modal volume file handling
"""

import modal
import os
from pathlib import Path
import uuid
import subprocess
import time
import json
import zipfile
import io
import shutil

# Global storage for temporary files
temp_files_storage = {}
# Status dictionary for job progress
job_status = {}

# Modal app instance
app = modal.App("music-ai-separator-zfturbo-complete")

# Create persistent volume for file storage
volume = modal.Volume.from_name("music-files-storage", create_if_missing=True)
storage_path = "/vol/music_files"

# ZFTurbo repository pinned to a known commit (2026-10-15)
ZFTURBO_REPO = "https://github.com/ZFTurbo/Music-Source-Separation-Training.git"
ZFTURBO_COMMIT = "6fdad13686bb7e84d029ec66f9dbe76e65c93ebf"
ZFTURBO_DIR = "/root/Music-Source-Separation-Training"
MODEL_DIR = "/models"
RELEASES = "https://github.com/ZFTurbo/Music-Source-Separation-Training/releases/download"

# Model configuration (see docs/pretrained_models.md in the ZFTurbo repo)
SEPARATION_MODELS = {
    "stems": {
        "name": "SCNet XL IHF",
        "model_type": "scnet",
        "config_url": f"{RELEASES}/v1.0.15/config_musdb18_scnet_xl_more_wide_v5.yaml",
        "model_url": f"{RELEASES}/v1.0.15/model_scnet_ep_36_sdr_10.0891.ckpt",
        "config_file": "config_musdb18_scnet_xl_more_wide_v5.yaml",
        "model_file": "model_scnet_ep_36_sdr_10.0891.ckpt",
        "config_sha256": "54ddcb8aeeae85c8d0e148741e7d87b0fbd38bd21cffa5d59ba124fe1e672f40",
        "model_sha256": "ac25975f0f5704f3d1a3c3c251505b7a0f417a22eafe82773440ee4f7e14b74f",
        "sdr": "9.92",
    },
    "vocals": {
        "name": "Mel-Band RoFormer (KimberleyJensen)",
        "model_type": "mel_band_roformer",
        "config_url": f"https://raw.githubusercontent.com/ZFTurbo/Music-Source-Separation-Training/{ZFTURBO_COMMIT}/configs/KimberleyJensen/config_vocals_mel_band_roformer_kj.yaml",
        # pinned to a Hugging Face commit, not the moving "main" ref
        "model_url": "https://huggingface.co/KimberleyJSN/melbandroformer/resolve/ac9b0614ab3cd7f77219e18ba494dfd93956c348/MelBandRoformer.ckpt",
        "config_file": "config_vocals_mel_band_roformer_kj.yaml",
        "model_file": "MelBandRoformer.ckpt",
        "config_sha256": "f63f38eb1e6e40a7db0dade714a5ae257555dd8748f4e774eae8679275a81926",
        "model_sha256": "87201f4d31afb5bc79993230fc49446918425574db48c01c405e44f365c7559e",
        "sdr": "10.98",
    },
}


def _download_commands():
    # .ckpt files are pickles and ZFTurbo loads them with weights_only=False,
    # so every artifact is pinned and checked against a known SHA-256 before use.
    cmds = [f"mkdir -p {MODEL_DIR}"]
    for m in SEPARATION_MODELS.values():
        for kind in ("config", "model"):
            path = f"{MODEL_DIR}/{m[kind + '_file']}"
            cmds.append(f"curl -fsSL -o {path} {m[kind + '_url']}")
            cmds.append(f"echo '{m[kind + '_sha256']}  {path}' | sha256sum -c -")
    return cmds


# ZFTurbo requirements without the GUI/keyboard extras (wxpython, pyaudio, keyboard)
zfturbo_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install(["ffmpeg", "libsndfile1", "git", "curl", "build-essential"])
    .run_commands([
        f"git clone {ZFTURBO_REPO} {ZFTURBO_DIR}",
        f"cd {ZFTURBO_DIR} && git checkout {ZFTURBO_COMMIT}",
        f"cd {ZFTURBO_DIR} && grep -viE '^(wxpython|pyaudio|keyboard)' requirements.txt > /tmp/requirements.txt",
        "pip install -r /tmp/requirements.txt",
        "pip install 'setuptools<81'",  # older librosa still imports pkg_resources
    ])
    .pip_install(["fastapi[standard]", "python-multipart", "requests"])
    .run_commands(_download_commands())
)

# GPU Memory Optimization Settings
GPU_SETTINGS = {
    "device_ids": "0",
    "use_cuda": True,
    "precision": "float32"  # 32-bit float WAV output
}


def save_job_status(job_id: str, status_data: dict):
    """Save job status to volume for persistence"""
    try:
        status_file = Path(storage_path) / f"status_{job_id}.json"
        with open(status_file, 'w') as f:
            json.dump(status_data, f)
        # Force commit for status updates
        volume.commit()
        print(f"📊 Status saved for job {job_id}: {status_data.get('progress', 0)}% - {status_data.get('phase', 'Unknown')}")
    except Exception as e:
        print(f"⚠️ Error saving job status: {e}")


def run_zfturbo_inference(model_key: str, input_dir: Path, store_dir: Path, use_tta: bool, extract_instrumental: bool):
    """Run ZFTurbo inference.py for one model, results land in store_dir/<input_stem>/<instr>.wav"""
    model = SEPARATION_MODELS[model_key]
    cmd = [
        "python", f"{ZFTURBO_DIR}/inference.py",
        "--model_type", model["model_type"],
        "--config_path", f"{MODEL_DIR}/{model['config_file']}",
        "--start_check_point", f"{MODEL_DIR}/{model['model_file']}",
        "--input_folder", str(input_dir),
        "--store_dir", str(store_dir),
        "--device_ids", GPU_SETTINGS["device_ids"],
        "--disable_detailed_pbar",
    ]
    if use_tta:
        cmd.append("--use_tta")
    if extract_instrumental:
        cmd.append("--extract_instrumental")

    env = os.environ.copy()
    env.update({
        "CUDA_VISIBLE_DEVICES": "0",
        "PYTORCH_CUDA_ALLOC_CONF": "max_split_size_mb:512",
        "TOKENIZERS_PARALLELISM": "false",
    })
    print(f"🎵 Running {model['name']}: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=1500, env=env, cwd=ZFTURBO_DIR)
    if result.returncode != 0:
        print(f"   stdout: {result.stdout[-4000:]}")
        print(f"   stderr: {result.stderr[-4000:]}")
        raise Exception(f"{model['name']} inference failed: {result.stderr[-1500:]}")
    print(f"✅ {model['name']} finished")


@app.function(
    image=zfturbo_image,
    gpu="a10g",
    timeout=1800,  # 30 minutes
    memory=20480,  # 20GB memory
    volumes={storage_path: volume},
    scaledown_window=120
)
def bs_roformer_separate_audio(
    audio_data: bytes,
    filename: str,
    job_id: str,
    selected_stems: str = "all",
    use_tta: bool = False,
    extract_instrumental: bool = False
) -> dict:
    """
    Stem separation: SCNet XL IHF for the 4 stems, Mel-Band RoFormer for vocals/instrumental.
    (Function name kept for compatibility with existing deployments.)
    """
    start_time = time.time()

    def set_status(progress, phase):
        job_status[job_id] = {
            "status": "processing",
            "progress": progress,
            "phase": phase,
            "error": None,
            "processing_time": None
        }
        save_job_status(job_id, job_status[job_id])

    try:
        set_status(10, "Datei wird vorbereitet")
        job_dir = Path(storage_path) / job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        output_dir = job_dir / "output"
        output_dir.mkdir(exist_ok=True)
        final_output_dir = output_dir / "final_stems"
        final_output_dir.mkdir(parents=True, exist_ok=True)

        all_stems = ["vocals", "drums", "bass", "other"]
        if selected_stems == "all":
            stems_to_process = list(all_stems)
        else:
            stems_to_process = [s.strip() for s in selected_stems.split(",") if s.strip() in all_stems]
        if not stems_to_process:  # Fallback if empty or invalid
            stems_to_process = list(all_stems)
        print(f"🎯 Stems to process: {stems_to_process} | instrumental: {extract_instrumental}")

        # Convert everything to 44.1kHz stereo WAV (also normalizes odd WAV formats)
        temp_input_dir = job_dir / "temp_input"
        temp_input_dir.mkdir(exist_ok=True)
        orig_file = job_dir / filename
        orig_file.write_bytes(audio_data)
        input_wav_path = temp_input_dir / "input.wav"
        ffmpeg_cmd = ["ffmpeg", "-y", "-i", str(orig_file), "-ar", "44100", "-ac", "2", "-sample_fmt", "s16", str(input_wav_path)]
        try:
            subprocess.run(ffmpeg_cmd, check=True, capture_output=True, timeout=120)
        except subprocess.CalledProcessError as e:
            raise Exception(f"FFmpeg-Konvertierung fehlgeschlagen: {e.stderr.decode(errors='ignore')[-500:]}")
        print(f"📁 Input: {input_wav_path} ({len(audio_data) // 1024} KB original)")
        volume.commit()

        # 1) SCNet XL IHF: drums / bass / other (+ vocals if no dedicated vocal pass is needed)
        need_band_stems = any(s in stems_to_process for s in ["drums", "bass", "other"])
        need_vocal_model = "vocals" in stems_to_process or extract_instrumental
        stems_store = output_dir / "scnet"
        vocals_store = output_dir / "vocal_model"

        if need_band_stems:
            set_status(30, "Separation läuft (SCNet XL)")
            run_zfturbo_inference("stems", temp_input_dir, stems_store, use_tta, False)

        # 2) Mel-Band RoFormer: best vocals + instrumental (mix - vocals)
        if need_vocal_model:
            set_status(60, "Gesang wird isoliert (Mel-Band RoFormer)")
            run_zfturbo_inference("vocals", temp_input_dir, vocals_store, use_tta, extract_instrumental)

        set_status(80, "Dateien werden kopiert")
        sources = {stem: stems_store / "input" / f"{stem}.wav" for stem in ["drums", "bass", "other"]}
        sources["vocals"] = vocals_store / "input" / "vocals.wav"
        if extract_instrumental:
            sources["instrumental"] = vocals_store / "input" / "instrumental.wav"

        wanted = stems_to_process + (["instrumental"] if extract_instrumental else [])
        output_files = []
        for stem_type in wanted:
            src = sources.get(stem_type)
            if src and src.exists():
                shutil.move(str(src), final_output_dir / f"{stem_type}.wav")
                output_files.append(f"{stem_type}.wav")
                print(f"✅ Moved {stem_type} stem")
            else:
                print(f"⚠️ Missing output for {stem_type}: {src}")

        if not output_files:
            raise Exception("No output files were successfully processed")

        # Vorschau-Aufgaben für alle finalen Dateien sammeln
        preview_tasks = [
            (str(final_output_dir / f), str(final_output_dir / f"preview_{f}"))
            for f in output_files
        ]
        volume.commit()

        print(f"🚀 Starting parallel generation of {len(preview_tasks)} previews...")
        job_status[job_id]["phase"] = "Vorschauen werden parallel erstellt"
        save_job_status(job_id, job_status[job_id])

        results = list(generate_preview_parallel.map(preview_tasks))
        successful_previews = sum(1 for r in results if r)
        print(f"✅ Parallel preview generation complete. {successful_previews}/{len(preview_tasks)} successful.")

        # Make sure previews written by the other containers are visible before completing
        volume.reload()

        total_size = sum(f.stat().st_size for f in final_output_dir.glob("*.wav"))
        processing_time = round(time.time() - start_time, 2)
        model_info = {
            "name": "SCNet XL IHF + Mel-Band RoFormer (ZFTurbo)",
            "sdr": f"{SEPARATION_MODELS['stems']['sdr']}dB avg / vocals {SEPARATION_MODELS['vocals']['sdr']}dB",
            "type": "SCNet (stems) + Mel-Band RoFormer (vocals)",
            "repository": "ZFTurbo/Music-Source-Separation-Training"
        }

        job_status[job_id] = {
            "status": "completed",
            "progress": 100,
            "phase": "Fertig - Download verfügbar",
            "error": None,
            "processing_time": processing_time,
            "files": output_files,
            "total_size_mb": round(total_size / (1024 * 1024), 1),
            "download_base_url": f"/download/{job_id}/final_stems",
            "model_info": model_info
        }
        save_job_status(job_id, job_status[job_id])
        print(f"🎉 Job {job_id} marked as COMPLETED with {len(output_files)} files")

        return {
            "success": True,
            "files": output_files,
            "job_id": job_id,
            "processing_time": processing_time,
            "total_size": total_size,
            "model_used": "scnet_xl_ihf+mel_band_roformer",
            "device": "A10G GPU (24GB)",
            "model_info": model_info,
            "gpu_settings": GPU_SETTINGS,
        }

    except Exception as e:
        error_msg = str(e)
        print(f"❌ Separation failed: {error_msg}")
        job_status[job_id] = {
            "status": "error",
            "progress": 100,
            "phase": "Fehler",
            "error": error_msg,
            "processing_time": round(time.time() - start_time, 2)
        }
        save_job_status(job_id, job_status[job_id])
        return {
            "success": False,
            "error": error_msg,
            "job_id": job_id,
            "processing_time": round(time.time() - start_time, 2)
        }

@app.function(
    image=zfturbo_image,
    volumes={storage_path: volume},
    timeout=120 # 2 minutes should be plenty for one preview
)
def generate_preview_parallel(paths: tuple[str, str], duration: int = 30):
    """
    Generates a single preview in parallel using ffmpeg.
    Accepts a tuple of string paths for Modal's .map() compatibility.
    """
    import subprocess
    import os
    from pathlib import Path

    audio_path_str, preview_path_str = paths
    audio_path = Path(audio_path_str)
    preview_path = Path(preview_path_str)

    try:
        # 1. Get total duration with ffprobe
        ffprobe_cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)
        ]
        total_duration = float(subprocess.check_output(ffprobe_cmd, text=True).strip())

        # 2. Calculate start time for the preview (middle of the track)
        start_time = max(0, (total_duration / 2) - (duration / 2))

        # 3. Create MP3 preview with ffmpeg (fast seeking)
        mp3_path = str(preview_path.with_suffix('.mp3'))
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-ss", str(start_time),
            "-i", str(audio_path),
            "-t", str(duration),
            "-vn", "-ar", "44100", "-ac", "2", "-b:a", "128k",
            mp3_path
        ]
        
        subprocess.run(ffmpeg_cmd, check=True, capture_output=True, timeout=60)

        if os.path.exists(mp3_path):
            print(f"✅ Parallel preview created: {mp3_path}")
            volume.commit() # Commit the created file to the volume
            return True
        else:
            print(f"❌ Parallel preview NOT found after ffmpeg call: {mp3_path}")
            return False

    except Exception as e:
        error_details = ""
        if isinstance(e, subprocess.CalledProcessError):
            error_details = e.stderr
        print(f"⚠️ Parallel preview failed for {audio_path.name}: {e} {error_details}")
        return False

# FastAPI web application - following Modal best practices
def create_fastapi_app():
    from fastapi import FastAPI, File, Form, UploadFile, HTTPException
    from fastapi.responses import StreamingResponse, PlainTextResponse, HTMLResponse
    from fastapi.middleware.cors import CORSMiddleware

    web_app = FastAPI(
        title="Music AI Separator - ZFTurbo Complete",
        description="Music source separation using ZFTurbo SCNet XL IHF + Mel-Band RoFormer",
        version="1.0.0"
    )
    @web_app.get("/status/{job_id}")
    async def status(job_id: str):
        """Status-API für Fortschrittsanzeige"""
        # Always check volume first for latest status
        volume.reload()
        status_file = Path(storage_path) / f"status_{job_id}.json"
        
        if status_file.exists():
            try:
                with open(status_file, 'r') as f:
                    status = json.load(f)
                print(f"📊 Status loaded from volume for job {job_id}: {status.get('progress', 0)}% - {status.get('phase', 'Unknown')}")
                return status
            except Exception as e:
                print(f"Error loading status from volume: {e}")
        
        # Fallback to in-memory status
        status = job_status.get(job_id)
        if status:
            print(f"📊 Status loaded from memory for job {job_id}: {status.get('progress', 0)}% - {status.get('phase', 'Unknown')}")
            return status
        
        print(f"❌ No status found for job {job_id}")
        return {"status": "unknown", "progress": 0, "phase": "Nicht gefunden", "error": "Job nicht gefunden"}

    @web_app.get("/debug/download_input_wav/{job_id}")    
    async def debug_download_input_wav(job_id: str):
        """Download the generated input.wav for debugging"""
        volume.reload()
        file_path = Path(storage_path) / job_id / "temp_input" / "input.wav"
        # Debug: Print job_id, file_path, and existence for troubleshooting
        print(f"[DOWNLOAD DEBUG] Job-ID: {job_id} | file_path: {file_path} | Exists: {file_path.exists()}")
        if not file_path.exists():
            raise HTTPException(404, f"input.wav not found for job {job_id}")
        def file_iterator():
            with open(file_path, "rb") as f:
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    yield chunk
        return StreamingResponse(
            file_iterator(),
            media_type="audio/wav",
            headers={
                "Content-Disposition": f"attachment; filename=input.wav",
                "Access-Control-Allow-Origin": "*",
            }
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
    async def api_upload(
        audio_file: UploadFile = File(...), 
        selected_stems: str = Form("all"),
        use_tta: bool = Form(False),
        extract_instrumental: bool = Form(False)
    ):
        """
        Upload endpoint - starts async processing and returns job_id immediately
        selected_stems: "all", "vocals", "drums", "bass", "other" or comma-separated like "vocals,drums"
        """
        from fastapi import Response
        
        try:
            print(f"🎵 Received file for separation: {audio_file.filename}")
            
            # Validate file format
            allowed_extensions = ['.mp3', '.wav', '.flac', '.m4a', '.aac']
            if not any(audio_file.filename.lower().endswith(ext) for ext in allowed_extensions):
                raise HTTPException(400, f"Unsupported file format. Allowed: {', '.join(allowed_extensions)}")
            
            # Read and validate audio data
            audio_data = await audio_file.read()
            
            if len(audio_data) == 0:
                raise HTTPException(400, "Empty file uploaded")
            
            # File size limit (100MB)
            max_size = 100 * 1024 * 1024
            if len(audio_data) > max_size:
                raise HTTPException(400, f"File too large (max {max_size // 1024 // 1024}MB)")
            
            # Generate job ID and safe filename
            job_id = str(uuid.uuid4())
            file_extension = Path(audio_file.filename).suffix
            safe_filename = f"{job_id}{file_extension}"
            
            print(f"🎵 Starting async processing for {audio_file.filename} ({len(audio_data)} bytes)")
            
            # Initialize job status
            job_status[job_id] = {
                "status": "queued",
                "progress": 0,
                "phase": "Upload abgeschlossen, wird verarbeitet...",
                "error": None,
                "processing_time": None,
                "files": [],
                "total_size_mb": 0
            }
            
            # Start async processing
            bs_roformer_separate_audio.spawn(
                audio_data, safe_filename, job_id, selected_stems, use_tta, extract_instrumental
            )
            
            response_data = {
                "job_id": job_id,
                "status": "queued",
                "message": "Processing started. Use /status/{job_id} to check progress."
            }
            
            print(f"🔄 ZFTurbo job {job_id} queued for processing")
            
            # Manual CORS headers for response
            import json
            response = Response(
                content=json.dumps(response_data),
                media_type="application/json"
            )
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            
            return response
                
        except Exception as e:
            print(f"❌ Unexpected ZFTurbo error: {str(e)}")
            raise HTTPException(500, f"Unexpected ZFTurbo error: {str(e)}")

    @web_app.get("/health")
    async def health():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "service": "Klein Digital Solutions - Music AI Separator",
            "implementation": "ZFTurbo/Music-Source-Separation-Training",
            "gpu": "A10G (24GB)",
            "model": "SCNet XL IHF + Mel-Band RoFormer",
            "max_file_size": "100MB",
            "repository": "https://github.com/ZFTurbo/Music-Source-Separation-Training"
        }

    @web_app.get("/models")
    async def models():
        """Get model information"""
        return {
            "models": {
                key: {
                    "name": m["name"],
                    "description": "4 stems (drums/bass/other)" if key == "stems" else "Vocals + instrumental",
                    "stems": ["drums", "bass", "other"] if key == "stems" else ["vocals", "instrumental"],
                    "sdr": f"{m['sdr']}dB",
                    "processing_time": "~2-5 minutes",
                    "repository": "ZFTurbo/Music-Source-Separation-Training",
                    "quality": "State-of-the-Art"
                }
                for key, m in SEPARATION_MODELS.items()
            },
            "gpu_info": {
                "type": "NVIDIA A10G",
                "memory": "24GB VRAM",
                "optimized_for": "Professional Audio Processing",
                "implementation": "ZFTurbo Complete"
            }
        }

    @web_app.get("/download/{job_id}/{model_name}/all.zip")
    async def download_zip(job_id: str, model_name: str):
        """Download all files as ZIP with streaming from volume"""
        
        volume.reload()  # Force volume reload for latest state
        
        # KORREKTUR: Vereinfachter und korrekter Pfad
        model_output_dir = Path(storage_path) / job_id / "output" / model_name
        
        if not model_output_dir.is_dir():
            raise HTTPException(404, "Job files not found")
        
        # Create ZIP in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for wav_file in model_output_dir.glob("*.wav"):
                zip_file.write(wav_file, wav_file.name)
        
        zip_buffer.seek(0)
        
        return StreamingResponse(
            io.BytesIO(zip_buffer.read()),
            media_type="application/zip",
            headers={
                "Content-Disposition": "attachment; filename=zfturbo_stems.zip",
                "Access-Control-Allow-Origin": "*",
            }
        )

    @web_app.get("/download/{job_id}/{model_name}/{filename}")
    async def download_file(job_id: str, model_name: str, filename: str):
        """Download individual file with streaming from volume"""
        
        volume.reload()  # Force volume reload for latest state
        
        # KORREKTUR: Vereinfachter und korrekter Pfad
        file_path = Path(storage_path) / job_id / "output" / model_name / filename
        
        if not file_path.exists():
            raise HTTPException(404, f"File not found: {filename}")

        def file_iterator():
            with open(file_path, "rb") as f:
                while chunk := f.read(8192):
                    yield chunk
        
        return StreamingResponse(
            file_iterator(),
            media_type="audio/wav",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Access-Control-Allow-Origin": "*",
            }
        )

    @web_app.get("/preview/{job_id}/{model_name}/{filename}")
    async def preview_file(job_id: str, model_name: str, filename: str):
        """Stream 30s MP3 preview for a stem"""
        volume.reload()
        
        # KORREKTUR: Vereinfachter und korrekter Pfad
        preview_mp3 = Path(storage_path) / job_id / "output" / model_name / filename
        
        if not preview_mp3.exists():
            # Try .wav if .mp3 not found
            preview_wav = preview_mp3.with_suffix('.wav')
            if preview_wav.exists():
                def file_iterator():
                    with open(preview_wav, "rb") as f:
                        while chunk := f.read(8192):
                            yield chunk
                print(f"⚠️ MP3-Vorschau nicht gefunden, sende WAV: {preview_wav}")
                return StreamingResponse(
                    file_iterator(),
                    media_type="audio/wav",
                    headers={
                        "Content-Disposition": f"inline; filename={preview_wav.name}",
                        "Access-Control-Allow-Origin": "*",
                    }
                )
            print(f"❌ Vorschau-Datei nicht gefunden: {preview_mp3} und {preview_wav}")
            raise HTTPException(404, f"Preview file not found: {filename}")
        def file_iterator():
            with open(preview_mp3, "rb") as f:
                while chunk := f.read(8192):
                    yield chunk
        print(f"✅ Sende MP3-Vorschau: {preview_mp3}")
        return StreamingResponse(
            file_iterator(),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": f"inline; filename={preview_mp3.name}",
                "Access-Control-Allow-Origin": "*",
            }
        )

    @web_app.options("/{path:path}")
    async def options_handler(path: str):
        """Handle CORS preflight requests"""
        return {"status": "ok"}

    
    return web_app

# Deploy FastAPI app using Modal's ASGI pattern
@app.function(image=zfturbo_image, volumes={storage_path: volume})
@modal.asgi_app()
def fastapi_app():
    return create_fastapi_app()

if __name__ == "__main__":
    print("🚀 Klein Digital Solutions - Music AI Separator")
    print("📡 ZFTurbo Complete Implementation - Modal Serverless")
    print("🔬 Repository: ZFTurbo/Music-Source-Separation-Training")
    print("💡 Deploy: modal deploy modal_app_zfturbo_complete.py")