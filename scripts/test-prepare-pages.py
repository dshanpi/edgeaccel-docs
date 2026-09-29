"""Check URL rewriting and preservation of original evidence during publication."""
import importlib.util
import json
import re
from pathlib import Path
import tempfile
import unittest
from urllib.parse import quote

spec = importlib.util.spec_from_file_location('prepare_pages', Path(__file__).with_name('prepare-pages.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PreparePagesTest(unittest.TestCase):
    def test_duplicate_media_and_all_generated_url_formats(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old = 'assets/files/测试视频-123.mp4'
            original = 'resources/测试视频.mp4'
            raw_html = '<a href="unchanged">original attachment</a>\r\n'
            uppercase = re.sub(r'\\u[0-9a-f]{4}', lambda m: '\\u' + m.group()[2:].upper(), json.dumps(old))
            fixture = {
                original: b'video fixture', old: b'video fixture',
                'assets/images/other-123.png': b'unique image',
                'resources/original.html': raw_html.encode(),
                'index.html': f'<video src="/edgeaccel-docs/{quote(old)}"></video>'.encode(),
                'assets/js/main.js': f'let a=base+"{old}";let b={json.dumps(old)};let c={uppercase};'.encode(),
                'search-index.json': json.dumps({'url': '/edgeaccel-docs/' + old}).encode(),
            }
            for name, data in fixture.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            self.assertEqual(module.prepare(root), 1)
            self.assertFalse((root / old).exists())
            self.assertEqual((root / original).read_bytes(), fixture[original])
            self.assertEqual((root / 'resources/original.html').read_bytes(), raw_html.encode())
            self.assertTrue((root / 'assets/images/other-123.png').is_file())
            self.assertIn('/edgeaccel-docs/' + quote(original), (root / 'index.html').read_text())
            self.assertEqual((root / 'assets/js/main.js').read_text().count(quote(original)), 3)
            self.assertEqual(json.loads((root / 'search-index.json').read_text())['url'], '/edgeaccel-docs/' + quote(original))
            self.assertTrue((root / '.nojekyll').exists())
            self.assertEqual(module.prepare(root), 0)


if __name__ == '__main__':
    unittest.main()
