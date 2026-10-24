#!/usr/bin/env python3
"""
Klein Digital Solutions - Music AI Transcription Service
Complete Music Transcription for Producers & Musicians

Features:
- MuScriptor large (Kyutai x Mirelo): multi-instrument audio -> MIDI (melody/instruments + real drum kit notes)
- beat_this (CPJKU): beats, downbeats and tempo -> click track for the DAW
- essentia: chord recognition (HPCP + ChordsDetection) and key detection (KeyExtractor)

License note: the MuScriptor weights are CC BY-NC 4.0 (non-commercial, private use only).
They are gated on Hugging Face: the account behind the "huggingface" Modal secret
must have accepted the license on https://huggingface.co/MuScriptor/muscriptor-large.
"""

import modal
from pathlib import Path
import uuid
import subprocess
import time
import json
import zipfile
import io
import shutil

# Global storage for job status tracking
job_status = {}

# Modal app instance
app = modal.App("music-ai-transcription-complete")

# Create persistent volume for file storage
volume = modal.Volume.from_name("music-transcription-storage", create_if_missing=True)
storage_path = "/vol/transcription_files"

# Hugging Face cache for the gated MuScriptor weights (downloaded on first use)
hf_cache = modal.Volume.from_name("muscriptor-hf-cache", create_if_missing=True)
HF_CACHE_PATH = "/cache/hf"

MUSCRIPTOR_MODEL = "large"
SOUNDFONT = "/usr/share/sounds/sf2/FluidR3_GM.sf2"


def _prefetch_beat_this():
    from beat_this.inference import File2Beats
    File2Beats(checkpoint_path="final0", device="cpu", dbn=False)


transcription_image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install(["ffmpeg", "libsndfile1", "fluidsynth", "fluid-soundfont-gm"])
    .pip_install([
        "muscriptor",
        "beat-this",
        "essentia==2.1b6.dev1389",
        "pretty_midi",
        "mido",
        "soundfile",
        "fastapi[standard]",
        "python-multipart",
    ])
    .env({"HF_HUB_CACHE": HF_CACHE_PATH})
    .run_function(_prefetch_beat_this)
)

with transcription_image.imports():
    import numpy as np

# Transcription configuration for producers
TRANSCRIPTION_CONFIG = {
    "melody": {
        "library": "MuScriptor large",
        "description": "Melodie/Instrumente -> MIDI-Noten fuer VST-Instrumente (alle Instrumente getrennt)",
        "output_formats": ["midi", "json"],
        "producer_benefit": "MIDI-Spuren je Instrument zum Laden in VSTs, Harmonizer & Synthesizer"
    },
    "drums": {
        "library": "MuScriptor large",
        "description": "Drums -> MIDI (Kick, Snare, Hi-Hat, Toms, Becken) zum Austauschen von Samples",
        "output_formats": ["midi", "json"],
        "producer_benefit": "Echtes Drum-Pattern als MIDI fuer Sample-Replacement in der DAW"
    },
    "chords": {
        "library": "essentia",
        "description": "Akkorde + Tonart -> Harmonische Analyse fuer Songwriting & Remixe",
        "output_formats": ["midi", "json", "txt"],
        "producer_benefit": "Chord-Progressionen und Tonart fuer Remixe, Covers & neue Arrangements"
    },
    "beat": {
        "library": "beat_this",
        "description": "Beat/Tempo -> Click-Track fuer die DAW",
        "output_formats": ["json", "txt", "midi"],
        "producer_benefit": "BPM + Grid fuer Synchronisation in der DAW"
    }
}


def save_job_status(job_id: str, status_data: dict):
    """Save job status to volume for persistence"""
    try:
        status_file = Path(storage_path) / f"status_{job_id}.json"
        with open(status_file, 'w') as f:
            json.dump(status_data, f)
        volume.commit()
        print(f"Status saved for job {job_id}: {status_data.get('progress', 0)}% - {status_data.get('phase', 'Unknown')}")
    except Exception as e:
        print(f"Error saving transcription job status: {e}")


def update_job_progress(job_id: str, progress: int, phase: str, additional_data: dict = None):
    """Helper to update job progress with additional data"""
    status_data = {
        "status": "processing",
        "progress": progress,
        "phase": phase,
        "error": None,
        "processing_time": None
    }
    if additional_data:
        status_data.update(additional_data)

    job_status[job_id] = status_data
    save_job_status(job_id, status_data)


@app.function(
    image=transcription_image,
    gpu="a10g",
    timeout=2400,
    memory=32768,
    volumes={storage_path: volume, HF_CACHE_PATH: hf_cache},
    secrets=[modal.Secret.from_name("huggingface")],
    scaledown_window=120
)
def transcribe_complete_audio(
    audio_data: bytes,
    filename: str,
    job_id: str,
    tasks: dict = None  # {"melody": True, "drums": True, "chords": True, "beat": True}
) -> dict:
    """
    Complete music transcription for producers
    Returns all formats needed for music production
    """
    start_time = time.time()

    if tasks is None:
        tasks = {"melody": True, "drums": True, "chords": True, "beat": True}

    update_job_progress(job_id, 5, "Initialisierung - Audio wird geladen")

    try:
        job_dir = Path(storage_path) / job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        input_file = job_dir / filename
        input_file.write_bytes(audio_data)

        output_dir = job_dir / "output"
        output_dir.mkdir(exist_ok=True)
        final_output_dir = output_dir / "final"
        final_output_dir.mkdir(exist_ok=True)

        print(f"Starting music transcription for job {job_id}")
        print(f"Tasks: {[task for task, enabled in tasks.items() if enabled]}")

        update_job_progress(job_id, 10, "Audio-Konvertierung zu WAV")
        wav_file = job_dir / "input.wav"
        mono_wav_file = job_dir / "input_mono.wav"
        try:
            subprocess.run(["ffmpeg", "-y", "-i", str(input_file), "-ar", "44100", "-ac", "2", str(wav_file)],
                           check=True, capture_output=True, timeout=120)
            subprocess.run(["ffmpeg", "-y", "-i", str(wav_file), "-ar", "44100", "-ac", "1", str(mono_wav_file)],
                           check=True, capture_output=True, timeout=120)
        except subprocess.CalledProcessError as e:
            raise Exception(f"Audio conversion failed: {e.stderr.decode(errors='ignore')[-500:]}")
        volume.commit()

        output_files = []
        completed_tasks = []
        task_errors = {}
        primary_tempo = None

        # ===================================================================
        # TASK 1+2: MELODY/INSTRUMENTS + DRUMS (MuScriptor, one pass)
        # ===================================================================

        if tasks.get("melody") or tasks.get("drums"):
            update_job_progress(job_id, 20, f"Noten-Transkription (MuScriptor {MUSCRIPTOR_MODEL}) - alle Instrumente")
            try:
                full_midi = output_dir / "muscriptor_full.mid"
                cmd = [
                    "muscriptor", "transcribe", str(wav_file),
                    "--model", MUSCRIPTOR_MODEL,
                    "--device", "cuda",
                    "--output", str(full_midi),
                ]
                print(f"Running: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
                hf_cache.commit()
                if result.returncode != 0 or not full_midi.exists():
                    stderr = result.stderr[-2000:]
                    if "GatedRepo" in stderr or "403" in stderr or "gated" in stderr.lower():
                        raise Exception("MuScriptor-Lizenz auf Hugging Face noch nicht akzeptiert: "
                                        "https://huggingface.co/MuScriptor/muscriptor-large")
                    raise Exception(f"MuScriptor failed: {stderr}")

                shutil.copy2(full_midi, final_output_dir / "full_transcription.mid")
                output_files.append("full_transcription.mid")
                instruments = split_muscriptor_midi(full_midi, final_output_dir)

                if tasks.get("melody"):
                    if instruments["melodic"]:
                        output_files += ["melody_notes.mid", "melody_simplified.mid", "melody_notes.json"]
                        completed_tasks.append("melody")
                    else:
                        task_errors["melody"] = "Keine melodischen Instrumente erkannt"

                if tasks.get("drums"):
                    update_job_progress(job_id, 45, "Drum-Noten werden exportiert")
                    if instruments["drums"]:
                        output_files += ["drums_pattern.mid", "drums_timing.json"]
                        completed_tasks.append("drums")
                    else:
                        task_errors["drums"] = "Kein Schlagzeug erkannt"
                volume.commit()
                print(f"MuScriptor done: {instruments}")

            except Exception as e:
                print(f"MuScriptor transcription failed: {e}")
                for t in ("melody", "drums"):
                    if tasks.get(t):
                        task_errors[t] = str(e)

        # ===================================================================
        # TASK 3: CHORDS + KEY (essentia)
        # ===================================================================

        if tasks.get("chords"):
            update_job_progress(job_id, 60, "Akkord- und Tonart-Erkennung (essentia)")
            try:
                chord_progression, key_info = analyze_chords_and_key(mono_wav_file)

                chord_midi_path = final_output_dir / "chord_progression.mid"
                create_chord_midi(chord_progression, chord_midi_path)
                output_files.append("chord_progression.mid")

                chord_analysis = {
                    "key": key_info,
                    "chord_progression": chord_progression,
                    "analysis": {
                        "unique_chords": sorted({c["chord"] for c in chord_progression}),
                        "producer_tips": generate_producer_tips(chord_progression, key_info)
                    }
                }
                with open(final_output_dir / "chord_analysis.json", 'w') as f:
                    json.dump(chord_analysis, f, indent=2)
                output_files.append("chord_analysis.json")

                create_chord_chart(chord_progression, key_info, final_output_dir / "chord_chart.txt")
                output_files.append("chord_chart.txt")

                completed_tasks.append("chords")
                print(f"Chord analysis completed - key {key_info['key']} {key_info['scale']}")

            except Exception as e:
                print(f"Chord recognition failed: {e}")
                task_errors["chords"] = str(e)

        # ===================================================================
        # TASK 4: BEAT/TEMPO (beat_this)
        # ===================================================================

        if tasks.get("beat"):
            update_job_progress(job_id, 80, "Beat/Tempo-Analyse (beat_this) - Click-Track fuer DAW")
            try:
                import numpy as np
                from beat_this.inference import File2Beats

                file2beats = File2Beats(checkpoint_path="final0", device="cuda", dbn=False)
                beats, downbeats = file2beats(str(wav_file))
                beats = np.asarray(beats, dtype=float)
                downbeats = np.asarray(downbeats, dtype=float)

                if len(beats) < 2:
                    raise Exception("Zu wenige Beats erkannt")
                primary_tempo = float(60.0 / np.median(np.diff(beats)))

                create_click_track_midi(beats, downbeats, primary_tempo, final_output_dir / "click_track.mid")
                output_files.append("click_track.mid")

                beat_analysis = {
                    "tempo_bpm": round(primary_tempo, 2),
                    "beats": beats.tolist(),
                    "downbeats": downbeats.tolist(),
                    "time_signature": detect_time_signature(beats, downbeats),
                    "total_bars": len(downbeats) if len(downbeats) > 0 else len(beats) // 4,
                    "analysis_summary": {
                        "tempo_stability": analyze_tempo_stability(beats),
                        "rhythm_complexity": analyze_rhythm_complexity(beats),
                        "daw_sync_notes": "Import click_track.mid to sync your DAW"
                    }
                }
                with open(final_output_dir / "beat_analysis.json", 'w') as f:
                    json.dump(beat_analysis, f, indent=2)
                output_files.append("beat_analysis.json")

                create_daw_tempo_map(beats, primary_tempo, final_output_dir / "tempo_map.txt")
                output_files.append("tempo_map.txt")

                completed_tasks.append("beat")
                print(f"Beat analysis completed - {primary_tempo:.1f} BPM")

            except Exception as e:
                print(f"Beat/Tempo analysis failed: {e}")
                task_errors["beat"] = str(e)

        # ===================================================================
        # FINAL PROCESSING & SUMMARY
        # ===================================================================

        requested = [t for t, enabled in tasks.items() if enabled]
        if not completed_tasks:
            raise Exception("Keine Transkription erfolgreich: " + "; ".join(f"{t}: {e}" for t, e in task_errors.items()))

        update_job_progress(job_id, 90, "Finalisierung - Producer Summary wird erstellt")

        with open(final_output_dir / "PRODUCER_SUMMARY.txt", 'w') as f:
            f.write(create_producer_summary(completed_tasks, output_files, primary_tempo))
        output_files.append("PRODUCER_SUMMARY.txt")

        with open(final_output_dir / "DAW_IMPORT_GUIDE.txt", 'w') as f:
            f.write(create_daw_instructions(completed_tasks, output_files))
        output_files.append("DAW_IMPORT_GUIDE.txt")

        total_size = sum(f.stat().st_size for f in final_output_dir.glob("*"))
        processing_time = round(time.time() - start_time, 2)
        volume.commit()

        final_status = {
            "status": "completed",
            "progress": 100,
            "phase": "Fertig - Alle Transcriptions fuer Producer verfuegbar",
            "error": None,
            "processing_time": processing_time,
            "files": output_files,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "download_base_url": f"/download/transcription/{job_id}",
            "completed_tasks": completed_tasks,
            "failed_tasks": {t: task_errors[t] for t in requested if t in task_errors},
            "producer_benefits": {
                task: TRANSCRIPTION_CONFIG[task]["producer_benefit"]
                for task in completed_tasks
            }
        }
        job_status[job_id] = final_status
        save_job_status(job_id, final_status)

        print(f"Transcription job {job_id} finished: {completed_tasks}, failed: {list(task_errors)}")
        return {
            "success": True,
            "files": output_files,
            "job_id": job_id,
            "processing_time": processing_time,
            "total_size": total_size,
            "completed_tasks": completed_tasks,
        }

    except Exception as e:
        error_msg = str(e)
        print(f"Music transcription failed: {error_msg}")
        error_status = {
            "status": "error",
            "progress": 100,
            "phase": "Fehler bei Transkription",
            "error": error_msg,
            "processing_time": round(time.time() - start_time, 2)
        }
        job_status[job_id] = error_status
        save_job_status(job_id, error_status)
        return {"success": False, "error": error_msg, "job_id": job_id}

# ===================================================================
# HELPER FUNCTIONS FOR MUSIC PRODUCTION
# ===================================================================

GM_DRUM_NAMES = {
    35: "kick", 36: "kick", 37: "side_stick", 38: "snare", 39: "clap", 40: "snare",
    41: "tom_low", 42: "hihat_closed", 43: "tom_low", 44: "hihat_pedal", 45: "tom_mid",
    46: "hihat_open", 47: "tom_mid", 48: "tom_high", 49: "crash", 50: "tom_high",
    51: "ride", 52: "china", 53: "ride_bell", 54: "tambourine", 55: "splash",
    56: "cowbell", 57: "crash", 59: "ride",
}


def split_muscriptor_midi(full_midi_path, out_dir):
    """Split the MuScriptor MIDI into melodic instruments and drums (keeps tempo map)"""
    import pretty_midi

    full = pretty_midi.PrettyMIDI(str(full_midi_path))
    melodic = [inst for inst in full.instruments if not inst.is_drum and inst.notes]
    drums = [inst for inst in full.instruments if inst.is_drum and inst.notes]

    def write_subset(instruments, path):
        midi = pretty_midi.PrettyMIDI(str(full_midi_path))
        midi.instruments = instruments
        midi.write(str(path))

    if melodic:
        write_subset(melodic, out_dir / "melody_notes.mid")
        create_producer_midi_summary(out_dir / "melody_notes.mid", out_dir / "melody_simplified.mid")
        notes_json = [
            {
                "instrument": inst.name or pretty_midi.program_to_instrument_name(inst.program),
                "program": int(inst.program),
                "notes": [
                    {"pitch": int(n.pitch), "name": pretty_midi.note_number_to_name(int(n.pitch)),
                     "start": round(float(n.start), 4), "end": round(float(n.end), 4), "velocity": int(n.velocity)}
                    for n in inst.notes
                ],
            }
            for inst in melodic
        ]
        with open(out_dir / "melody_notes.json", 'w') as f:
            json.dump(notes_json, f, indent=2)

    if drums:
        write_subset(drums, out_dir / "drums_pattern.mid")
        hits = {}
        for inst in drums:
            for n in inst.notes:
                hits.setdefault(GM_DRUM_NAMES.get(int(n.pitch), f"note_{int(n.pitch)}"), []).append(round(float(n.start), 4))
        drum_json = {
            "hits": {name: sorted(times) for name, times in sorted(hits.items())},
            "hit_counts": {name: len(times) for name, times in sorted(hits.items())},
            "midi_mapping": "General MIDI drum map (channel 10)",
            "producer_note": "Import drums_pattern.mid to replace with your drum samples in DAW"
        }
        with open(out_dir / "drums_timing.json", 'w') as f:
            json.dump(drum_json, f, indent=2)

    return {
        "melodic": [inst.name or pretty_midi.program_to_instrument_name(inst.program) for inst in melodic],
        "drums": [inst.name or "Drums" for inst in drums],
    }


def create_producer_midi_summary(input_midi_path, output_path):
    """Create a simplified MIDI file for easier editing in DAW"""
    try:
        import pretty_midi

        midi_data = pretty_midi.PrettyMIDI(str(input_midi_path))
        for instrument in midi_data.instruments:
            # Keep notes longer than 0.1 seconds, normalize velocity
            instrument.notes = [
                pretty_midi.Note(velocity=min(100, max(60, n.velocity)), pitch=n.pitch, start=n.start, end=n.end)
                for n in instrument.notes if n.end - n.start > 0.1
            ]
        midi_data.write(str(output_path))
        print(f"Created simplified MIDI: {output_path}")

    except Exception as e:
        print(f"Could not create simplified MIDI: {e}")


NOTE_TO_PC = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6,
              "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}


def chord_to_pitches(chord_name):
    """'C#m' -> [61, 64, 68]; 'Bb' -> [70, 74, 77] (root position around middle C)"""
    minor = chord_name.endswith("m")
    root = chord_name[:-1] if minor else chord_name
    if root not in NOTE_TO_PC:
        return None
    base = 60 + NOTE_TO_PC[root]
    return [base, base + (3 if minor else 4), base + 7]


def analyze_chords_and_key(mono_wav_file, sample_rate=44100, frame_size=8192, hop_size=1024):
    """Chord recognition (HPCP + ChordsDetection) and key detection (KeyExtractor) with essentia"""
    import essentia
    import essentia.standard as es

    audio = es.MonoLoader(filename=str(mono_wav_file), sampleRate=sample_rate)()

    # Key detection on the full track
    key, scale, strength = es.KeyExtractor(sampleRate=sample_rate)(audio)
    key_info = {"key": key, "scale": scale, "strength": round(float(strength), 3),
                "label": f"{key} {'Dur' if scale == 'major' else 'Moll'}"}

    windowing = es.Windowing(type='blackmanharris62')
    spectrum = es.Spectrum()
    spectralpeaks = es.SpectralPeaks(orderBy='magnitude', magnitudeThreshold=0.00001,
                                     minFrequency=40, maxFrequency=5000, maxPeaks=100)
    hpcp = es.HPCP(size=12, referenceFrequency=440, harmonics=8, bandPreset=False,
                   minFrequency=40, maxFrequency=5000, weightType='cosine', nonLinear=False)

    hpcp_frames = []
    for frame in es.FrameGenerator(audio, frameSize=frame_size, hopSize=hop_size, startFromZero=True):
        peaks_freq, peaks_mag = spectralpeaks(spectrum(windowing(frame)))
        hpcp_frames.append(hpcp(peaks_freq, peaks_mag))

    chords, chord_strength = es.ChordsDetection(hopSize=hop_size, sampleRate=sample_rate, windowSize=2)(
        essentia.array(hpcp_frames))

    # Merge consecutive identical chords into segments
    frame_dur = hop_size / sample_rate
    progression = []
    for i, (chord, conf) in enumerate(zip(chords, chord_strength)):
        t = i * frame_dur
        if conf < 0.3 or chord == 'N':
            continue
        if progression and progression[-1]["chord"] == chord and abs(progression[-1]["end"] - t) < 2 * frame_dur:
            seg = progression[-1]
            seg["end"] = t + frame_dur
            seg["_conf"].append(float(conf))
        else:
            progression.append({"chord": chord, "start": t, "end": t + frame_dur, "_conf": [float(conf)]})

    clean = []
    for seg in progression:
        duration = seg["end"] - seg["start"]
        if duration < 0.25:  # drop flicker
            continue
        clean.append({
            "chord": seg["chord"],
            "time": round(seg["start"], 3),
            "duration": round(duration, 3),
            "confidence": round(sum(seg["_conf"]) / len(seg["_conf"]), 3),
        })
    return clean, key_info


def create_chord_midi(chord_progression, output_path):
    """Create MIDI file with chord progression"""
    import pretty_midi

    midi = pretty_midi.PrettyMIDI()
    chord_track = pretty_midi.Instrument(program=0, name="Chord Progression")
    for chord_info in chord_progression:
        pitches = chord_to_pitches(chord_info["chord"])
        if not pitches:
            continue
        for pitch in pitches:
            chord_track.notes.append(pretty_midi.Note(
                velocity=80, pitch=pitch,
                start=chord_info["time"], end=chord_info["time"] + chord_info["duration"]
            ))
    midi.instruments.append(chord_track)
    midi.write(str(output_path))
    print(f"Created chord progression MIDI: {output_path}")


def generate_producer_tips(chord_progression, key_info):
    """Generate helpful tips for producers"""
    tips = [
        f"Tonart laut Analyse: {key_info['label']} (Sicherheit {key_info['strength']})",
        "Import chord_progression.mid into your DAW as a guide track",
        "Use these chords to create bass lines and lead melodies",
        "Try different inversions of these chords for variety",
    ]
    if len(chord_progression) > 8:
        tips.append("Consider looping sections of this progression for verses/choruses")
    return tips


def create_chord_chart(chord_progression, key_info, output_path):
    """Create human-readable chord chart"""
    with open(output_path, 'w') as f:
        f.write("CHORD CHART FOR MUSIC PRODUCTION\n")
        f.write("================================\n\n")
        f.write(f"Tonart: {key_info['label']} ({key_info['key']} {key_info['scale']}, Sicherheit {key_info['strength']})\n\n")

        if not chord_progression:
            f.write("No clear chord progression detected.\n")
            return

        f.write("Time\t\tChord\t\tDauer\t\tConfidence\n")
        f.write("-" * 56 + "\n")
        for c in chord_progression:
            f.write(f"{c['time']:>7.2f}s\t{c['chord']:<12}\t{c['duration']:.2f}s\t\t{c['confidence']:.2f}\n")

        f.write("\n\nPRODUCER NOTES:\n")
        f.write("- Import chord_progression.mid for MIDI version\n")
        f.write("- Use as foundation for bass lines and melodies\n")
        f.write("- Experiment with different chord voicings\n")

def create_click_track_midi(beats, downbeats, tempo, output_path):
    """Create a click track MIDI for DAW synchronization"""
    try:
        import pretty_midi
        
        midi = pretty_midi.PrettyMIDI()
        click_track = pretty_midi.Instrument(program=0, is_drum=True, name="Click Track")
        
        # Click sounds
        kick_click = 36   # Strong beat (downbeat)
        snare_click = 37  # Regular beat
        
        # Add downbeats as strong clicks
        for downbeat_time in downbeats:
            note = pretty_midi.Note(
                velocity=120,  # Loud for downbeats
                pitch=kick_click,
                start=downbeat_time,
                end=downbeat_time + 0.05
            )
            click_track.notes.append(note)
        
        # Add regular beats as softer clicks
        for beat_time in beats:
            # Skip if this is already a downbeat
            if not any(abs(beat_time - db) < 0.01 for db in downbeats):
                note = pretty_midi.Note(
                    velocity=80,  # Softer for regular beats
                    pitch=snare_click,
                    start=beat_time,
                    end=beat_time + 0.05
                )
                click_track.notes.append(note)
        
        midi.instruments.append(click_track)
        midi.write(str(output_path))
        print(f"Created click track MIDI: {output_path}")
        
    except Exception as e:
        print(f"Could not create click track MIDI: {e}")

def detect_time_signature(beats, downbeats):
    """Detect time signature from beat analysis"""
    if len(downbeats) < 2:
        return "4/4"  # Default
    
    # Calculate average beats between downbeats
    beat_intervals = []
    for i in range(len(downbeats) - 1):
        start_time = downbeats[i]
        end_time = downbeats[i + 1]
        
        # Count beats between downbeats
        beats_in_bar = sum(1 for beat in beats if start_time <= beat < end_time)
        if beats_in_bar > 0:
            beat_intervals.append(beats_in_bar)
    
    if not beat_intervals:
        return "4/4"
    
    # Most common interval
    avg_beats = round(np.mean(beat_intervals))
    
    if avg_beats == 3:
        return "3/4"
    elif avg_beats == 4:
        return "4/4"
    elif avg_beats == 6:
        return "6/8"
    else:
        return f"{avg_beats}/4"

def analyze_tempo_stability(beats):
    """Analyze how stable the tempo is"""
    if len(beats) < 3:
        return "stable"
    
    # Calculate intervals between beats
    intervals = np.diff(beats)
    
    # Calculate coefficient of variation
    cv = np.std(intervals) / np.mean(intervals) if np.mean(intervals) > 0 else 0
    
    if cv < 0.05:
        return "very stable"
    elif cv < 0.1:
        return "stable"
    elif cv < 0.2:
        return "moderately stable"
    else:
        return "variable tempo"

def analyze_rhythm_complexity(beats):
    """Analyze rhythm complexity"""
    if len(beats) < 4:
        return "simple"
    
    # Simple metric based on beat regularity
    intervals = np.diff(beats)
    regularity = 1 - (np.std(intervals) / np.mean(intervals)) if np.mean(intervals) > 0 else 1
    
    if regularity > 0.9:
        return "simple and regular"
    elif regularity > 0.7:
        return "moderate complexity"
    else:
        return "complex rhythm"

def create_daw_tempo_map(beats, primary_tempo, output_path):
    """Create a tempo map file for DAW import"""
    try:
        with open(output_path, 'w') as f:
            f.write("DAW TEMPO MAP\n")
            f.write("=============\n\n")
            f.write(f"Primary Tempo: {primary_tempo:.2f} BPM\n\n")
            f.write("Beat Positions (seconds):\n")
            f.write("-" * 30 + "\n")
            
            for i, beat_time in enumerate(beats):
                f.write(f"Beat {i+1:3d}: {beat_time:.3f}s\n")
            
            f.write("\n\nDAW IMPORT INSTRUCTIONS:\n")
            f.write("1. Set your DAW to " + f"{primary_tempo:.0f} BPM\n")
            f.write("2. Import click_track.mid for perfect synchronization\n")
            f.write("3. Use beat positions above for manual tempo mapping if needed\n")
        
        print(f"Created DAW tempo map: {output_path}")
        
    except Exception as e:
        print(f"Could not create tempo map: {e}")

def create_producer_summary(completed_tasks, output_files, tempo=None):
    """Create a summary for producers"""
    summary = """
KLEIN DIGITAL SOLUTIONS - MUSIC TRANSCRIPTION COMPLETE
=========================================================

PRODUCER-READY FILES GENERATED:
"""
    if "melody" in completed_tasks or "drums" in completed_tasks:
        summary += """
FULL TRANSCRIPTION (MuScriptor large):
   -> full_transcription.mid - All instruments incl. drums, with tempo map
"""
    if "melody" in completed_tasks:
        summary += """
MELODY/INSTRUMENTS (MuScriptor large):
   -> melody_notes.mid - One track per detected instrument, load into VSTs
   -> melody_simplified.mid - Cleaned version for easier editing
   -> melody_notes.json - Detailed note data per instrument
"""
    if "drums" in completed_tasks:
        summary += """
DRUMS (MuScriptor large):
   -> drums_pattern.mid - Kick/Snare/Hi-Hat/Toms/Cymbals (General MIDI)
   -> drums_timing.json - Hit times per drum piece
"""
    if "chords" in completed_tasks:
        summary += """
CHORDS + KEY (essentia):
   -> chord_progression.mid - Chord progression as MIDI
   -> chord_analysis.json - Key + chord segments
   -> chord_chart.txt - Human-readable chord chart
"""
    if "beat" in completed_tasks:
        summary += f"""
BEAT/TEMPO (beat_this):
   -> click_track.mid - Click for DAW synchronization
   -> beat_analysis.json - Beats, downbeats, time signature
   -> tempo_map.txt - Manual tempo mapping guide
   {f"-> Primary Tempo: {tempo:.1f} BPM" if tempo else ""}
"""
    summary += """

DAW WORKFLOW TIPS:
==================
1. Set the DAW tempo (see beat_analysis.json) or import click_track.mid
2. Load melody_notes.mid tracks into your favorite VST instruments
3. Use chord_progression.mid as harmonic foundation
4. Replace drums_pattern.mid hits with your own samples
"""
    return summary


def create_daw_instructions(completed_tasks, output_files):
    """Create DAW import instructions"""
    instructions = """
DAW IMPORT GUIDE - KLEIN DIGITAL SOLUTIONS
==========================================
"""
    if "beat" in completed_tasks:
        instructions += """
1. TEMPO & SYNCHRONIZATION:
   - Create a new project and set the BPM from beat_analysis.json
   - Import 'click_track.mid' and align it with the original audio
"""
    if "melody" in completed_tasks:
        instructions += """
2. MELODY & INSTRUMENTS:
   - Import 'melody_notes.mid' (one MIDI track per instrument)
   - Load matching VST instruments, adjust velocity and timing as needed
"""
    if "chords" in completed_tasks:
        instructions += """
3. CHORD PROGRESSION:
   - Import 'chord_progression.mid' on a pad/piano track
   - 'chord_chart.txt' lists key, chord names and timing
"""
    if "drums" in completed_tasks:
        instructions += """
4. DRUM REPLACEMENT:
   - Import 'drums_pattern.mid' into your drum sampler (General MIDI mapping)
"""
    instructions += """
TROUBLESHOOTING:
===============
- If timing seems off, check the DAW tempo against beat_analysis.json
- 'full_transcription.mid' contains the MuScriptor tempo map
"""
    return instructions

# ===================================================================
# FASTAPI WEB APPLICATION
# ===================================================================

def create_transcription_app():
    from fastapi import FastAPI, File, Form, UploadFile, HTTPException
    from fastapi.responses import StreamingResponse, JSONResponse
    from fastapi.middleware.cors import CORSMiddleware

    web_app = FastAPI(
        title="Klein Digital Solutions - Music AI Transcription Complete",
        description="Professional music transcription for producers: Melody, Drums, Chords & Beat analysis",
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

    @web_app.post("/transcribe")
    async def api_transcribe(
        audio_file: UploadFile = File(..., description="Audio file for transcription"),
        melody: bool = Form(True, description="Extract melody/instruments (MuScriptor)"),
        drums: bool = Form(True, description="Extract drum patterns (MuScriptor)"),
        chords: bool = Form(True, description="Analyze chords + key (essentia)"),
        beat: bool = Form(True, description="Analyze beat/tempo (beat_this)")
    ):
        """
        Complete music transcription for professional production
        """
        from fastapi import Response
        
        try:
            print(f"Received transcription request: {audio_file.filename}")
            
            # Validate file format
            allowed_extensions = ['.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg']
            if not any(audio_file.filename.lower().endswith(ext) for ext in allowed_extensions):
                raise HTTPException(400, f"Unsupported file format. Allowed: {', '.join(allowed_extensions)}")
            
            # Read and validate audio data
            audio_data = await audio_file.read()
            
            if len(audio_data) == 0:
                raise HTTPException(400, "Empty audio file uploaded")
            
            # File size limit (100MB for transcription)
            max_size = 100 * 1024 * 1024
            if len(audio_data) > max_size:
                raise HTTPException(400, f"File too large (max {max_size // 1024 // 1024}MB)")
            
            # Check that at least one task is selected
            tasks = {"melody": melody, "drums": drums, "chords": chords, "beat": beat}
            if not any(tasks.values()):
                raise HTTPException(400, "At least one transcription task must be selected")
            
            # Generate job ID
            job_id = str(uuid.uuid4())
            file_extension = Path(audio_file.filename).suffix
            safe_filename = f"{job_id}{file_extension}"
            
            selected_tasks = [task for task, enabled in tasks.items() if enabled]
            print(f"Starting transcription for {audio_file.filename} ({len(audio_data)} bytes)")
            print(f"Selected tasks: {selected_tasks}")
            
            # Initialize job status
            job_status[job_id] = {
                "status": "queued",
                "progress": 0,
                "phase": "Upload abgeschlossen, Transcription wird vorbereitet...",
                "error": None,
                "processing_time": None,
                "files": [],
                "total_size_mb": 0,
                "selected_tasks": selected_tasks
            }
            
            # Start async transcription
            transcribe_complete_audio.spawn(audio_data, safe_filename, job_id, tasks)
            
            response_data = {
                "job_id": job_id,
                "status": "queued",
                "selected_tasks": selected_tasks,
                "message": "Complete music transcription started. Use /status/transcription/{job_id} to check progress.",
                "estimated_time": f"{len(selected_tasks) * 2}-{len(selected_tasks) * 5} minutes"
            }
            
            print(f"Music transcription job {job_id} queued for processing")
            
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
            print(f"Transcription upload error: {str(e)}")
            raise HTTPException(500, f"Transcription upload error: {str(e)}")

    @web_app.get("/status/transcription/{job_id}")
    @web_app.get("/status/{job_id}")  # path used by the frontend
    async def transcription_status(job_id: str):
        """Status API for transcription progress"""
        # Always check volume first for latest status
        volume.reload()
        status_file = Path(storage_path) / f"status_{job_id}.json"
        
        if status_file.exists():
            try:
                with open(status_file, 'r') as f:
                    status = json.load(f)
                print(f"Transcription status loaded from volume for job {job_id}: {status.get('progress', 0)}% - {status.get('phase', 'Unknown')}")
                return status
            except Exception as e:
                print(f"Error loading transcription status from volume: {e}")
        
        # Fallback to in-memory status
        status = job_status.get(job_id)
        if status:
            print(f"Transcription status loaded from memory for job {job_id}: {status.get('progress', 0)}% - {status.get('phase', 'Unknown')}")
            return status
        
        print(f"No transcription status found for job {job_id}")
        return {
            "status": "unknown", 
            "progress": 0, 
            "phase": "Job nicht gefunden", 
            "error": "Transcription job nicht gefunden"
        }

    @web_app.get("/health")
    async def health():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "service": "Klein Digital Solutions - Music AI Transcription Complete",
            "version": "2.0.0",
            "libraries": {
                "melody": f"MuScriptor {MUSCRIPTOR_MODEL} (CC BY-NC 4.0)",
                "drums": f"MuScriptor {MUSCRIPTOR_MODEL} (CC BY-NC 4.0)",
                "chords": "essentia (ChordsDetection + KeyExtractor)",
                "beat": "beat_this (CPJKU)"
            },
            "max_file_size": "100MB",
            "supported_formats": ["MP3", "WAV", "FLAC", "M4A", "AAC", "OGG"],
            "producer_ready": True
        }

    @web_app.get("/capabilities")
    async def capabilities():
        """Get detailed transcription capabilities"""
        return {
            "transcription_types": TRANSCRIPTION_CONFIG,
            "workflow": {
                "step_1": "Upload audio file",
                "step_2": "Select transcription tasks (melody, drums, chords, beat)",
                "step_3": "Download producer-ready MIDI and analysis files",
                "step_4": "Import into your DAW using provided guides"
            },
            "output_formats": {
                "midi": "Ready for DAW import",
                "json": "Detailed analysis data",
                "txt": "Human-readable charts and guides"
            },
            "producer_benefits": {
                "time_saving": "Skip manual transcription work",
                "accuracy": "AI-powered precision",
                "daw_ready": "Files optimized for music production",
                "educational": "Learn from professional track analysis"
            }
        }

    @web_app.get("/download/transcription/{job_id}/all.zip")
    async def download_transcription_zip(job_id: str):
        """Download all transcription files as ZIP"""
        volume.reload()  # Force volume reload for latest state
        
        output_dir = Path(storage_path) / job_id / "output" / "final"
        
        # Debug logging for download issues
        print(f"DEBUG DOWNLOAD: Looking for files in: {output_dir}")
        print(f"DEBUG DOWNLOAD: Directory exists: {output_dir.exists()}")
        print(f"DEBUG DOWNLOAD: Is directory: {output_dir.is_dir()}")
        
        if output_dir.exists():
            files_found = list(output_dir.glob("*"))
            print(f"DEBUG DOWNLOAD: Files found: {[f.name for f in files_found]}")
            print(f"DEBUG DOWNLOAD: File count: {len(files_found)}")
        else:
            # Check parent directories
            job_dir = Path(storage_path) / job_id
            print(f"DEBUG DOWNLOAD: Job dir exists: {job_dir.exists()}")
            if job_dir.exists():
                job_contents = list(job_dir.glob("*"))
                print(f"DEBUG DOWNLOAD: Job dir contents: {[f.name for f in job_contents]}")
                
                output_base = job_dir / "output"
                print(f"DEBUG DOWNLOAD: Output base exists: {output_base.exists()}")
                if output_base.exists():
                    output_contents = list(output_base.glob("*"))
                    print(f"DEBUG DOWNLOAD: Output base contents: {[f.name for f in output_contents]}")
        
        if not output_dir.is_dir():
            raise HTTPException(404, "Transcription files not found")
        
        # Create ZIP in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for file_path in output_dir.glob("*"):
                if file_path.is_file():
                    zip_file.write(file_path, file_path.name)
        
        zip_buffer.seek(0)
        
        return StreamingResponse(
            io.BytesIO(zip_buffer.read()),
            media_type="application/zip",
            headers={
                "Content-Disposition": "attachment; filename=music_transcription_complete.zip",
                "Access-Control-Allow-Origin": "*",
            }
        )

    @web_app.get("/download/transcription/{job_id}/{filename}")
    async def download_transcription_file(job_id: str, filename: str):
        """Download individual transcription file"""
        volume.reload()  # Force volume reload for latest state
        
        file_path = Path(storage_path) / job_id / "output" / "final" / Path(filename).name

        if not file_path.exists():
            raise HTTPException(404, f"Transcription file not found: {filename}")

        def file_iterator():
            with open(file_path, "rb") as f:
                while chunk := f.read(8192):
                    yield chunk
        
        # Determine media type
        media_type = "application/octet-stream"
        if filename.endswith(('.mid', '.midi')):
            media_type = "audio/midi"
        elif filename.endswith('.json'):
            media_type = "application/json"
        elif filename.endswith('.txt'):
            media_type = "text/plain"
        
        return StreamingResponse(
            file_iterator(),
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Access-Control-Allow-Origin": "*",
            }
        )

    @web_app.get("/preview/transcription/{job_id}/{filename}")
    async def preview_transcription_file(job_id: str, filename: str):
        """Generate and stream audio preview for transcription files"""
        volume.reload()
        
        output_dir = Path(storage_path) / job_id / "output" / "final"
        file_path = output_dir / filename
        
        print(f"DEBUG PREVIEW: Looking for {file_path}")
        
        if not file_path.exists():
            raise HTTPException(404, f"Transcription file not found: {filename}")
        
        # For MIDI files, we need to convert to audio for preview
        if filename.endswith('.mid') or filename.endswith('.midi'):
            # Generate audio preview from MIDI using FluidSynth
            preview_path = output_dir / f"preview_{filename.replace('.mid', '.mp3').replace('.midi', '.mp3')}"
            
            if not preview_path.exists():
                try:
                    # Use fluidsynth to render MIDI to audio
                    import subprocess
                    wav_temp = output_dir / f"temp_{filename.replace('.mid', '.wav').replace('.midi', '.wav')}"
                    
                    # Convert MIDI to WAV using fluidsynth
                    fluidsynth_cmd = [
                        "fluidsynth", "-ni", SOUNDFONT, 
                        str(file_path), "-F", str(wav_temp), "-r", "44100"
                    ]
                    
                    subprocess.run(fluidsynth_cmd, check=True, capture_output=True, timeout=30)
                    
                    # Convert WAV to MP3 preview (30 seconds)
                    ffmpeg_cmd = [
                        "ffmpeg", "-y", "-i", str(wav_temp), "-t", "30", 
                        "-ar", "44100", "-ac", "2", "-b:a", "128k", str(preview_path)
                    ]
                    
                    subprocess.run(ffmpeg_cmd, check=True, capture_output=True, timeout=30)
                    
                    # Clean up temp WAV
                    if wav_temp.exists():
                        wav_temp.unlink()
                    
                    volume.commit()
                    print(f"DEBUG PREVIEW: Generated MIDI preview: {preview_path}")
                    
                except Exception as e:
                    print(f"❌ Failed to generate MIDI preview: {e}")
                    raise HTTPException(500, f"Could not generate preview for {filename}")
            
            # Stream the MP3 preview
            def file_iterator():
                with open(preview_path, "rb") as f:
                    while chunk := f.read(8192):
                        yield chunk
            
            return StreamingResponse(
                file_iterator(),
                media_type="audio/mpeg",
                headers={
                    "Content-Disposition": f"inline; filename=preview_{filename}.mp3",
                    "Access-Control-Allow-Origin": "*",
                }
            )
        
        # For non-MIDI files (JSON, TXT), return as downloadable content
        else:
            def file_iterator():
                with open(file_path, "rb") as f:
                    while chunk := f.read(8192):
                        yield chunk
            
            media_type = "application/json" if filename.endswith('.json') else "text/plain"
            
            return StreamingResponse(
                file_iterator(),
                media_type=media_type,
                headers={
                    "Content-Disposition": f"inline; filename={filename}",
                    "Access-Control-Allow-Origin": "*",
                }
            )

    @web_app.options("/{path:path}")
    async def options_handler(path: str):
        """Handle CORS preflight requests"""
        return {"status": "ok"}
    
    return web_app

# Deploy FastAPI app using Modal's ASGI pattern
@app.function(image=transcription_image, volumes={storage_path: volume})
@modal.asgi_app()
def transcription_app():
    return create_transcription_app()

if __name__ == "__main__":
    print("Klein Digital Solutions - Music AI Transcription Complete")
    print("Professional transcription for producers & musicians")
    print("Modal Serverless Deployment with GPU optimization")
    print("Deploy: modal deploy modal_app_transcription.py")
    print("\nFeatures:")
    print("   • MuScriptor: Melody/Instruments + Drums -> MIDI")
    print("   • essentia: Chords + Key")
    print("   • beat_this: Beat/Tempo -> DAW synchronization")