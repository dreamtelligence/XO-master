#!/usr/bin/env python3
"""
Klein Digital Solutions - Matchering 2.0 AI Mastering Service
Modal Serverless Deployment with A10G GPU
Professional Audio Mastering with Reference Matching
"""

import modal
import os
from pathlib import Path
import tempfile
import uuid
import time
import json
import zipfile
import io

# Global storage for temporary files
temp_files_storage = {}
# Status dictionary for job progress
job_status = {}

# Modal app instance
app = modal.App("matchering-ai-mastering")

# Create persistent volume for file storage
volume = modal.Volume.from_name("matchering-files-storage", create_if_missing=True)
storage_path = "/vol/matchering_files"

# Matchering 2.0 Docker image with all dependencies
matchering_image = modal.Image.debian_slim(python_version="3.11").apt_install([
    "ffmpeg",
    "libsndfile1",
    "libsndfile1-dev",
    "build-essential",
    "python3-dev",
    "pkg-config"
]).pip_install([
    # Core dependencies
    "soundfile>=0.12.1",
    "numpy>=1.21.0",
    "scipy>=1.7.0",
    "librosa>=0.9.0",
    
    # Audio processing for automatic mastering
    "pydub>=0.25.0",
    "pedalboard>=0.8.1",  # Spotify's audio effects library
    "pyloudnorm>=0.1.0",  # LUFS measurement for professional mastering
    
    # FastAPI stack
    "fastapi[standard]",
    "python-multipart>=0.0.6",
    
    # Additional audio processing
    "pydub>=0.25.0",
    "mutagen>=1.45.0"
])

def save_job_status(job_id: str, status_data: dict):
    """Save job status to volume for persistence"""
    try:
        status_file = Path(storage_path) / f"status_{job_id}.json"
        with open(status_file, 'w') as f:
            json.dump(status_data, f)
        # Force commit for status updates
        volume.commit()
        print(f"📊 Mastering status saved for job {job_id}: {status_data.get('progress', 0)}% - {status_data.get('phase', 'Unknown')}")
    except Exception as e:
        print(f"⚠️ Error saving mastering job status: {e}")

@app.function(
    image=matchering_image,
    timeout=900,  # 15 minutes should be enough for mastering
    memory=8192,  # 8GB memory for audio processing
    volumes={storage_path: volume},
    scaledown_window=60
)
def automatic_master_audio(
    target_audio_data: bytes, 
    target_filename: str,
    job_id: str,
    mastering_intensity: str = "medium",
    output_formats: list = ["16bit", "24bit"],
    bass_mono_making: bool = True,
    intelligent_eq: bool = True,
    lufs_targeting: bool = True
) -> dict:
    """
    Automatic AI Mastering - LANDR-style mastering without reference
    Based on 2025 best practices for automatic mastering chain
    """
    start_time = time.time()
    
    # Set initial job status
    job_status[job_id] = {
        "status": "processing",
        "progress": 5,
        "phase": "Initialisierung",
        "error": None,
        "processing_time": None
    }
    
    try:
        # Setup directories
        job_dir = Path(storage_path) / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        
        # Save input file
        target_file = job_dir / f"target_{target_filename}"
        target_file.write_bytes(target_audio_data)
        
        output_dir = job_dir / "output"
        output_dir.mkdir(exist_ok=True)
        
        print(f"🎚️ Starting Automatic AI Mastering for job {job_id}")
        print(f"📁 Target: {target_file} ({len(target_audio_data) // 1024} KB)")
        print(f"🎯 Intensity: {mastering_intensity}")
        
        # Update progress
        job_status[job_id] = {
            "status": "processing",
            "progress": 20,
            "phase": "Audio wird analysiert",
            "error": None,
            "processing_time": None
        }
        save_job_status(job_id, job_status[job_id])
        
        # Convert to WAV if needed
        import subprocess
        
        target_wav = job_dir / "target.wav"
        print(f"🔍 Input file: {target_file} (exists: {target_file.exists()}, size: {target_file.stat().st_size if target_file.exists() else 'N/A'})")
        print(f"🔍 Output file: {target_wav}")
        
        if not target_filename.lower().endswith('.wav'):
            # First try to probe the file
            probe_cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration,format_name",
                "-of", "default=noprint_wrappers=1",
                str(target_file)
            ]
            try:
                probe_result = subprocess.run(probe_cmd, check=True, capture_output=True, text=True, timeout=30)
                print(f"📊 File probe result: {probe_result.stdout}")
            except Exception as probe_error:
                print(f"⚠️ File probe failed: {probe_error}")
            
            # Try conversion with multiple fallback options
            conversion_attempts = [
                # Standard conversion
                [
                    "ffmpeg", "-y", "-v", "error",
                    "-i", str(target_file),
                    "-ar", "44100", "-ac", "2",
                    "-acodec", "pcm_s16le",
                    str(target_wav)
                ],
                # More compatible conversion
                [
                    "ffmpeg", "-y", "-v", "error",
                    "-i", str(target_file),
                    "-ar", "44100", "-ac", "2",
                    "-f", "wav",
                    str(target_wav)
                ],
                # Force format interpretation
                [
                    "ffmpeg", "-y", "-v", "error",
                    "-f", "mp3", "-i", str(target_file),
                    "-ar", "44100", "-ac", "2",
                    "-acodec", "pcm_s16le",
                    str(target_wav)
                ]
            ]
            
            conversion_successful = False
            for i, ffmpeg_cmd in enumerate(conversion_attempts):
                try:
                    print(f"🔄 Conversion attempt {i+1}: {' '.join(ffmpeg_cmd)}")
                    result = subprocess.run(ffmpeg_cmd, check=True, capture_output=True, text=True, timeout=120)
                    print(f"✅ Converted target to WAV: {target_wav}")
                    conversion_successful = True
                    break
                except subprocess.CalledProcessError as e:
                    print(f"❌ Conversion attempt {i+1} failed:")
                    print(f"   Return code: {e.returncode}")
                    print(f"   STDERR: {e.stderr}")
                    if i < len(conversion_attempts) - 1:
                        print(f"   Trying next method...")
                    continue
                except subprocess.TimeoutExpired:
                    print(f"❌ Conversion attempt {i+1} timed out")
                    continue
            
            if not conversion_successful:
                raise Exception(f"All audio conversion attempts failed for file: {target_filename}")
                
        else:
            import shutil
            shutil.copy2(target_file, target_wav)
            print(f"✅ Copied WAV file: {target_wav}")
        
        # Update progress
        job_status[job_id] = {
            "status": "processing",
            "progress": 40,
            "phase": "Automatic AI Mastering Chain läuft",
            "error": None,
            "processing_time": None
        }
        save_job_status(job_id, job_status[job_id])
        
        # Load audio for processing
        import soundfile as sf
        import numpy as np
        import pyloudnorm as pyln
        from pedalboard import Pedalboard, Compressor, Limiter, HighpassFilter, LowpassFilter, Gain, PeakFilter
        from pedalboard.io import AudioFile
        from scipy import signal
        
        print(f"🎯 Running Automatic Mastering Chain...")
        
        # Read audio file
        with AudioFile(str(target_wav)) as f:
            audio = f.read(f.frames)
            sample_rate = f.samplerate
        
        print(f"📊 Audio loaded: {audio.shape[1] if len(audio.shape) > 1 else 1} channels, {sample_rate} Hz")
        
        # ===================================================================
        # 🎯 LUFS-ZIELWERT KONFIGURATION (Industry Standards 2025)
        # ===================================================================
        
        # LUFS-Zielwerte basierend auf Mastering-Intensität
        if mastering_intensity == "low":
            target_lufs = -16.0     # Sehr dynamisch, audiophil
            print("🎯 LUFS-Ziel: -16.0 LUFS (Dynamisches Mastering)")
        elif mastering_intensity == "high": 
            target_lufs = -9.0      # Sehr laut, Club/Radio
            print("🎯 LUFS-Ziel: -9.0 LUFS (Lautes Club/Radio Mastering)")
        else:  # medium
            target_lufs = -14.0     # Streaming-Standard (Spotify, Apple Music)
            print("🎯 LUFS-Ziel: -14.0 LUFS (Streaming-Standard)")
        
        # ===================================================================
        # 🔊 INTELLIGENTE BASS-BEARBEITUNG (Mono-Making für Punch)
        # ===================================================================
        if bass_mono_making:
            print("🔊 Starting intelligent bass processing...")
            if len(audio.shape) > 1 and audio.shape[0] == 2:
                bass_crossover_freq = 150.0
                from scipy.signal import butter, filtfilt
                nyquist = sample_rate / 2
                bass_cutoff = bass_crossover_freq / nyquist
                bass_b, bass_a = butter(4, bass_cutoff, btype='low')
                highs_b, highs_a = butter(4, bass_cutoff, btype='high')
                bass_band = np.array([
                    filtfilt(bass_b, bass_a, audio[0]),
                    filtfilt(bass_b, bass_a, audio[1])
                ])
                highs_band = np.array([
                    filtfilt(highs_b, highs_a, audio[0]),
                    filtfilt(highs_b, highs_a, audio[1])
                ])
                bass_mono = (bass_band[0] + bass_band[1]) / 2
                bass_band_mono = np.array([bass_mono, bass_mono])
                audio = bass_band_mono + highs_band
                print(f"✅ Bass Mono-Making: Frequenzen unter {bass_crossover_freq}Hz sind jetzt mono")
                print("🔊 Resultat: Druckvoller, zentrierter Bass + breite Stereo-Höhen")
            else:
                print("ℹ️ Mono-Audio erkannt - Bass Mono-Making übersprungen")
        else:
            print("⏭️ Bass Mono-Making vom Nutzer deaktiviert.")
        
        # Original Audio als Backup für LUFS-Vergleich
        original_audio = audio.copy()
        
        # ===================================================================
        # 🎛️ INTELLIGENTE FREQUENZ-ANALYSE (2025 Best Practices)
        # ===================================================================
        if intelligent_eq:
            rms = np.sqrt(np.mean(audio**2))
            peak = np.max(np.abs(audio))
            dynamic_range = peak / rms if rms > 0 else 1.0
            print(f"📈 Audio Analysis: RMS={rms:.3f}, Peak={peak:.3f}, Dynamic Range={dynamic_range:.2f}")
            if len(audio.shape) > 1:
                mono_audio = np.mean(audio, axis=0)
            else:
                mono_audio = audio
            fft = np.fft.rfft(mono_audio)
            freqs = np.fft.rfftfreq(len(mono_audio), 1/sample_rate)
            magnitude = np.abs(fft)
            bass_range = (20, 200)
            low_mid_range = (200, 800)
            mid_range = (800, 4000)
            high_range = (4000, 20000)
            def analyze_frequency_band(freq_range):
                mask = (freqs >= freq_range[0]) & (freqs <= freq_range[1])
                band_energy = np.sum(magnitude[mask])
                total_energy = np.sum(magnitude)
                return band_energy / total_energy if total_energy > 0 else 0
            bass_energy = analyze_frequency_band(bass_range)
            low_mid_energy = analyze_frequency_band(low_mid_range)
            mid_energy = analyze_frequency_band(mid_range)
            high_energy = analyze_frequency_band(high_range)
            print(f"🎛️ Frequency Analysis:")
            print(f"   Bass (20-200Hz): {bass_energy:.3f} ({bass_energy*100:.1f}%)")
            print(f"   Low-Mid (200-800Hz): {low_mid_energy:.3f} ({low_mid_energy*100:.1f}%)")
            print(f"   Mid (800-4kHz): {mid_energy:.3f} ({mid_energy*100:.1f}%)")
            print(f"   High (4-20kHz): {high_energy:.3f} ({high_energy*100:.1f}%)")
        else:
            print("⏭️ Intelligente Frequenz-Analyse vom Nutzer deaktiviert.")
            rms = np.sqrt(np.mean(audio**2))
            peak = np.max(np.abs(audio))
            dynamic_range = peak / rms if rms > 0 else 1.0
            bass_energy = 0.2
            low_mid_energy = 0.3
            mid_energy = 0.3
            high_energy = 0.2
        
        # ===================================================================
        # 🧠 INTELLIGENTE PARAMETER-ANPASSUNG (AI-inspired)
        # ===================================================================
        
        # Bass-Problem-Erkennung (wie bei AI Mastering Services)
        bass_is_problematic = bass_energy > 0.35  # Mehr als 35% der Energie im Bass
        bass_is_weak = bass_energy < 0.15         # Weniger als 15% der Energie im Bass
        
        # Mid-Range Analyse (Vocal-Bereich)
        vocal_energy = mid_energy + low_mid_energy
        vocal_is_prominent = vocal_energy > 0.45
        vocal_is_weak = vocal_energy < 0.25
        
        # High-Frequency Analyse
        high_is_harsh = high_energy > 0.25        # Zu viel High-End
        high_is_dull = high_energy < 0.08         # Zu wenig High-End
        
        print(f"🔍 Intelligent Detection:")
        print(f"   Bass problematic: {bass_is_problematic} | Bass weak: {bass_is_weak}")
        print(f"   Vocal prominent: {vocal_is_prominent} | Vocal weak: {vocal_is_weak}")
        print(f"   High harsh: {high_is_harsh} | High dull: {high_is_dull}")
        
        # ===================================================================
        # 🎛️ INTELLIGENTE MULTI-BAND PARAMETER-BERECHNUNG
        # ===================================================================
        
        # Basis-Parameter nach Intensität
        if mastering_intensity == "low":
            base_comp_threshold = -12.0
            base_comp_ratio = 1.5
            limit_threshold = -2.0
            eq_boost = 0.5
        elif mastering_intensity == "high":
            base_comp_threshold = -20.0
            base_comp_ratio = 3.0
            limit_threshold = -0.5
            eq_boost = 2.0
        else:  # medium (default)
            base_comp_threshold = -16.0
            base_comp_ratio = 2.0
            limit_threshold = -1.0
            eq_boost = 1.0
        
        # ===================================================================
        # 🧠 AI-INSPIRIERTE MULTI-BAND-KONFIGURATION
        # ===================================================================
        
        # Bass-Band Kompressor (20-200Hz) - Intelligente Anpassung
        if bass_is_problematic:
            # Zu viel Bass - aggressiver komprimieren
            bass_threshold = base_comp_threshold + 5.0  # Früher eingreifen
            bass_ratio = base_comp_ratio + 1.5          # Stärker komprimieren
            bass_attack = 15.0                          # Schneller Angriff
            bass_release = 80.0                         # Mittlere Release
            print("🎛️ Bass-Korrektur: Problematischer Bass wird reduziert")
        elif bass_is_weak:
            # Zu wenig Bass - sanfter behandeln, mehr durchlassen
            bass_threshold = base_comp_threshold - 8.0  # Später eingreifen
            bass_ratio = 1.2                           # Minimal komprimieren
            bass_attack = 50.0                         # Langsamer Angriff
            bass_release = 150.0                       # Längere Release
            print("🎛️ Bass-Boost: Schwacher Bass wird verstärkt")
        else:
            # Normaler Bass - Standard-Behandlung
            bass_threshold = base_comp_threshold
            bass_ratio = base_comp_ratio * 0.8
            bass_attack = 25.0
            bass_release = 100.0
            print("🎛️ Bass-Balance: Normaler Bass, Standard-Behandlung")
        
        # Mid-Band Kompressor (200-4000Hz) - Vocal-Bereich
        if vocal_is_prominent:
            # Zu prominente Vocals/Mids - sanft kontrollieren
            mid_threshold = base_comp_threshold + 2.0
            mid_ratio = base_comp_ratio * 0.9
            mid_attack = 20.0
            mid_release = 60.0
            print("🎛️ Mid-Kontrolle: Prominente Vocals werden sanft kontrolliert")
        elif vocal_is_weak:
            # Schwache Vocals - weniger komprimieren
            mid_threshold = base_comp_threshold - 5.0
            mid_ratio = 1.1                           # Minimal komprimieren
            mid_attack = 35.0
            mid_release = 120.0
            print("🎛️ Mid-Boost: Schwache Vocals werden unterstützt")
        else:
            # Normale Vocals - Standard
            mid_threshold = base_comp_threshold + 1.0
            mid_ratio = base_comp_ratio * 0.7         # Sanfter für Vocals
            mid_attack = 25.0
            mid_release = 80.0
            print("🎛️ Mid-Balance: Normale Vocals, Standard-Behandlung")
        
        # High-Band Kompressor (4000Hz+) - Höhen/Brillanz
        if high_is_harsh:
            # Zu aggressive Höhen - stark kontrollieren
            high_threshold = base_comp_threshold + 3.0
            high_ratio = base_comp_ratio + 0.5
            high_attack = 5.0                         # Sehr schnell für Peaks
            high_release = 40.0
            print("🎛️ High-Kontrolle: Harte Höhen werden gezähmt")
        elif high_is_dull:
            # Zu dumpfe Höhen - wenig komprimieren
            high_threshold = base_comp_threshold - 10.0
            high_ratio = 1.1
            high_attack = 15.0
            high_release = 100.0
            print("🎛️ High-Boost: Dumpfe Höhen werden aufgehellt")
        else:
            # Normale Höhen
            high_threshold = base_comp_threshold - 2.0
            high_ratio = base_comp_ratio * 0.8
            high_attack = 10.0
            high_release = 60.0
            print("🎛️ High-Balance: Normale Höhen, Standard-Behandlung")
        
        # Anpassung basierend auf Dynamik-Umfang
        if dynamic_range > 10:
            # Sehr dynamisch - alle Schwellen senken
            bass_threshold -= 2.0
            mid_threshold -= 2.0
            high_threshold -= 2.0
            limit_threshold -= 0.5
            print("🎛️ Dynamik-Anpassung: Hohe Dynamik erkannt, sanftere Kompression")
        elif dynamic_range < 3:
            # Bereits komprimiert - weniger aggressiv
            bass_ratio *= 0.8
            mid_ratio *= 0.8
            high_ratio *= 0.8
            limit_threshold -= 0.3
            print("🎛️ Dynamik-Anpassung: Geringe Dynamik erkannt, reduzierte Kompression")
        
        print(f"🎛️ Final Multi-Band Parameters:")
        print(f"   Bass Band: Threshold={bass_threshold:.1f}dB, Ratio={bass_ratio:.1f}:1")
        print(f"   Mid Band: Threshold={mid_threshold:.1f}dB, Ratio={mid_ratio:.1f}:1")
        print(f"   High Band: Threshold={high_threshold:.1f}dB, Ratio={high_ratio:.1f}:1")
        print(f"   Final Limiter: Threshold={limit_threshold:.1f}dB")
        
        # ===================================================================
        # 🎚️ PROFESSIONELLE MASTERING-CHAIN (2025 Best Practices)
        # ===================================================================
        
        # ===================================================================
        # 🎛️ ALTERNATIVE MULTI-BAND IMPLEMENTIERUNG 
        # (Da MultibandCompressor nicht verfügbar ist, verwenden wir Frequenz-spezifische Bearbeitung)
        # ===================================================================
        
        # Berechne intelligente EQ-Anpassungen basierend auf Frequenz-Analyse
        bass_adjustment = 0.0
        mid_adjustment = 0.0
        high_adjustment = 0.0
        
        if bass_is_problematic:
            bass_adjustment = -2.0  # Bass reduzieren
            print("🎛️ EQ: Bass wird um 2dB reduziert")
        elif bass_is_weak:
            bass_adjustment = 1.5   # Bass anheben
            print("🎛️ EQ: Bass wird um 1.5dB angehoben")
        
        if vocal_is_weak:
            mid_adjustment = 1.0    # Mids für Vocals anheben
            print("🎛️ EQ: Mids werden um 1dB angehoben")
        elif vocal_is_prominent:
            mid_adjustment = -0.5   # Mids leicht reduzieren
            print("🎛️ EQ: Mids werden um 0.5dB reduziert")
        
        if high_is_harsh:
            high_adjustment = -1.5  # Harte Höhen reduzieren
            print("🎛️ EQ: Höhen werden um 1.5dB reduziert")
        elif high_is_dull:
            high_adjustment = 2.0   # Dumpfe Höhen aufhellen
            print("🎛️ EQ: Höhen werden um 2dB angehoben")
        
        # Hauptkompressor-Parameter (gewichtet nach problematischsten Frequenzen)
        main_threshold = base_comp_threshold
        main_ratio = base_comp_ratio
        main_attack = 25.0
        main_release = 80.0
        
        # Anpassungen basierend auf dominanten Problemen
        if bass_is_problematic:
            # Bass-Problem ist dominant - aggressivere Kompression
            main_threshold += 3.0
            main_ratio += 0.5
            main_attack = 15.0  # Schneller für Bass-Kontrolle
            print("🎛️ Kompressor: Angepasst für Bass-Problem")
        elif high_is_harsh:
            # Höhen-Problem ist dominant - schnelle Attack für Peaks
            main_attack = 8.0
            main_ratio += 0.3
            print("🎛️ Kompressor: Angepasst für Höhen-Problem")
        elif vocal_is_prominent:
            # Vocal-Problem - sanftere Behandlung
            main_threshold -= 2.0
            main_ratio *= 0.9
            main_attack = 30.0
            print("🎛️ Kompressor: Angepasst für Vocal-Kontrolle")
        
        board = Pedalboard([
            # 1. High-pass filter to remove sub-bass rumble
            HighpassFilter(cutoff_frequency_hz=30),
            
            # ===================================================================
            # 🧠 INTELLIGENTE FREQUENZ-SPEZIFISCHE EQ-ANPASSUNGEN
            # ===================================================================
            
            # Bass-Anpassung (80Hz - typischer Bass-Fundamental)
            PeakFilter(
                cutoff_frequency_hz=80,
                gain_db=bass_adjustment,
                q=0.7  # Moderate Q für natürlichen Sound
            ) if abs(bass_adjustment) > 0.1 else Gain(gain_db=0),
            
            # Low-Mid Anpassung (400Hz - Vocal-Body/Wärme)
            PeakFilter(
                cutoff_frequency_hz=400,
                gain_db=mid_adjustment * 0.6,  # Subtiler im Low-Mid
                q=0.8
            ) if abs(mid_adjustment) > 0.1 else Gain(gain_db=0),
            
            # Mid-Anpassung (1.5kHz - Vocal-Präsenz)
            PeakFilter(
                cutoff_frequency_hz=1500,
                gain_db=mid_adjustment,
                q=1.0
            ) if abs(mid_adjustment) > 0.1 else Gain(gain_db=0),
            
            # High-Mid Anpassung (3kHz - Klarheit)
            PeakFilter(
                cutoff_frequency_hz=3000,
                gain_db=high_adjustment * 0.7,  # Subtiler
                q=1.2
            ) if abs(high_adjustment) > 0.1 else Gain(gain_db=0),
            
            # High-Anpassung (8kHz - Brillanz)
            PeakFilter(
                cutoff_frequency_hz=8000,
                gain_db=high_adjustment,
                q=1.0
            ) if abs(high_adjustment) > 0.1 else Gain(gain_db=0),
            
            # Air-Band (12kHz - Luftigkeit)
            PeakFilter(
                cutoff_frequency_hz=12000,
                gain_db=high_adjustment * 0.5,  # Noch subtiler für Air
                q=0.8
            ) if high_adjustment > 0.5 else Gain(gain_db=0),
            
            # ===================================================================
            # 🎚️ INTELLIGENTER HAUPT-KOMPRESSOR
            # ===================================================================
            Compressor(
                threshold_db=main_threshold,
                ratio=main_ratio,
                attack_ms=main_attack,
                release_ms=main_release
            ),
            
            # ===================================================================
            # 🎛️ FREQUENZ-SPEZIFISCHE NACHBEARBEITUNG
            # ===================================================================
            
            # Sanfte Bass-Kontrolle nach EQ (falls Bass immer noch problematisch)
            Compressor(
                threshold_db=bass_threshold,
                ratio=max(1.2, bass_ratio * 0.6),  # Sanfter Nachkompressor
                attack_ms=20.0,
                release_ms=100.0
            ) if bass_is_problematic else Gain(gain_db=0),
            
            # High-Frequency Limiter (für harsche Höhen)
            Compressor(
                threshold_db=high_threshold,
                ratio=max(1.3, high_ratio * 0.7),  # Sanfter für Höhen
                attack_ms=5.0,  # Sehr schnell für Peaks
                release_ms=50.0
            ) if high_is_harsh else Gain(gain_db=0),
            
            # ===================================================================
            # 🎚️ FINAL GLUE & LIMITING
            # ===================================================================
            
            # Final "Glue" Kompressor für Gesamt-Kohäsion
            Compressor(
                threshold_db=base_comp_threshold - 5.0,  # Sanfter Final-Kompressor
                ratio=1.3,                               # Sehr sanft für "Glue"
                attack_ms=50.0,
                release_ms=120.0
            ),
            
            # Overall subtle boost basierend auf Intensität
            Gain(gain_db=eq_boost * 0.3),
            
            # Final Limiting für Loudness und Safety
            Limiter(
                threshold_db=limit_threshold,
                release_ms=50.0
            ),
            
            # Safety high-cut to prevent aliasing
            LowpassFilter(cutoff_frequency_hz=20000)
        ])
        
        # Process audio through mastering chain
        print("🎚️ Processing through mastering chain...")
        mastered_audio = board(audio, sample_rate)
        
        # ===================================================================
        # 🎯 LUFS-TARGETING (Industry Standard Loudness Mastering)
        # ===================================================================
        if lufs_targeting:
            print("🎯 Starting LUFS-Targeting for professional loudness...")
            try:
                if len(mastered_audio.shape) > 1:
                    audio_for_lufs = mastered_audio.T
                else:
                    audio_for_lufs = mastered_audio
                meter = pyln.Meter(sample_rate)
                current_lufs = meter.integrated_loudness(audio_for_lufs)
                print(f"📊 Aktuelle LUFS: {current_lufs:.1f} LUFS")
                print(f"🎯 Ziel-LUFS: {target_lufs:.1f} LUFS")
                lufs_difference = target_lufs - current_lufs
                print(f"🔧 LUFS-Differenz: {lufs_difference:+.1f} dB")
                if abs(lufs_difference) > 0.5:
                    print(f"🎚️ Anpassung um {lufs_difference:+.1f} dB für LUFS-Ziel...")
                    lufs_adjustment_chain = Pedalboard([
                        Gain(gain_db=lufs_difference),
                        Limiter(
                            threshold_db=-0.2,
                            release_ms=30.0
                        )
                    ])
                    mastered_audio = lufs_adjustment_chain(mastered_audio, sample_rate)
                    if len(mastered_audio.shape) > 1:
                        final_audio_for_lufs = mastered_audio.T
                    else:
                        final_audio_for_lufs = mastered_audio
                    final_lufs = meter.integrated_loudness(final_audio_for_lufs)
                    print(f"✅ Finale LUFS: {final_lufs:.1f} LUFS (Ziel: {target_lufs:.1f} LUFS)")
                    print(f"🎯 LUFS-Präzision: {abs(final_lufs - target_lufs):.1f} dB Abweichung")
                    if abs(final_lufs - target_lufs) <= 1.0:
                        print("🎉 LUFS-Targeting erfolgreich!")
                    else:
                        print("⚠️ LUFS-Targeting teilweise erfolgreich")
                else:
                    print("✅ LUFS bereits im Zielbereich - keine Anpassung nötig")
                    final_lufs = current_lufs
            except Exception as e:
                print(f"⚠️ LUFS-Messung fehlgeschlagen: {e}")
                print("🔄 Fallback: Standard-Normalisierung wird verwendet")
                final_lufs = "N/A"
                mastered_peak = np.max(np.abs(mastered_audio))
                if mastered_peak > 0.95:
                    mastered_audio = mastered_audio * (0.95 / mastered_peak)
        else:
            print("⏭️ LUFS-Targeting vom Nutzer deaktiviert.")
            final_lufs = "N/A"
        
        # Final Safety Check
        mastered_peak = np.max(np.abs(mastered_audio))
        if mastered_peak > 0.98:
            mastered_audio = mastered_audio * (0.95 / mastered_peak)
            print("🛡️ Safety-Normalisierung angewendet")
        
        print("✅ Professional LUFS-Targeting Mastering completed!")
        
        # Füge LUFS-Info zum Status hinzu
        if isinstance(final_lufs, (int, float)):
            print(f"📊 Master-Statistiken:")
            print(f"   Final LUFS: {final_lufs:.1f} LUFS")
            print(f"   Target LUFS: {target_lufs:.1f} LUFS")
            print(f"   Peak Level: {mastered_peak:.3f} (-{20*np.log10(mastered_peak):.1f} dBFS)")
        
        print("✅ Automatic mastering completed successfully")
        
        # Update progress
        job_status[job_id] = {
            "status": "processing",
            "progress": 80,
            "phase": "Dateien werden finalisiert",
            "error": None,
            "processing_time": None
        }
        save_job_status(job_id, job_status[job_id])
        
        # Save output files in requested formats
        output_files = []
        
        if "16bit" in output_formats:
            output_16bit = output_dir / "mastered_16bit.wav"
            sf.write(str(output_16bit), mastered_audio.T, sample_rate, subtype='PCM_16')
            output_files.append("mastered_16bit.wav")
            print(f"✅ Saved 16-bit master: {output_16bit}")
        
        if "24bit" in output_formats:
            output_24bit = output_dir / "mastered_24bit.wav"
            sf.write(str(output_24bit), mastered_audio.T, sample_rate, subtype='PCM_24')
            output_files.append("mastered_24bit.wav")
            print(f"✅ Saved 24-bit master: {output_24bit}")
        
        if not output_files:
            raise Exception("No output files were created")
        
        # Calculate statistics
        total_size = sum((output_dir / f).stat().st_size for f in output_files)
        processing_time = round(time.time() - start_time, 2)
        
        # Save volume changes
        volume.commit()
        
        # Update final job status
        job_status[job_id] = {
            "status": "completed",
            "progress": 100,
            "phase": "Fertig - Automatic Mastering abgeschlossen",
            "error": None,
            "processing_time": processing_time,
            "files": output_files,
            "total_size_mb": round(total_size / (1024*1024), 1),
            "download_base_url": f"/download/mastering/{job_id}"
        }
        
        # Persist status to volume
        save_job_status(job_id, job_status[job_id])
        
        print(f"🎉 Automatic Mastering job {job_id} completed with {len(output_files)} files")
        
        return {
            "success": True,
            "files": output_files,
            "job_id": job_id,
            "processing_time": processing_time,
            "total_size": total_size,
            "service": "Automatic AI Mastering",
            "target_file": target_filename,
            "mastering_intensity": mastering_intensity,
            "output_formats": output_formats
        }
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Automatic mastering failed: {error_msg}")
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

# FastAPI web application
def create_matchering_app():
    from fastapi import FastAPI, File, Form, UploadFile, HTTPException
    from fastapi.responses import StreamingResponse
    from fastapi.middleware.cors import CORSMiddleware

    web_app = FastAPI(
        title="Matchering 2.0 AI Mastering Service",
        description="Professional audio mastering using reference tracks with Matchering 2.0",
        version="1.0.0"
    )

    # CORS middleware
    web_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @web_app.post("/master")
    async def api_master(
        target_audio: UploadFile = File(..., description="Audio file to be mastered"),
        mastering_intensity: str = Form("medium", description="Mastering intensity: low, medium, high"),
        output_formats: str = Form("16bit,24bit", description="Output formats: 16bit, 24bit, or both"),
        bass_mono_making: bool = Form(True),
        intelligent_eq: bool = Form(True),
        lufs_targeting: bool = Form(True)
    ):
        """
        Main API endpoint for Automatic AI Mastering - No reference track needed
        """
        from fastapi import Response
        
        try:
            print(f"🎚️ Received automatic mastering request:")
            print(f"   Target: {target_audio.filename}")
            print(f"   Intensity: {mastering_intensity}")
            
            # Validate file formats
            allowed_extensions = ['.mp3', '.wav', '.flac', '.m4a', '.aac']
            
            if not any(target_audio.filename.lower().endswith(ext) for ext in allowed_extensions):
                raise HTTPException(400, f"Unsupported target file format. Allowed: {', '.join(allowed_extensions)}")
            
            # Read audio file
            target_data = await target_audio.read()
            
            if len(target_data) == 0:
                raise HTTPException(400, "Empty audio file uploaded")
            
            # File size limit (50MB)
            max_size = 50 * 1024 * 1024
            if len(target_data) > max_size:
                raise HTTPException(400, f"Target file too large (max {max_size // 1024 // 1024}MB)")
            
            # Validate mastering intensity
            if mastering_intensity not in ["low", "medium", "high"]:
                mastering_intensity = "medium"
            
            # Parse output formats
            formats = [f.strip() for f in output_formats.split(",") if f.strip() in ["16bit", "24bit"]]
            if not formats:
                formats = ["16bit", "24bit"]
            
            # Generate job ID
            job_id = str(uuid.uuid4())
            
            print(f"🎚️ Starting async Automatic Mastering processing")
            
            # Initialize job status
            job_status[job_id] = {
                "status": "queued",
                "progress": 0,
                "phase": "Upload abgeschlossen, Automatic Mastering wird vorbereitet...",
                "error": None,
                "processing_time": None,
                "files": [],
                "total_size_mb": 0
            }
            
            # Start async processing
            automatic_master_audio.spawn(
                target_data, 
                target_audio.filename,
                job_id,
                mastering_intensity,
                formats,
                bass_mono_making,
                intelligent_eq,
                lufs_targeting
            )
            
            response_data = {
                "job_id": job_id,
                "status": "queued",
                "message": "Automatic Mastering started. Use /status/mastering/{job_id} to check progress.",
                "target_file": target_audio.filename,
                "mastering_intensity": mastering_intensity,
                "output_formats": formats
            }
            
            print(f"🔄 Automatic Mastering job {job_id} queued for processing")
            
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
            print(f"❌ Unexpected Automatic Mastering error: {str(e)}")
            raise HTTPException(500, f"Unexpected Automatic Mastering error: {str(e)}")

    @web_app.get("/status/mastering/{job_id}")
    async def mastering_status(job_id: str):
        """Status API for mastering progress"""
        # Always check volume first for latest status
        volume.reload()
        status_file = Path(storage_path) / f"status_{job_id}.json"
        
        if status_file.exists():
            try:
                with open(status_file, 'r') as f:
                    status = json.load(f)
                print(f"📊 Mastering status loaded from volume for job {job_id}: {status.get('progress', 0)}% - {status.get('phase', 'Unknown')}")
                return status
            except Exception as e:
                print(f"Error loading mastering status from volume: {e}")
        
        # Fallback to in-memory status
        status = job_status.get(job_id)
        if status:
            print(f"📊 Mastering status loaded from memory for job {job_id}: {status.get('progress', 0)}% - {status.get('phase', 'Unknown')}")
            return status
        
        print(f"❌ No mastering status found for job {job_id}")
        return {"status": "unknown", "progress": 0, "phase": "Nicht gefunden", "error": "Job nicht gefunden"}

    @web_app.get("/health")
    async def health():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "service": "Klein Digital Solutions - Automatic AI Mastering",
            "version": "Automatic Mastering 1.0+",
            "description": "Professional automatic audio mastering without reference tracks",
            "max_file_size": "50MB",
            "supported_formats": ["MP3", "WAV", "FLAC", "M4A", "AAC"],
            "output_formats": ["16-bit PCM", "24-bit PCM"],
            "mastering_intensities": ["low", "medium", "high"]
        }

    @web_app.get("/download/mastering/{job_id}/all.zip")
    async def download_mastered_zip(job_id: str):
        """Download all mastered files as ZIP"""
        
        volume.reload()  # Force volume reload for latest state
        
        # Construct directory path
        output_dir = Path(storage_path) / job_id / "output"
        
        if not output_dir.is_dir():
            raise HTTPException(404, "Mastered files not found")
        
        # Create ZIP in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for audio_file in output_dir.glob("*.wav"):
                zip_file.write(audio_file, audio_file.name)
        
        zip_buffer.seek(0)
        
        return StreamingResponse(
            io.BytesIO(zip_buffer.read()),
            media_type="application/zip",
            headers={
                "Content-Disposition": "attachment; filename=mastered_tracks.zip",
                "Access-Control-Allow-Origin": "*",
            }
        )

    @web_app.get("/download/mastering/{job_id}/{filename}")
    async def download_mastered_file(job_id: str, filename: str):
        """Download individual mastered file"""
        
        volume.reload()  # Force volume reload for latest state
        
        # Construct file path
        file_path = Path(storage_path) / job_id / "output" / filename
        
        if not file_path.exists():
            raise HTTPException(404, f"Mastered file not found: {filename}")

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

    @web_app.options("/{path:path}")
    async def options_handler(path: str):
        """Handle CORS preflight requests"""
        return {"status": "ok"}
    
    return web_app

# Deploy FastAPI app using Modal's ASGI pattern
@app.function(image=matchering_image, volumes={storage_path: volume})
@modal.asgi_app()
def matchering_app():
    return create_matchering_app()

if __name__ == "__main__":
    print("🎚️ Klein Digital Solutions - Matchering 2.0 AI Mastering")
    print("📡 Modal Serverless Deployment")
    print("🎯 Professional Audio Mastering with Reference Matching")
    print("💡 Deploy: modal deploy modal_app_matchering.py")