"""Offline operator account creation and consistent SQLite backup."""
import argparse, getpass, secrets, sqlite3
from pathlib import Path
import server

p=argparse.ArgumentParser(); sub=p.add_subparsers(dest='command',required=True)
u=sub.add_parser('create-user'); u.add_argument('username'); u.add_argument('--allow-short-password',action='store_true',help='운영자가 지정한 짧은 비밀번호 허용')
b=sub.add_parser('backup'); b.add_argument('destination')
a=p.parse_args(); server.init()
if a.command=='create-user':
    password=getpass.getpass('비밀번호: ')
    if not 3<=len(a.username)<=80 or not (1 if a.allow_short_password else 12)<=len(password)<=200: raise SystemExit('아이디/비밀번호 길이를 확인하세요.')
    if password!=getpass.getpass('비밀번호 확인: '): raise SystemExit('비밀번호 불일치')
    salt=secrets.token_hex(16)
    with server.connect() as c: c.execute('INSERT INTO users(username,salt,password) VALUES(?,?,?)',(a.username,salt,server.password(password,salt)))
    print('계정 생성 완료')
else:
    path=Path(a.destination)
    if path.exists(): raise SystemExit('기존 백업을 덮어쓰지 않습니다.')
    path.parent.mkdir(parents=True,exist_ok=True)
    with server.connect() as source, sqlite3.connect(str(path)) as dest: source.backup(dest)
    path.chmod(0o600);print('백업 완료')
