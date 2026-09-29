#!/bin/bash
set -euo pipefail
ROOT=/home/baiwen/ax-pipeline
BUILD="$ROOT/build_axcl-aarch64_ci"
cd "$ROOT/six"
g++ -O2 -std=c++17 -pthread -Wall -Wextra src/six_app.cpp -o bin/six_app.new \
 -I"$ROOT/include" -I"$ROOT/third-party/json" -I"$ROOT/deps/ax-video-sdk/include" \
 -I"$ROOT/plugins/common/npu/include" -I"$ROOT/plugins/common/npu/src/npu/runner/axcl" -I/usr/include/axcl -I"$ROOT/deps/ax-video-sdk/src/common" \
 "$BUILD/plugins/common/npu/libax_plugin_npu_common.a" "$BUILD/libax_pipeline_tracking.a" "$BUILD/third-party/ByteTrack/libByteTrack.a" \
 -L"$BUILD/deps/ax-video-sdk-build" -L/usr/lib/axcl -lax_video_sdk -laxcl_ivps -laxcl_rt -laxcl_npu -ldl \
 $(pkg-config --cflags --libs opencv4) -Wl,--allow-shlib-undefined \
 -Wl,-rpath,"$BUILD/deps/ax-video-sdk-build:/usr/lib/axcl"


mv -f bin/six_app.new bin/six_app

