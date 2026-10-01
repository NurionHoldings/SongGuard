"""Publish UI only; proxy same-origin API to a persistent HTTPS backend."""
import os, shutil
from pathlib import Path
from urllib.parse import urlsplit

root = Path(__file__).resolve().parents[1]
value = os.environ.get('SONG_GUARD_API_ORIGIN', '').strip()
u = urlsplit(value)
if (u.scheme != 'https' or not u.hostname or u.username or u.password
        or u.path not in ('', '/') or u.query or u.fragment
        or any(c.isspace() for c in value) or any(c in value for c in ('*', '\\'))):
    raise SystemExit('Set SONG_GUARD_API_ORIGIN to the HTTPS origin of the persistent Python backend (no path, credentials, or query).')
origin = value.rstrip('/')
dest = root / 'dist'
if dest.exists(): shutil.rmtree(dest)
shutil.copytree(root / 'static', dest)
(dest / '_redirects').write_text(
    f'/api/* {origin}/api/:splat 200\n'
    f'/health {origin}/health 200\n', encoding='utf-8')
print('Netlify UI built with same-origin API proxy. No database or account secrets published.')
