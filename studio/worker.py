"""Run one CPU audio operation in an isolated Python process."""

import contextlib
import json
import os
import sys
from pathlib import Path

from audio_core.engines import local_render


if __name__ == "__main__":
    os.environ["XO_RENDER_WORKER"] = "1"
    spec = Path(sys.argv[1])
    request = json.loads(spec.read_text())
    inputs = [(Path(path), asset) for path, asset in request["inputs"]]
    with contextlib.redirect_stdout(sys.stderr):
        files = list(local_render(request["tool"], inputs, request["params"], request["project"], spec.parent, lambda: False))
    print(json.dumps([(str(path), role, meta) for path, role, meta in files], allow_nan=False))
