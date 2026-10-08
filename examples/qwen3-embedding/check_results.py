"""Check one documented retrieval example against the full original-model CPU reference."""
import argparse
import json
from pathlib import Path
import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=['official-readme', 'chinese-retrieval'], required=True)
    parser.add_argument('--result-dir', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    reference = json.loads((root / 'reference.json').read_text('utf-8'))[args.case]
    result = json.loads((args.result_dir / 'result.json').read_text('utf-8'))
    actual = np.load(args.result_dir / 'embeddings.npy', allow_pickle=False).astype(np.float64)
    expected = np.asarray(reference['vectors'], dtype=np.float64)
    assert result['provider'] == 'AXCLRTExecutionProvider' and result['texts'] == reference['texts']
    assert actual.shape == expected.shape == (4, 1024) and np.isfinite(actual).all()
    norms = np.linalg.norm(actual, axis=1)
    assert np.all(np.abs(norms - 1) <= 1e-5), 'Expected unit vectors.'
    cosines = np.sum(actual * expected, axis=1) / norms / np.linalg.norm(expected, axis=1)
    assert np.all(cosines >= 0.99), 'CPU vector agreement failed.'
    scores = actual[:2] @ actual[2:].T
    cpu_scores = expected[:2] @ expected[2:].T
    assert np.max(np.abs(scores - cpu_scores)) <= 0.02, 'Retrieval score agreement failed.'
    assert np.argmax(scores, axis=1).tolist() == [0, 1], 'Retrieval order differs.'
    assert np.max(np.abs(scores - np.asarray(result['similarities']))) < 1e-6
    assert len(result['samples']) == 4
    for sample in result['samples']:
        assert 1 <= sample['tokens'] <= 512
        assert sample['decoderExecutions'] == 28 * ((sample['tokens'] + 127) // 128)
        assert sample['postExecutions'] == 1
    print('PASS: four complete vectors, original-model agreement and both retrieval matches.')
    print('CPU cosine:', ', '.join(f'{value:.6f}' for value in cosines))


if __name__ == '__main__':
    main()
