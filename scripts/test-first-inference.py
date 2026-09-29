"""Exercise the downloadable Bash helper with local fixtures; no hardware or network."""
from pathlib import Path
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'static/scripts/ax8850-first-inference.sh'
BASH = os.environ.get('TEST_BASH') or (r'C:\Program Files\Git\bin\bash.exe' if os.name == 'nt' else shutil.which('bash'))


class FirstInferenceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='first inference ')
        self.work = Path(self.tmp.name).as_posix()
        self.prelude = f'''source {shlex.quote(SCRIPT.as_posix())}
WORK_DIR={shlex.quote(self.work)}
MODEL_DIR="$WORK_DIR/models"
SOURCE_DIR="$WORK_DIR/source"
BUILD_DIR="$WORK_DIR/build"
'''

    def tearDown(self):
        self.tmp.cleanup()

    def run_bash(self, body, success=True):
        result = subprocess.run([BASH, '--noprofile', '--norc', '-c', self.prelude + body],
                                capture_output=True, text=True, encoding='utf-8', errors='replace')
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        return result

    def test_versions_match_evidence(self):
        manifest = json.loads((ROOT / 'static/validation/effects/yolo11/download-manifest.json').read_text())
        text = SCRIPT.read_text(encoding='utf-8')
        self.assertIn('MODEL_REV=' + manifest['revision'], text)
        for file in manifest['files']:
            self.assertIn(f"fetch_verified {file['path']} {file['sha256']}", text)
        self.assertIn('cbfa4c76891758983ca2b0c99c11d6621d59af39', text)

    def test_help_and_bash_syntax(self):
        subprocess.run([BASH, '-n', SCRIPT.as_posix()], check=True)
        self.assertIn('Ubuntu/Debian', self.run_bash('main --help').stdout)

    def test_download_and_reuse(self):
        digest = hashlib.sha256(b'fixture').hexdigest()
        self.run_bash(f'''curl() {{
  local target
  while (($#)); do if [[ "$1" == --output ]]; then target=$2; shift; fi; shift; done
  printf fixture > "$target"
}}
fetch_verified nested/model {digest}
curl() {{ exit 99; }}
fetch_verified nested/model {digest}
''')
        self.assertEqual((Path(self.work) / 'models/nested/model').read_bytes(), b'fixture')

    def test_download_failure_never_becomes_valid_file(self):
        self.run_bash('curl() { return 22; }; fetch_verified model deadbeef', success=False)
        self.assertFalse((Path(self.work) / 'models/model').exists())

    def test_bad_download_is_rejected(self):
        self.run_bash('''curl() {
  local target
  while (($#)); do if [[ "$1" == --output ]]; then target=$2; shift; fi; shift; done
  printf broken > "$target"
}
fetch_verified model aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
''', success=False)
        self.assertFalse((Path(self.work) / 'models/model').exists())

    def test_existing_bad_file_is_preserved(self):
        self.run_bash('''mkdir -p "$MODEL_DIR"; printf original > "$MODEL_DIR/model"
curl() { exit 99; }
fetch_verified model aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
''', success=False)
        self.assertEqual((Path(self.work) / 'models/model').read_bytes(), b'original')

    def mock_binary(self, body):
        binary = Path(self.work) / 'build/bin/axcl_yolo11'
        binary.parent.mkdir(parents=True, exist_ok=True)
        binary.write_text('#!/usr/bin/env bash\n' + body + '\n', encoding='utf-8', newline='\n')
        binary.chmod(0o755)

    def test_fresh_results_and_preserved_previous_run(self):
        self.mock_binary('printf image > yolo11_out.jpg')
        self.run_bash('ldd() { printf "all libraries found\\n"; }; run_inference; run_inference')
        self.assertEqual(len(list((Path(self.work) / 'results').glob('run.*/yolo11_out.jpg'))), 2)

    def test_success_exit_without_image_is_failure(self):
        self.mock_binary('exit 0')
        self.run_bash('ldd() { :; }; run_inference', success=False)

    def test_nonzero_exit_is_not_hidden_by_tee(self):
        self.mock_binary('printf image > yolo11_out.jpg; exit 7')
        self.run_bash('ldd() { :; }; run_inference', success=False)

    def test_missing_library_stops_before_running(self):
        self.mock_binary('printf image > yolo11_out.jpg')
        self.run_bash('ldd() { printf "libaxcl_rt.so => not found\\n"; }; run_inference', success=False)
        self.assertFalse((Path(self.work) / 'results').exists())

    def test_device_failure_stops_before_installation(self):
        self.run_bash('''check_environment() { return 1; }
install_dependencies() { touch "$WORK_DIR/installed"; }
main
''', success=False)
        self.assertFalse((Path(self.work) / 'installed').exists())

    def test_source_changes_are_not_overwritten(self):
        self.run_bash('''mkdir -p "$SOURCE_DIR"
git() { if [[ "$*" == *rev-parse* ]]; then printf '%s\\n' "$SOURCE_REV"; else printf ' M file\\n'; fi; }
cmake() { touch "$WORK_DIR/built"; }
prepare_source
''', success=False)
        self.assertFalse((Path(self.work) / 'built').exists())

    def test_only_yolo11_target_is_built(self):
        self.run_bash('''mkdir -p "$SOURCE_DIR" "$BUILD_DIR/bin"
git() { if [[ "$*" == *rev-parse* ]]; then printf '%s\\n' "$SOURCE_REV"; fi; }
cmake() { printf '%s\\n' "$*" >> "$WORK_DIR/cmake-args"; }
printf '#!/usr/bin/env bash\\nexit 0\\n' > "$BUILD_DIR/bin/axcl_yolo11"
chmod +x "$BUILD_DIR/bin/axcl_yolo11"
prepare_source
''')
        self.assertIn('--target axcl_yolo11 --parallel 2', (Path(self.work) / 'cmake-args').read_text())


if __name__ == '__main__':
    unittest.main()
