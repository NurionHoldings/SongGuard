import os, shutil, subprocess, tempfile, unittest
from pathlib import Path

class NetlifyBuild(unittest.TestCase):
    def run_build(self, origin):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'scripts').mkdir();(root/'static').mkdir()
            shutil.copy(Path(__file__).parents[1]/'scripts/build_netlify.py',root/'scripts')
            (root/'static/index.html').write_text('public UI')
            (root/'private.sqlite3').write_text('must not publish')
            env={**os.environ,'SONG_GUARD_API_ORIGIN':origin}
            result=subprocess.run(['python',str(root/'scripts/build_netlify.py')],env=env,capture_output=True)
            redirect=(root/'dist/_redirects').read_text() if result.returncode==0 else ''
            files={p.name for p in (root/'dist').glob('*')}
            return result.returncode,redirect,files
    def test_origin_required_and_https_only(self):
        for origin in ('','http://backend.test','https://user:secret@backend.test','https://backend.test/api','https://backend.test?secret=x','https://backend.test\n/anything'):
            self.assertNotEqual(self.run_build(origin)[0],0)
    def test_proxy_build_publishes_only_static_files(self):
        code,redirect,files=self.run_build('https://backend.test/')
        self.assertEqual(code,0)
        self.assertEqual(redirect,'/api/* https://backend.test/api/:splat 200\n/health https://backend.test/health 200\n')
        self.assertEqual(files,{'index.html','_redirects'})
