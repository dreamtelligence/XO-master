#!/bin/bash
set -euo pipefail

scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT
cd "$scratch"

download() {
  curl -fLsS --retry 3 "$1" -o "$3"
  printf '%s  %s\n' "$2" "$3" | sha256sum -c -
}

download https://github.com/Rikorose/DeepFilterNet/releases/download/v0.5.6/deep-filter-0.5.6-x86_64-unknown-linux-musl \
  70775e251eee44c0f2451a1e833326cf8bcbbe304d3e7cd12851e6fce72ef7da deepFilter
install -m 755 deepFilter /usr/local/bin/deepFilter

revision=70f1d256acd4b34a572f999a05c87bf00b67730d
download "https://codeload.github.com/xiph/rnnoise/tar.gz/$revision" \
  f61ee0b3f4c4cd337303e003d333357c5eaf25ef5d75a742109ee59e9a0a3932 rnnoise.tgz
tar -xzf rnnoise.tgz
(
  cd "rnnoise-$revision"
  model_hash=0a8755f8e2d834eff6a54714ecc7d75f9932e845df35f8b59bc52a7cfe6e8b37
  model="rnnoise_data-$model_hash.tar.gz"
  download "https://media.xiph.org/rnnoise/models/$model" "$model_hash" "$model"
  ./autogen.sh
  ./configure --disable-shared
  make -j4
  install -m 755 examples/rnnoise_demo /usr/local/bin/rnnoise_demo
)

download https://github.com/jatinchowdhury18/AnalogTapeModel/releases/download/v2.11.4/ChowTapeModel-Linux-x64-2.11.4.deb \
  71aaae1c454ac83ac16b248d4cc99c12bf6d11452a87376fcb6b1e79060e3a5c tape.deb
download https://github.com/Chowdhury-DSP/ChowMatrix/releases/download/v1.3.0/ChowMatrix-Linux-x64-1.3.0.deb \
  332749bba2fcfefeb68c105b9f55fd71aa7a8bfb524f592cbb68cc6c0581a767 matrix.deb
download https://github.com/michaelwillis/dragonfly-reverb/releases/download/3.2.10/dragonfly-reverb-3.2.10-linux-x86_64.tar.xz \
  59f1593120de82e31dd194e2ab1536af14fec2b3ec6ec45abf6d9c8ac02ef430 dragonfly.tar.xz
dpkg-deb -x tape.deb tape
dpkg-deb -x matrix.deb matrix
tar -xf dragonfly.tar.xz
mkdir -p /opt/xo-plugins
cp -a tape/usr/lib/vst3/CHOWTapeModel.vst3 matrix/usr/lib/vst3/ChowMatrix.vst3 \
  dragonfly-reverb-3.2.10/DragonflyPlateReverb.vst3 /opt/xo-plugins/
