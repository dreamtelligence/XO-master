#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."
if [[ ! -x .venv/bin/python ]]; then
  uv venv --python 3.11 .venv
fi
uv pip sync --python .venv/bin/python requirements-workspace.lock
npm --prefix web ci --no-audit --no-fund

if [[ ${1:-} != --speech ]]; then
  exit 0
fi

if [[ "$(uname -s)-$(uname -m)" != Darwin-arm64 ]]; then
  echo 'Das gepinnte Sprachsetup in diesem Skript setzt macOS auf Apple Silicon voraus.' >&2
  exit 1
fi
for binary in autoreconf automake glibtoolize curl shasum make; do
  command -v "$binary" >/dev/null || { echo "Benötigt: $binary" >&2; exit 1; }
done

scratch=$(mktemp -d "${TMPDIR:-/tmp}/xo-speech.XXXXXX")
trap 'rm -rf "$scratch"' EXIT
venv_bin="$PWD/.venv/bin"

download() {
  local url=$1 hash=$2 file=$3
  curl -fLsS "$url" -o "$file"
  printf '%s  %s\n' "$hash" "$file" | shasum -a 256 -c -
}

download https://github.com/Rikorose/DeepFilterNet/releases/download/v0.5.6/deep-filter-0.5.6-aarch64-apple-darwin \
  4601e7f4e4c03e59a4c5b5000216ef3add3e808799cfccd95e14e83ea4611081 "$scratch/deepFilter"
install -m 755 "$scratch/deepFilter" "$venv_bin/deepFilter"

revision=70f1d256acd4b34a572f999a05c87bf00b67730d
download "https://codeload.github.com/xiph/rnnoise/tar.gz/$revision" \
  f61ee0b3f4c4cd337303e003d333357c5eaf25ef5d75a742109ee59e9a0a3932 "$scratch/rnnoise.tgz"
tar -xzf "$scratch/rnnoise.tgz" -C "$scratch"
cd "$scratch/rnnoise-$revision"
model_hash=0a8755f8e2d834eff6a54714ecc7d75f9932e845df35f8b59bc52a7cfe6e8b37
model="rnnoise_data-$model_hash.tar.gz"
download "https://media.xiph.org/rnnoise/models/$model" "$model_hash" "$model"
./autogen.sh
./configure --disable-shared
make -j4
install -m 755 examples/rnnoise_demo "$venv_bin/rnnoise_demo"
