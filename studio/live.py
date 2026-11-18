"""One-time, project-scoped tickets and an isolated live DSP subprocess."""

import asyncio
import contextlib
import json
import os
import secrets
import signal
import struct
import sys
import time

from anyio import CancelScope
from fastapi import WebSocket, WebSocketDisconnect

from audio_core import engines
from studio.store import AUDIO, Problem

RATE = 48000
BLOCK = 2048
HEADER = struct.Struct("<II")
CHANNELS = 4  # Dry and wet stereo.
ADPCM_STATE = struct.Struct("<hB")
MESSAGE_LIMIT = 8192
TICKET_SECONDS = 20
MAX_SESSIONS = 3


class LiveEffects:
    def __init__(self):
        self.tickets = {}
        self.active = 0

    def issue(self, store, project, asset, body, url):
        now = time.monotonic()
        self.tickets = {token: ticket for token, ticket in self.tickets.items() if ticket[0] > now}
        if len(self.tickets) >= 12 or self.active >= MAX_SESSIONS:
            raise Problem("Die Live-Vorschau ist ausgelastet. Versuche es gleich erneut.", 429)
        item = store.asset(project, asset)
        if item["role"] not in AUDIO or not store.engines["effects"]:
            raise Problem("Für diese Datei ist keine Live-Vorschau verfügbar.")
        meta = item["meta"]
        start, end = engines.region(meta, body)
        if end - start > 30 * meta["rate"]:
            raise Problem("Die Live-Vorschau unterstützt Ausschnitte bis 30 Sekunden.")
        position = engines.integer(body.get("position", start), start, end - 1, "Abspielposition")
        engines.effect_chain(body, store.effect_plugins)
        request = {"source": str(store.path(item)), "start": start / meta["rate"], "duration": (end - start) / meta["rate"],
                   "offset": round((position - start) * RATE / meta["rate"]), "chain": body["chain"],
                   "plugins": store.effect_plugins, "codec": body["codec"]}
        token = secrets.token_urlsafe(32)
        self.tickets[token] = (now + TICKET_SECONDS, request)
        return {"url": url, "ticket": token, "rate": RATE, "frames": BLOCK, "codec": body["codec"]}

    async def connect(self, socket: WebSocket):
        protocols = socket.scope.get("subprotocols", [])
        redeemed = self.tickets.pop(protocols[1], None) if len(protocols) == 2 and protocols[0] == "xo-fx" else None
        if self.active >= MAX_SESSIONS or not redeemed or redeemed[0] <= time.monotonic():
            await socket.close(code=1008)
            return
        self.active += 1
        process = None
        try:
            await socket.accept(subprotocol="xo-fx")
            process = await asyncio.create_subprocess_exec(sys.executable, "-m", "studio.live_worker",
                stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
                start_new_session=True)
            async with asyncio.timeout(18):
                process.stdin.write(json.dumps(redeemed[1]).encode() + b"\n")
                await process.stdin.drain()
                if await process.stdout.readexactly(1) != b"1":
                    raise ValueError("Live engine failed to start")
            compressed = redeemed[1]["codec"] == "adpcm"
            await socket.send_json({"ready": True})
            async with asyncio.timeout(600):
                while True:
                    async with asyncio.timeout(12):
                        event = await socket.receive()
                        if event["type"] == "websocket.disconnect":
                            return
                        message = event.get("text", "").encode()
                        if not message or len(message) > MESSAGE_LIMIT or b"\n" in message or b"\r" in message:
                            raise ValueError("Invalid live command")
                        command = json.loads(message)
                        blocks = command.get("blocks", 1) if isinstance(command, dict) else 0
                        if type(blocks) is not int or not 1 <= blocks <= (3 if compressed else 1):
                            raise ValueError("Invalid live batch")
                        continuation = json.dumps({"loop": command.get("loop") is True}).encode()
                        packets = bytearray()
                        for index in range(blocks):
                            process.stdin.write((message if not index else continuation) + b"\n")
                            await process.stdin.drain()
                            header = await process.stdout.readexactly(HEADER.size)
                            _, frames = HEADER.unpack(header)
                            if frames > BLOCK:
                                raise ValueError("Invalid live frame")
                            if not frames:
                                break
                            size = ADPCM_STATE.size + (frames + 1) // 2 if compressed else frames * 2
                            packets.extend(header + await process.stdout.readexactly(CHANNELS * size))
                        if packets:
                            await socket.send_bytes(bytes(packets))
                        if not frames:
                            await socket.send_json({"end": True})
                            await socket.close()
                            return
        except WebSocketDisconnect:
            pass
        except (TimeoutError, OSError, ValueError, RuntimeError, asyncio.IncompleteReadError):
            with contextlib.suppress(RuntimeError, OSError):
                await socket.close(code=1011, reason="Die Live-Vorschau wurde beendet.")
        finally:
            self.active -= 1
            if process is not None:
                with CancelScope(shield=True):
                    with contextlib.suppress(ProcessLookupError):
                        os.killpg(process.pid, signal.SIGKILL)
                    await process.communicate()
