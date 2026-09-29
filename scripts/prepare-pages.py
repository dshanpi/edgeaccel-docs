"""Deduplicate emitted media without changing original attachments or evidence."""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import quote


def prepare(root):
    root = Path(root).resolve()
    if not (root / 'index.html').is_file():
        raise ValueError('Expected a completed Docusaurus build directory')
    files = sorted(p for p in root.rglob('*') if p.is_file())
    emitted = {'assets/files', 'assets/images'}

    def is_emitted(path):
        return path.parent.relative_to(root).as_posix() in emitted

    groups = defaultdict(list)
    for path in files:
        # Only media and attachments can have webpack-generated duplicates.
        if is_emitted(path) or path.relative_to(root).parts[0] in {
            'resources', 'validation', 'img', 'scripts', 'examples', 'templates', 'projects'
        }:
            with path.open('rb') as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            groups[(path.suffix.lower(), digest)].append(path)

    replacements = {}
    duplicates = []
    for paths in groups.values():
        canonical = min(paths, key=lambda p: (is_emitted(p), p.as_posix()))
        target = quote(canonical.relative_to(root).as_posix(), safe='/')
        for path in paths:
            if path == canonical or not is_emitted(path):
                continue
            old = path.relative_to(root).as_posix()
            escaped = json.dumps(old, ensure_ascii=True)[1:-1]
            uppercase_escaped = re.sub(r'\\u[0-9a-f]{4}', lambda m: '\\u' + m.group()[2:].upper(), escaped)
            # HTML URLs, webpack strings, and JSON may encode filenames differently.
            for variant in {old, quote(old, safe='/'), quote(old, safe="/!$&'()*+,;=:@"),
                            escaped, uppercase_escaped}:
                replacements[variant] = target
            duplicates.append(path)

    if replacements:
        pattern = re.compile('|'.join(re.escape(key) for key in sorted(replacements, key=len, reverse=True)))
        for path in files:
            relative = path.relative_to(root)
            # Preserve all files copied from static/, including source code and manifests.
            generated = (relative.parts[0] in {'docs', 'search'} and path.suffix == '.html') or (
                relative.parts[0] == 'assets' and path.suffix in {'.js', '.css'}
            ) or (len(relative.parts) == 1 and path.suffix in {'.html', '.json', '.xml'})
            if not generated:
                continue
            text = path.read_text(encoding='utf-8')
            updated = pattern.sub(lambda match: replacements[match.group()], text)
            if updated != text:
                path.write_text(updated, encoding='utf-8', newline='')
        for path in duplicates:
            path.unlink()

    (root / '.nojekyll').touch()
    size = sum(p.stat().st_size for p in root.rglob('*') if p.is_file())
    print(f'Removed {len(duplicates)} duplicate assets; website size: {size / 1_000_000:.1f} MB')
    if size >= 1_000_000_000:
        raise ValueError('Website exceeds the GitHub Pages 1 GB limit')
    return len(duplicates)


if __name__ == '__main__':
    prepare(sys.argv[1] if len(sys.argv) > 1 else 'build')
