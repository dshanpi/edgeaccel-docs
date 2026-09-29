"""Run the fixed SenseVoice package on files; no microphone or server required."""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import soundfile as sf


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--model-dir', type=Path, default=Path('.'))
    p.add_argument('--out', type=Path, default=Path('sensevoice-result.json'))
    p.add_argument('--languages', nargs='+', default=['zh', 'en', 'yue', 'ja', 'ko'])
    args = p.parse_args()
    root = args.model_dir.resolve()
    sys.path.insert(0, str(root / 'python'))
    from SenseVoiceAx import SenseVoiceAx
    model_dir = root / 'sensevoice_ax650'
    start = time.perf_counter()
    model = SenseVoiceAx(str(model_dir/'sensevoice.axmodel'), str(model_dir/'am.mvn'),
                         str(model_dir/'tokens.txt'), str(model_dir/'chn_jpn_yue_eng_ko_spectok.bpe.model'),
                         max_seq_len=256, streaming=False)
    result = {'provider': 'AXCLRTExecutionProvider', 'mode': 'non-streaming',
              'loadSeconds': time.perf_counter()-start, 'samples': []}
    for language in args.languages:
        assert language in ['zh', 'en', 'yue', 'ja', 'ko'], language
        path = root/'example'/f'{language}.mp3'
        info = sf.info(path)
        start = time.perf_counter()
        text = model.infer(str(path), language, print_rtf=True)
        seconds = time.perf_counter()-start
        entry = {'file': f'{language}.mp3', 'language': language, 'text': text,
                 'audioSeconds': info.duration, 'wallSeconds': seconds, 'wallRTF': seconds/info.duration,
                 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        result['samples'].append(entry)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        print(json.dumps(entry, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
