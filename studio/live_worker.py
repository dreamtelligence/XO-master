"""Render consecutive preview blocks with persistent effect instances."""

import audioop
import json
import os
import sys

import numpy as np
import pedalboard as pb

from audio_core import engines
from studio.live import ADPCM_STATE, BLOCK, CHANNELS, HEADER, MESSAGE_LIMIT, RATE


class EffectProcessor:
    def __init__(self, installed):
        self.installed = installed
        self.slots = {}
        self.board = pb.Pedalboard()

    def configure(self, chain):
        active = iter(engines.effect_chain({"chain": chain}, self.installed))
        slots, effects = {}, []
        for index, step in enumerate(chain):
            slot = (index, step["effect"])
            previous = self.slots.get(slot)
            if step.get("bypass"):
                if previous:
                    slots[slot] = previous
                continue
            name, values = next(active)
            if previous:
                plugin, old = previous
                if old != values:
                    engines.set_effect_parameters(plugin, name, values)
            else:
                plugin = engines.make_effect(pb, name, values, self.installed)
            slots[slot] = plugin, values
            effects.append(plugin)
        self.slots = slots
        self.board = pb.Pedalboard(effects)

    def process(self, dry):
        wet = self.board(dry, RATE, buffer_size=BLOCK, reset=False)
        if wet.shape[1] < dry.shape[1]:
            wet = np.pad(wet, ((0, 0), (dry.shape[1] - wet.shape[1], 0)))
        if not np.isfinite(wet).all():
            raise ValueError("Invalid audio output")
        return wet[:, :dry.shape[1]]


def main():
    os.environ["XO_RENDER_WORKER"] = "1"
    source, output = sys.stdin.buffer, sys.stdout.buffer
    options = json.loads(source.readline())
    processor = EffectProcessor(options["plugins"])
    processor.configure(options["chain"])
    pcm, _ = engines.ffmpeg("-ss", options["start"], "-i", options["source"], "-t", options["duration"],
                            "-ar", RATE, "-ac", 2, "-f", "f32le", "pipe:1")
    audio = np.frombuffer(pcm, dtype="<f4").reshape(-1, 2)
    if not len(audio):
        raise ValueError("Empty clip")
    offset = min(options["offset"], len(audio) - 1)
    states = [(0, 0)] * CHANNELS
    output.write(b"1")
    output.flush()
    while line := source.readline(MESSAGE_LIMIT + 2):
        command = json.loads(line)
        if "chain" in command:
            processor.configure(command["chain"])
        if offset == len(audio) and command.get("loop") is True:
            offset = 0
        count = min(BLOCK, len(audio) - offset)
        output.write(HEADER.pack(offset, count))
        if count:
            dry = np.ascontiguousarray(audio[offset:offset + count].T)
            wet = processor.process(dry)
            pcm = (np.clip(np.concatenate((dry, wet)), -1, 32767 / 32768) * 32768).astype("<i2")
            # shortcut: audioop is part of the pinned Python 3.11 runtime, replace before upgrading to 3.13.
            if options.get("codec") == "adpcm":
                for channel, samples in enumerate(pcm):
                    state = states[channel]
                    encoded, states[channel] = audioop.lin2adpcm(samples.tobytes() + b"\0\0" * (count % 2), 2, state)
                    output.write(ADPCM_STATE.pack(*state) + encoded)
            else:
                output.write(pcm.tobytes())
            offset += count
        output.flush()
        if not count:
            break


if __name__ == "__main__":
    main()
