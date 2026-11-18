"""Local audio engines. Input and output paths come from the workspace store."""

import importlib.util
import json
import math
import os
import re
import shutil
import signal
import sys
import subprocess
import time
from pathlib import Path


def binary(command):
    local = Path(sys.executable).parent / command
    return str(local) if local.is_file() and os.access(local, os.X_OK) else shutil.which(command) or command


INPUT_PROTOCOLS = "file,pipe"
INPUT_FORMATS = "wav,aiff,flac,mp3,aac,ogg,mov,matroska,webm"


class UserError(ValueError):
    """An error whose message is suitable for the workspace interface."""


class Cancelled(Exception):
    pass


def run(args, cancelled=lambda: False, timeout=900):
    import tempfile
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        isolated = not os.environ.get("XO_RENDER_WORKER")
        with subprocess.Popen([str(binary(str(args[0]))), *map(str, args[1:])], stdout=stdout, stderr=stderr,
                              start_new_session=isolated) as process:
            deadline = time.monotonic() + timeout
            while process.poll() is None:
                if cancelled() or time.monotonic() > deadline:
                    try:
                        if isolated:
                            os.killpg(process.pid, signal.SIGKILL)
                        else:
                            process.kill()
                    except ProcessLookupError:
                        pass
                    process.wait()
                    if cancelled():
                        raise Cancelled()
                    raise UserError("Die Audioverarbeitung hat das Zeitlimit erreicht.")
                time.sleep(0.08)
        stdout.seek(0)
        stderr.seek(0)
        output = stdout.read()
        errors = stderr.read().decode(errors="replace")
        if process.returncode:
            raise ValueError(f"{Path(args[0]).name}: {errors.strip()[-550:] or 'Verarbeitung fehlgeschlagen.'}")
        return output, errors


def ffmpeg(*args, cancelled=lambda: False):
    secured = []
    for arg in args:
        if arg == "-i":
            secured.extend(["-protocol_whitelist", INPUT_PROTOCOLS])
        secured.append(arg)
    return run(["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y", *secured], cancelled)


def probe(file):
    data, _ = run(["ffprobe", "-v", "error", "-protocol_whitelist", INPUT_PROTOCOLS, "-format_whitelist", INPUT_FORMATS, "-select_streams", "a", "-show_streams", "-show_format",
                   "-of", "json", file], timeout=30)
    data = json.loads(data)
    if len(data.get("streams", [])) != 1:
        raise UserError("Die Datei benötigt genau einen Audiostream.")
    audio = data["streams"][0]
    channels = audio["channels"]
    rate = int(audio["sample_rate"])
    if channels not in (1, 2):
        raise UserError("Bitte als Mono oder Stereo importieren. Mehrkanal-Audio zuerst abmischen.")
    duration = float(audio.get("duration", data["format"].get("duration", 0)))
    if not 0 < duration <= 1800 or not 8000 <= rate <= 192000:
        raise UserError("Unterstützt werden bis zu 30 Minuten und 8–192 kHz.")
    frames = round(duration * rate)
    if audio.get("time_base") == f"1/{rate}" and "duration_ts" in audio:
        frames = int(audio["duration_ts"])
    return {"rate": rate, "channels": channels, "samples": frames, "seconds": frames / rate,
            "codec": audio["codec_name"],
            "bits": int(audio.get("bits_per_raw_sample", audio.get("bits_per_sample", 0))) or None,
            "container": data["format"]["format_name"]}


def peaks_and_listen(source, preview, meta, cancelled=lambda: False):
    from array import array
    # Decode at the source rate for exact decoded length and finite/overload counts.
    # Stream blocks so a full song never needs a full-resolution PCM buffer in memory.
    args = ["ffmpeg", "-nostdin", "-v", "error", "-xerror", "-protocol_whitelist", INPUT_PROTOCOLS, "-format_whitelist", INPUT_FORMATS, "-i", str(source), "-map", "0:a:0",
            "-f", "f32le", "-acodec", "pcm_f32le", "pipe:1"]
    size = max(1, math.ceil(meta["samples"] / 512)) * meta["channels"]
    peaks, count, nonfinite, clipped, maximum = [], 0, 0, 0, 0
    with subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) as process:
        while block := process.stdout.read(size * 4):
            if cancelled():
                process.kill()
                raise Cancelled()
            values = array("f", block)
            finite = [abs(value) for value in values if math.isfinite(value)]
            extreme = max(finite, default=0)
            peaks.append(round(min(1, extreme), 4))
            count += len(values)
            nonfinite += len(values) - len(finite)
            clipped += sum(value >= 1 for value in finite)
            maximum = max(maximum, extreme)
        if process.wait() or not count:
            raise UserError("Audio konnte nicht vollständig dekodiert werden.")
    if nonfinite:
        raise UserError(f"Audio enthält {nonfinite} nicht-finite Werte.")
    meta.update(samples=count // meta["channels"], seconds=count / (meta["channels"] * meta["rate"]),
                peaks=peaks, sample_peak=round(20 * math.log10(maximum), 2) if maximum else None,
                clipped_samples=clipped, nonfinite_samples=nonfinite)
    ffmpeg("-i", source, "-map", "0:a:0", "-c:a", "libmp3lame", "-q:a", "4", preview, cancelled=cancelled)


def qa(source, cancelled=lambda: False):
    _, log = run(["ffmpeg", "-nostdin", "-hide_banner", "-protocol_whitelist", INPUT_PROTOCOLS, "-format_whitelist", INPUT_FORMATS, "-i", source, "-vn", "-af",
                  "silencedetect=n=-55dB:d=0.25,loudnorm=print_format=json", "-f", "null", "-"], cancelled)
    match = re.search(r'\{\s*"input_i".*?\}', log, re.S)
    if not match:
        raise UserError("Lautheit konnte nicht gemessen werden.")
    measures = json.loads(match[0])
    def finite(key):
        value = float(measures[key])
        return value if math.isfinite(value) else None
    beginnings = re.findall(r"silence_start: ([\d.]+)", log)
    endings = re.findall(r"silence_end: ([\d.]+)", log)
    integrated = finite("input_i")
    return {"lufs": integrated, "true_peak": finite("input_tp"), "lra": finite("input_lra") if integrated is not None else None,
            "silence": [[float(a), float(b)] for a, b in zip(beginnings, endings)],
            "method": "FFmpeg loudnorm / EBU R128; Stille ab 250 ms unter −55 dBFS"}


def number(value, low, high, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not low <= value <= high:
        raise UserError(f"{name} muss zwischen {low} und {high} liegen.")
    return value


def integer(value, low, high, name):
    if type(value) is not int:
        raise UserError(f"{name} muss ganzzahlig sein.")
    return number(value, low, high, name)


def region(meta, data):
    start = integer(data.get("start", 0), 0, meta["samples"] - 1, "Startsample")
    end = integer(data.get("end", meta["samples"]), start + 1, meta["samples"], "Endsample")
    return start, end


def render_selection(source, target, meta, choice, cancelled):
    start, end = region(meta, choice)
    filters = [f"atrim=start_sample={start}:end_sample={end}", "asetpts=PTS-STARTPTS"]
    for side in ("in", "out"):
        ms = number(choice.get("fade_" + side, 0), 0, 500, "Fade")
        length = min((end - start) // 2, round(ms * meta["rate"] / 1000))
        if length:
            position = 0 if side == "in" else end - start - length
            filters.append(f"afade=t={side}:ss={position}:ns={length}")
    ffmpeg("-i", source, "-af", ",".join(filters), "-c:a", "pcm_f32le", target, cancelled=cancelled)
    return start, end


EFFECTS = {
    "Gain": {"gain_db": [-36, 18, 0]},
    "HighpassFilter": {"cutoff_frequency_hz": [20, 18000, 80]},
    "LowpassFilter": {"cutoff_frequency_hz": [20, 18000, 10000]},
    "PeakFilter": {"cutoff_frequency_hz": [20, 18000, 1000], "gain_db": [-18, 18, 0], "q": [0.1, 10, 0.707]},
    "Compressor": {"threshold_db": [-60, 0, -18], "ratio": [1, 20, 2], "attack_ms": [0.1, 200, 20], "release_ms": [1, 600, 100]},
    "NoiseGate": {"threshold_db": [-80, -5, -45], "ratio": [1, 20, 5], "attack_ms": [0.1, 200, 5], "release_ms": [1, 600, 80]},
    "Limiter": {"threshold_db": [-24, 0, -1], "release_ms": [1, 500, 100]},
    "Reverb": {"room_size": [0, 1, 0.4], "wet_level": [0, 1, 0.25], "dry_level": [0, 1, 0.75]},
    "Delay": {"delay_seconds": [0.01, 2, 0.25], "feedback": [0, 0.8, 0.25], "mix": [0, 1, 0.25]},
    "ChowTape": {"tape_drive": [0, 1, .54], "tape_saturation": [0, 1, .64], "dry_wet": [0, 100, 70]},
    "ChowMatrix": {"time_ms": [40, 1000, 375], "feedback_percent": [0, 70, 40], "wet": [-36, 0, -10]},
    "DragonflyPlate": {"wet_level": [0, 100, 27], "decay_s": [.1, 5, 1.35], "predelay_ms": [0, 100, 18]},
}
PLUGIN_BUNDLES = {
    "ChowTape": ("CHOWTapeModel.vst3", "2.11.4", "3d7f18863f3680d69aaf38a1216905bb1efdc2782a480c10f15f910f90861b98"),
    "ChowMatrix": ("ChowMatrix.vst3", "1.3.0", "978bb2366b2c314de91a435e08459e3ef57023b82ac76b5cee484a9a39f68bc5"),
    "DragonflyPlate": ("DragonflyPlateReverb.vst3", "3.2.10", "5f874c3eb103149b1127bc5304385643bf297ad5d2d2f7694c87272641e86ac1"),
}
LINUX_PLUGIN_HASHES = {
    "ChowTape": "3d0914651e404d393f509825d53f3d9397c4d037f065a90055b0c7ba42ea1360",
    "ChowMatrix": "611fd1f0191ef7f2c76d545b5bff13c06fd679320343248bbfbecdb2095ba76b",
    "DragonflyPlate": "a389683700a09b321728bc5a2d857492eddc437c9a19e3c54c430ac7c90c0fb4",
}


def effect_plugins(root):
    import hashlib

    result = {}
    for key, (filename, version_name, expected) in PLUGIN_BUNDLES.items():
        bundle = root / filename
        if sys.platform == "linux":
            executable = bundle / "Contents" / "x86_64-linux" / f"{bundle.stem}.so"
            expected = LINUX_PLUGIN_HASHES[key]
        else:
            executable = bundle / "Contents" / "MacOS" / bundle.stem
        if not executable.is_file():
            continue
        try:
            with executable.open("rb") as binary_file:
                digest = hashlib.file_digest(binary_file, "sha256").hexdigest()
        except OSError:
            continue
        if digest == expected:
            result[key] = {"path": str(bundle), "version": version_name, "sha256": digest}
    return result


def effect_chain(params, installed):
    chain = params.get("chain", [])
    if not isinstance(chain, list) or not 1 <= len(chain) <= 12:
        raise UserError("Bitte 1–12 Effekte in die Kette legen.")
    active = []
    for step in chain:
        effect = step.get("effect") if isinstance(step, dict) else None
        if not isinstance(effect, str) or effect not in EFFECTS:
            raise UserError("Die Effektkette enthält ein unbekanntes Modul.")
        if step.get("bypass"):
            continue
        if effect in PLUGIN_BUNDLES and effect not in installed:
            raise UserError("Ein VST3 aus der Effektkette fehlt in der lokalen Installation.")
        values = {key: number(step.get(key, default), low, high, key)
                  for key, (low, high, default) in EFFECTS[effect].items()}
        active.append((effect, values))
    number(params.get("tail", 0), 0, 5, "Ausklang")
    return active


def set_effect_parameters(plugin, name, values):
    if name == "ChowMatrix":
        # The pinned matrix has two default nodes and a JUCE range skewed around 200 ms.
        skew = math.log(.5) / math.log(200 / 1500)
        for node, multiplier in ((1, 1), (2, 1.5)):
            plugin.parameters[f"node_{node}_delay"].raw_value = (values["time_ms"] * multiplier / 1500) ** skew
            plugin.parameters[f"node_{node}_feedback"].raw_value = values["feedback_percent"] / 100
        plugin.dry = 0
        plugin.wet = values["wet"]
        return
    for key, value in values.items():
        setattr(plugin, key, value)
    if name == "DragonflyPlate":
        plugin.dry_level = 100 - values["wet_level"]


def make_effect(pb, name, values, installed):
    if name not in installed:
        return getattr(pb, name)(**values)
    try:
        plugin = pb.load_plugin(installed[name]["path"], initialization_timeout=7)
        if not plugin.is_effect:
            raise ValueError("VST3 is not an audio effect")
        set_effect_parameters(plugin, name, values)
        return plugin
    except (AttributeError, KeyError, OSError, RuntimeError, ValueError) as exc:
        raise UserError(f"Das lokale VST3 {name} konnte nicht geladen oder eingestellt werden.") from exc


def capabilities():
    package = importlib.util.find_spec
    binaries = {key: bool(shutil.which(binary(command))) for key, command in [
        ("rubberband", "rubberband"), ("deepfilter", "deepFilter"), ("rnnoise", "rnnoise_demo"),
        ("ffmpeg", "ffmpeg"),
    ]}
    return binaries | {key: package(module) is not None for key, module in [
        ("samples", "librosa"), ("effects", "pedalboard"), ("reference", "matchering"),
        ("basic_pitch", "basic_pitch"), ("midi", "pretty_midi"), ("loudness", "pyloudnorm"),
    ]}


def estimate_key(y, rate):
    import librosa
    import numpy as np

    if len(y) < rate or np.max(np.abs(y)) < 1e-4:
        return None
    # Sample the beginning, middle and end of longer tracks to bound CQT work.
    span = 24 * rate
    starts = np.linspace(0, max(0, len(y) - span), 3, dtype=int) if len(y) > 3 * span else range(0, len(y), span)
    chroma = np.zeros(12)
    for start in starts:
        section = y[start:start + span]
        if len(section) >= rate and np.max(np.abs(section)) >= 1e-4:
            chroma += librosa.feature.chroma_cqt(y=section, sr=rate, norm=None).sum(axis=1)
    if np.count_nonzero(chroma > chroma.max() * 0.18) < 3:
        return None
    # Krumhansl–Kessler tone profiles in chromatic order from the tonic.
    profiles = {
        "major": [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88],
        "minor": [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17],
    }
    if np.std(chroma) < 1e-9:
        return None
    scores = sorted((float(np.corrcoef(chroma, np.roll(profile, tonic))[0, 1]), tonic, mode)
                    for mode, profile in profiles.items() for tonic in range(12))
    score, tonic, mode = scores[-1]
    if score < 0.55 or score - scores[-2][0] < 0.035:
        return None
    return {"tonic": tonic, "mode": mode}


def tonal_key(value):
    if (not isinstance(value, dict) or type(value.get("tonic")) is not int or not 0 <= value["tonic"] < 12
            or value.get("mode") not in ("major", "minor")):
        raise UserError("Bitte eine gültige Dur- oder Molltonart wählen.")
    return {"tonic": value["tonic"], "mode": value["mode"]}


def detect(source, meta, params):
    import librosa
    y, rate = librosa.load(source, sr=22050, mono=True)
    key = estimate_key(y, rate)
    if params.get("mode") == "key":
        return {"key": key, "origin": "librosa"}
    duration = meta["samples"]
    detected_bpm, beats = librosa.beat.beat_track(y=y, sr=rate)
    bpm = float(detected_bpm.item()) if detected_bpm.size else 0
    result = {"bpm": bpm or None, "confidence": None, "origin": "librosa", "key": key,
              "beats": [round(x * meta["rate"]) for x in librosa.frames_to_time(beats, sr=rate)
                        if 0 <= round(x * meta["rate"]) < duration]}
    if params.get("mode") == "oneshot":
        wait = math.ceil(number(params.get("spacing", 100), 25, 2000, "Mindestabstand") * 22.05 / 512)
        strength = number(params.get("sensitivity", 0.07), 0.01, 1, "Schwelle")
        onsets = librosa.onset.onset_detect(y=y, sr=rate, backtrack=True, wait=wait, delta=strength, units="time")
        pre = round(number(params.get("pre", 8), 0, 100, "Vorlauf") * meta["rate"] / 1000)
        tail = round(number(params.get("tail", 350), 30, 5000, "Ausklang") * meta["rate"] / 1000)
        minimum = round(number(params.get("minimum", 30), 10, 2000, "Mindestlänge") * meta["rate"] / 1000)
        starts = sorted(set(max(0, round(t * meta["rate"]) - pre) for t in onsets))
        result["regions"] = [
            {"start": start, "end": end, "name": f"Treffer {i + 1}"}
            for i, start in enumerate(starts[:128])
            if (end := min(start + tail, starts[i + 1] if i + 1 < len(starts) else duration)) - start >= minimum
        ]
    return result


def notes_from_file(source):
    import pretty_midi
    midi = pretty_midi.PrettyMIDI(str(source))
    tempo_times, tempos = midi.get_tempo_changes()
    signatures = [[s.time, s.numerator, s.denominator] for s in midi.time_signature_changes]
    return {"tracks": [{"program": int(i.program), "drums": bool(i.is_drum), "name": i.name,
                        "notes": [[float(n.start), float(n.end), int(n.pitch), int(n.velocity)] for n in sorted(i.notes, key=lambda n: n.start)],
                        "bends": [[float(b.time), int(b.pitch)] for b in i.pitch_bends],
                        "controls": [[float(c.time), int(c.number), int(c.value)] for c in i.control_changes]}
                       for i in midi.instruments],
            "tempo": [[float(t), float(b)] for t, b in zip(tempo_times, tempos)],
            "signatures": signatures}


def write_midi(path, view, bpm, meter, params):
    import pretty_midi
    numerator, denominator = (int(value) for value in meter.split("/"))
    midi = pretty_midi.PrettyMIDI(initial_tempo=bpm, resolution=960)
    midi.time_signature_changes.append(pretty_midi.TimeSignature(numerator, denominator, 0))
    ratio = number(params.get("ratio", 1), 0.1, 10, "Zeitverhältnis")
    pitch = integer(params.get("transpose", 0), -12, 12, "Transposition")
    quantize = number(params.get("quantize", 0), 0, 1, "Quantisierung")
    grid = 60 / bpm / 4
    origin = number(params.get("origin", 0), 0, 1800, "Grid-Ursprung")
    low = number(params.get("clip_start", 0), 0, 1800, "MIDI-Start")
    high = number(params.get("clip_end", 1800), low, 1800, "MIDI-Ende")
    tracks = view.get("tracks")
    if not isinstance(tracks, list) or not 1 <= len(tracks) <= 64:
        raise UserError("MIDI benötigt 1–64 Spuren.")
    for track in tracks:
        instrument = pretty_midi.Instrument(integer(track["program"], 0, 127, "Programm"),
                                            bool(track["drums"]), str(track["name"])[:80])
        if any(len(track.get(kind, [])) > 20000 for kind in ("notes", "bends", "controls")):
            raise UserError("MIDI-Spur enthält zu viele Ereignisse.")
        for a, b, key, velocity in track["notes"]:
            a, b = number(a, 0, 1800, "Notenstart"), number(b, a + 0.0001, 1800, "Notenende")
            if b <= low or a >= high:
                continue
            a, b = (max(a, low) - low) * ratio, (min(b, high) - low) * ratio
            moved = max(0, a + (round((a - origin) / grid) * grid + origin - a) * quantize)
            shifted = integer(key, 0, 127, "Tonhöhe") + (0 if instrument.is_drum else pitch)
            if not 0 <= shifted <= 127:
                raise UserError("Transposition überschreitet den MIDI-Tonumfang.")
            instrument.notes.append(pretty_midi.Note(integer(velocity, 1, 127, "Velocity"),
                                                     shifted, moved, moved + b - a))
        for when, value in track.get("bends", []):
            when = number(when, 0, 1800, "Pitch-Bend-Zeit")
            if low <= when < high:
                instrument.pitch_bends.append(pretty_midi.PitchBend(integer(value, -8192, 8191, "Pitch Bend"),
                                                                    (when - low) * ratio))
        for when, control, value in track.get("controls", []):
            when = number(when, 0, 1800, "Controller-Zeit")
            control = integer(control, 0, 127, "Controller")
            value = integer(value, 0, 127, "Controllerwert")
            # Keep range/program controls before a clipped note, including the RPN selection and deselection.
            if when < high and (when >= low or control in (6, 38, 100, 101)):
                instrument.control_changes.append(pretty_midi.ControlChange(control, value, max(0, (when - low) * ratio)))
        midi.instruments.append(instrument)
    if not any(track.notes for track in midi.instruments):
        raise UserError("Die Auswahl enthält keine MIDI-Noten.")
    midi.write(str(path))


def version(package):
    from importlib.metadata import version as installed_version
    return f"{package} {installed_version(package)}"


def local_render(tool, inputs, params, project, directory, cancelled, installed=None):
    """Yield (file, role, provenance) for one immutable job snapshot."""
    source, asset = inputs[0] if inputs else (None, None)
    meta = asset.get("meta", {}) if asset else {}
    output = directory / "Ergebnis.wav"
    bpm, meter = project["bpm"], project["meter"]
    engine = "FFmpeg"
    info = {}
    role = "variant"
    if tool == "qa":
        report = qa(source, cancelled) | {key: meta.get(key) for key in ("sample_peak", "clipped_samples", "nonfinite_samples", "rate", "channels", "codec", "bits", "seconds")}
        output = directory / "Qualitätscheck.json"
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2))
        yield output, "analysis", {"engine": engine, **report}
        return
    if tool == "detect":
        report = detect(source, meta, params)
        output = directory / ("Tonart.json" if params.get("mode") == "key" else "Grid und Slices.json")
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2))
        yield output, "analysis", {"engine": version("librosa"), **report}
        return
    if tool in ("loop", "oneshot"):
        regions = params.get("regions", [params])
        if not isinstance(regions, list) or not 1 <= len(regions) <= 128:
            raise UserError("Bitte 1–128 Regionen auswählen.")
        for i, choice in enumerate(regions, 1):
            output = directory / f"{'Loop' if tool == 'loop' else 'Treffer'} {i:02}.wav"
            if choice.get("snap_zero"):
                from array import array
                start, end = region(meta, choice)
                values = array("f", ffmpeg("-ss", start / meta["rate"], "-i", source, "-t", 0.003,
                                           "-ac", 1, "-f", "f32le", "-", cancelled=cancelled)[0])
                for offset in range(1, len(values)):
                    if values[offset - 1] * values[offset] <= 0 and start + offset < end:
                        choice = choice | {"start": start + offset}
                        break
            start, end = render_selection(source, output, meta, choice, cancelled)
            yield output, tool, {"engine": engine, "source_start": start, "source_end": end,
                                 "sample_offset": start, "source_rate": meta["rate"],
                                 "fade_in_ms": choice.get("fade_in", 0), "fade_out_ms": choice.get("fade_out", 0),
                                 "bpm": bpm, "meter": meter, "compact": True}
        return
    if tool == "stretch":
        from fractions import Fraction
        source_bpm = number(params.get("source_bpm", bpm), 30, 300, "Quelltempo")
        target_bpm = number(params.get("target_bpm", bpm), 30, 300, "Zieltempo")
        pitch = number(params.get("pitch", 0), -12, 12, "Halbtöne")
        key = tonal_key(params["source_key"]) if "source_key" in params else None
        ratio = source_bpm / target_bpm
        audio = [(path, item) for path, item in inputs if item["role"] != "midi"]
        if not audio:
            raise UserError("Tempo und Tonhöhe benötigen Audio.")
        if len(audio) > 1 and params.get("preview"):
            raise UserError("Auswahlvorschau ist für eine einzelne Audiodatei verfügbar.")
        rate = audio[0][1]["meta"]["rate"] if len(audio) == 1 else project["rate"]
        start, stop = region(meta, params) if params.get("preview") else (0, meta["samples"])
        if len(audio) > 1 and len({(item["meta"]["rate"], item["meta"]["samples"],
                                    item["meta"].get("project_offset", 0), item["meta"].get("bpm", bpm))
                                   for _, item in audio}) != 1:
            raise UserError("Gruppenrender braucht gleich ausgerichtete Spuren mit identischer Zeitbasis.")
        length = round(Fraction(stop - start, meta["rate"]) * rate)
        all_inputs, labels = [], []
        for i, (path, item) in enumerate(audio):
            normalized = directory / f"source-{i}.wav"
            render_selection(path, normalized, item["meta"], {"start": start, "end": stop}, cancelled)
            all_inputs.extend(["-i", normalized])
            labels.extend(f"{i}.{channel}" for channel in range(item["meta"]["channels"]))
        stacked = directory / "rubberband-input.wav"
        if len(audio) == 1:
            stacked = directory / "source-0.wav"
        else:
            # Join as discrete channels in one offline Rubber Band pass.
            joined = "".join(f"[{index}:a]" for index in range(len(audio)))
            ffmpeg(*all_inputs, "-filter_complex", f"{joined}amerge=inputs={len(audio)}",
                   "-ar", rate, "-c:a", "pcm_f32le", stacked, cancelled=cancelled)
        stretched = directory / "rubberband-output.wav"
        args = ["rubberband", "--fine", "--centre-focus", "--time", ratio, "--pitch", pitch]
        if params.get("formant"):
            args.append("--formant")
        run([*args, stacked, stretched], cancelled)
        desired = round(length * ratio)
        details = {"engine": "Rubber Band R3 offline", "bpm": target_bpm, "source_bpm": source_bpm, "meter": meter,
                   "ratio": ratio, "pitch": pitch, "source_start": start, "source_rate": meta["rate"],
                   "rendered_samples": probe(stretched)["samples"] if len(audio) == 1 else None,
                   "preview_render": bool(params.get("preview"))}
        if key and len(audio) == 1 and pitch == int(pitch):
            details["key"] = {"tonic": (key["tonic"] + int(pitch)) % 12, "mode": key["mode"]}
        for i, (path, item) in enumerate(audio):
            target = directory / ("Tonart.wav" if "key" in details and pitch and ratio == 1 else f"Tempo {i + 1}.wav")
            channels = item["meta"]["channels"]
            layout = "mono" if channels == 1 else "stereo"
            selectors = "|".join(f"c{j}=c{labels.index(f'{i}.{j}')}" for j in range(channels))
            ffmpeg("-i", stretched, "-af", f"pan={layout}|{selectors},apad,atrim=end_sample={desired}",
                   "-c:a", "pcm_f32le", target, cancelled=cancelled)
            yield target, role, details | {"source_asset": item["id"],
                                            "project_offset": round(item["meta"].get("project_offset", 0) * ratio)}
        for path, item in inputs:
            if item["role"] == "midi":
                if pitch != int(pitch):
                    raise UserError("Gemeinsamer MIDI-Export unterstützt ganze Halbtöne.")
                target = directory / f"Tempo {item['id'][:6]}.mid"
                write_midi(target, notes_from_file(path), target_bpm, meter, {"ratio": ratio, "transpose": int(pitch)})
                yield target, "midi", details | {"source_asset": item["id"], "preview_render": False}
        return
    if tool == "effects":
        import pedalboard as pb
        from pedalboard.io import AudioFile
        import soundfile as sf
        installed = installed or {}
        chain = effect_chain(params, installed)
        identities = {effect: {k: info for k, info in installed[effect].items() if k != "path"}
                      for effect, _ in chain if effect in installed}
        active = pb.Pedalboard([make_effect(pb, effect, values, installed) for effect, values in chain])
        selection = directory / "Auswahl.wav"
        start, end = render_selection(source, selection, meta, params if params.get("preview") else {}, cancelled)
        output = directory / ("FX-Vorschau.wav" if params.get("preview") else "Ergebnis.wav")
        with AudioFile(str(selection)) as reader:
            import numpy as np
            channels = 2 if identities else reader.num_channels
            tail = round(float(params.get("tail", 0)) * reader.samplerate)
            with sf.SoundFile(str(output), "w", reader.samplerate, channels, subtype="FLOAT") as writer:
                pending = reader.frames
                while pending:
                    if cancelled():
                        raise Cancelled()
                    block = reader.read(min(pending, 65536))
                    if not block.shape[-1]:
                        raise UserError("Audiodecoder lieferte weniger Samples als gemeldet.")
                    pending -= block.shape[-1]
                    if reader.num_channels < channels:
                        block = np.repeat(block, channels, axis=0)
                    writer.write(active(block, reader.samplerate, reset=False).T)
                if tail:
                    writer.write(active(np.zeros((channels, tail), dtype=np.float32), reader.samplerate, reset=False).T)
                missing = end - start + tail - writer.frames
                if missing > 0:
                    flushed = active(np.zeros((channels, missing + 8192), dtype=np.float32), reader.samplerate, reset=False)
                    if flushed.shape[-1] < missing:
                        raise UserError("Ein Effekt lieferte keine vollständige Audioausgabe.")
                    writer.write(flushed[:, :missing].T)
        engine = version("pedalboard")
        info = {"source_start": start, "source_end": end, "source_rate": meta["rate"],
                "preview_render": bool(params.get("preview")), "plugins": identities}
        if params.get("preview"):
            dry_lufs = qa(selection, cancelled)["lufs"]
            wet_lufs = qa(output, cancelled)["lufs"]
            if dry_lufs is not None and wet_lufs is not None:
                info["comparison_lufs"] = [dry_lufs, wet_lufs]
    elif tool == "reference":
        import matchering
        from matchering.log import Code, ModuleError

        if len(inputs) != 2 or inputs[1][1]["role"] != "reference":
            raise UserError("Bitte Mix und Referenzspur auswählen.")
        target_wav, reference_wav = directory / "Mix.wav", directory / "Referenz.wav"
        for path, wav in ((source, target_wav), (inputs[1][0], reference_wav)):
            ffmpeg("-i", path, "-c:a", "pcm_f32le", wav, cancelled=cancelled)
        try:
            matchering.process(target=str(target_wav), reference=str(reference_wav),
                               results=[matchering.pcm24(str(output))])
        except ModuleError as error:
            if str(error).startswith(f"{int(Code.ERROR_TARGET_EQUALS_REFERENCE)}:"):
                raise UserError("Mix und Referenz enthalten dasselbe Audio. Wähle eine andere Referenzspur.") from error
            raise
        engine = version("matchering")
        info = qa(output, cancelled)
    elif tool == "basic_pitch":
        from basic_pitch import FilenameSuffix, build_icassp_2022_model_path
        from basic_pitch.inference import predict
        selection = directory / "Auswahl.wav"
        start, end = render_selection(source, selection, meta, params, cancelled)
        _, predicted, _ = predict(str(selection), build_icassp_2022_model_path(FilenameSuffix.onnx))
        raw = directory / "prediction.mid"
        predicted.write(str(raw))
        output = directory / "Basic Pitch.mid"
        write_midi(output, notes_from_file(raw), bpm, meter, {"clip_end": (end - start) / meta["rate"]})
        role, engine = "midi", version("basic-pitch")
        info = {"source_start": start, "source_rate": meta["rate"], "bpm": bpm, "meter": meter}
    elif tool == "midi":
        output = directory / "MIDI Bearbeitung.mid"
        write_midi(output, params.get("view") or notes_from_file(source), bpm, meter, params)
        role, engine = "midi", version("pretty-midi")
        info = {"bpm": bpm, "meter": meter}
    elif tool in ("deepfilter", "rnnoise"):
        clean_input = directory / "source.wav"
        start, _ = render_selection(source, clean_input, meta, params if params.get("preview") else {}, cancelled)
        speech = directory / "speech.wav"
        ffmpeg("-i", clean_input, "-ac", 1, "-ar", 48000, "-c:a", "pcm_s16le", speech, cancelled=cancelled)
        frames = probe(speech)["samples"]
        if tool == "deepfilter":
            padded = directory / "speech-padded.wav"
            ffmpeg("-i", speech, "-af", "apad=pad_len=1440", "-c:a", "pcm_s16le", padded, cancelled=cancelled)
            target = directory / "filtered"
            target.mkdir()
            run(["deepFilter", "--compensate-delay", "--output-dir", target, padded], cancelled)
            files = list(target.glob("*.wav"))
            if len(files) != 1 or probe(files[0])["samples"] < frames:
                raise UserError("DeepFilterNet hat keine vollständig zeitkompensierte Datei erzeugt.")
            ffmpeg("-i", files[0], "-af", f"atrim=end_sample={frames}", "-c:a", "pcm_f32le", output, cancelled=cancelled)
            engine = "DeepFilterNet 0.5.6"
        else:
            raw_in, raw_out = directory / "input.pcm", directory / "output.pcm"
            # The demo skips the warm-up frame and drops partial trailing frames.
            padded_frames = (math.ceil(frames / 480) + 1) * 480
            ffmpeg("-i", speech, "-af", f"apad=whole_len={padded_frames}", "-f", "s16le", raw_in, cancelled=cancelled)
            run(["rnnoise_demo", raw_in, raw_out], cancelled)
            if raw_out.stat().st_size < frames * 2:
                raise UserError("RNNoise hat weniger Samples geliefert als erwartet.")
            ffmpeg("-f", "s16le", "-ar", 48000, "-ac", 1, "-i", raw_out, "-af",
                   f"atrim=end_sample={frames}", "-c:a", "pcm_f32le", output, cancelled=cancelled)
            engine = "RNNoise 70f1d25 / 48 kHz mono"

        info = {"channel_mapping": "mono, 48 kHz", "preview_render": bool(params.get("preview"))}
        info.update(source_start=start, source_rate=meta["rate"])
    elif tool == "cut":
        cuts = params.get("cuts")
        if not isinstance(cuts, list) or not 1 <= len(cuts) <= 128:
            raise UserError("Bitte 1–128 geprüfte Schnitte auswählen.")
        mapping, last, result_sample = [], 0, 0
        for cut in sorted([region(meta, cut) for cut in cuts] + [(meta["samples"], meta["samples"])]):
            if cut[0] < last:
                raise UserError("Schnitte dürfen sich nicht überschneiden.")
            if cut[0] > last:
                mapping.append({"source_start": last, "source_end": cut[0], "result_start": result_sample})
                result_sample += cut[0] - last
            last = cut[1]
        if not mapping:
            raise UserError("Schnitte würden die ganze Aufnahme entfernen.")
        segments = []
        for i, segment in enumerate(mapping):
            selection = directory / f"keep-{i}.wav"
            render_selection(source, selection, meta, {"start": segment["source_start"], "end": segment["source_end"]}, cancelled)
            segments.append(f"file '{selection.name}'")
        file_list = directory / "segments.txt"
        file_list.write_text("\n".join(segments))
        ffmpeg("-f", "concat", "-safe", "1", "-i", file_list, "-c:a", "pcm_f32le", output, cancelled=cancelled)
        info = {"edit_map": mapping, "source_rate": meta["rate"], "cuts": cuts}
    elif tool == "mix":
        tracks = params.get("tracks", {})
        solos = any(tracks.get(item["id"], {}).get("solo") for _, item in inputs)
        arguments, filters = [], []
        for i, (path, item) in enumerate(inputs):
            track = tracks.get(item["id"], {})
            if track.get("mute") or (solos and not track.get("solo")):
                continue
            clip = directory / f"mix-{i}.wav"
            render_selection(path, clip, item["meta"], track, cancelled)
            arguments.extend(["-i", clip])
            index = len(filters)
            gain = number(track.get("gain", 0), -60, 12, "Spurpegel")
            pan = number(track.get("pan", 0), -1, 1, "Panorama")
            delay = integer(track.get("offset", 0), 0, project["rate"] * 1800, "Projekt-Offset")
            filters.append(f"[{index}:a]aformat=channel_layouts=stereo,aresample={project['rate']},"
                           f"pan=stereo|c0={1-max(0,pan)}*c0|c1={1+min(0,pan)}*c1,"
                           f"volume={gain}dB,adelay={delay}S:all=1[x{index}]")
        if not filters:
            raise UserError("Der Mix enthält keine hörbare Spur.")
        blend = "".join(f"[x{i}]" for i in range(len(filters))) + f"amix=inputs={len(filters)}:normalize=0"
        ffmpeg(*arguments, "-filter_complex", ";".join([*filters, blend]), "-c:a", "pcm_f32le", output, cancelled=cancelled)
        info = qa(output, cancelled)
    else:
        raise UserError("Unbekanntes Werkzeug.")
    yield output, role, {"engine": engine, **info}
