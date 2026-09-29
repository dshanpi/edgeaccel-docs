#!/bin/bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

# Verify the intended host before apt invokes any old package removal scripts.
sha256sum -c SHA256SUMS
python3 ./ax8850-headers-check --target-only

sudo apt install \
  "$PWD/pahole_1.25-0ubuntu3_arm64.deb" \
  "$PWD/linux-headers-vendor-rk35xx_25.11.0-trunk+ax8850.1_arm64.deb"

/usr/bin/ax8850-headers-check
printf '\nHeaders installation and checks passed. Existing AXCL drivers and PAC were not replaced by this script.\n'
