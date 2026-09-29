#!/usr/bin/env bash
set -euo pipefail

SOURCE_DIR="${1:-$HOME/edgeaccel/toolchains/piper-src-ba3cc06c5248}"
PREFIX="${2:-$HOME/edgeaccel/toolchains/piper-phonemize-ba3cc06c5248}"
REVISION=ba3cc06c5248215928821f1393b2b854a936991a
if [[ -e "$SOURCE_DIR" || -e "$PREFIX" ]]; then
    echo 'Choose new source and install directories, or reuse the existing installation.' >&2
    exit 1
fi
mkdir -p "$SOURCE_DIR"
curl -fL --retry 3 "https://codeload.github.com/rhasspy/piper-phonemize/tar.gz/$REVISION" -o "$SOURCE_DIR/source.tar.gz"
echo "9f5f7ce05445215cb6a0dab684824513e27070b0f9121ad2927374a67d5479fb  $SOURCE_DIR/source.tar.gz" | sha256sum -c -
tar -xzf "$SOURCE_DIR/source.tar.gz" -C "$SOURCE_DIR" --strip-components=1
cmake -S "$SOURCE_DIR" -B "$SOURCE_DIR/build" -DCMAKE_BUILD_TYPE=Release \
    "-DCMAKE_INSTALL_PREFIX=$PREFIX" '-DCMAKE_INSTALL_RPATH=$ORIGIN/../lib'
cmake --build "$SOURCE_DIR/build" --parallel 2
ctest --test-dir "$SOURCE_DIR/build" --output-on-failure
cmake --install "$SOURCE_DIR/build"
printf '%s\n' '{"text":"This is almost twice the current industry production level per train."}' |
    "$PREFIX/bin/piper_phonemize" --language en-us --espeak_data "$PREFIX/share/espeak-ng-data" --json_input
