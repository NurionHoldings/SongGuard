import os, json, sqlite3, secrets, hashlib, hmac, time, io, zipfile, threading
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from http.cookies import SimpleCookie
from datetime import date, timedelta
from core import ledger, scenario, preemption, VARIABLES
from drafts import draft
from paperwork import schemas, missing, html as filing_html, CHECKS
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).parent
DB = os.environ.get('SONG_GUARD_DB', str(ROOT/'data'/'songguard.sqlite3'))
STAGES = ['관리','집행준비','경매접수','매각진행','배당검토','수령대기','일부회수','전액회수','직접취득']
LOGIN_ATTEMPTS = {}
LOGIN_LOCK = threading.Lock()
def connect():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c
def init():
    Path(DB).parent.mkdir(parents=True,exist_ok=True)
    with connect() as c:
        c.executescript('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE, salt TEXT, password TEXT);
        CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id INTEGER,csrf TEXT,expires REAL);
        CREATE TABLE IF NOT EXISTS records(id TEXT PRIMARY KEY,user_id INTEGER,kind TEXT,payload TEXT,version INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,user_id INTEGER,at TEXT,action TEXT,record_id TEXT);
        CREATE TABLE IF NOT EXISTS evidence(id TEXT PRIMARY KEY,user_id INTEGER,record_id TEXT,name TEXT,body BLOB);''')
    try: os.chmod(DB,0o600)
    except OSError: pass
def password(value,salt): return hashlib.pbkdf2_hmac('sha256',value.encode(),bytes.fromhex(salt),600000).hex()
def audit(c,uid,action,rid): c.execute('INSERT INTO audit(user_id,at,action,record_id) VALUES(?,datetime(\'now\'),?,?)',(uid,action,rid))
def validate(kind,p):
    if kind not in ('claim','asset','case','task','event'): raise ValueError('잘못된 자료 유형')
    if not isinstance(p,dict) or not p.get('title'): raise ValueError('제목이 필요합니다.')
    if len(json.dumps(p))>100000: raise ValueError('자료 크기 초과')
    if kind=='claim': ledger(p)
    if kind=='case':
        if p.get('stage') not in STAGES: raise ValueError('잘못된 사건 단계')
        if p.get('stage') in ('전액회수','직접취득') and not p.get('completion_evidence'): raise ValueError('종결에는 입금 또는 취득 증빙 ID가 필요합니다.')
        for key in ('auction_date','distribution_date','claim_deadline','special_deadline'):
            if p.get(key): date.fromisoformat(p[key])
    if kind=='task':
        date.fromisoformat(p['due'])
        if p.get('done') and not p.get('evidence'): raise ValueError('완료 증빙 ID가 필요합니다.')

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def send(self,status,data,ctype='application/json; charset=utf-8',headers=None):
        raw=json.dumps(data,ensure_ascii=False).encode() if ctype.startswith('application/json') else data
        self.send_response(status)
        for k,v in {'Content-Type':ctype,'Content-Length':str(len(raw)),'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','X-Frame-Options':'DENY','Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",**(headers or {})}.items(): self.send_header(k,v)
        self.end_headers(); self.wfile.write(raw)
    def body(self):
        n=int(self.headers.get('Content-Length',0))
        if n>12*1024*1024: raise ValueError('파일은 12MB 이하로 업로드하세요.')
        return self.rfile.read(n)
    def session(self):
        cookies=SimpleCookie(); cookies.load(self.headers.get('Cookie',''))
        token=cookies.get('sg_session')
        with connect() as c: row=c.execute('SELECT * FROM sessions WHERE token=? AND expires>?',(token.value if token else '',time.time())).fetchone()
        return dict(row) if row else None
    def do_GET(self): self.handle_request('GET')
    def do_POST(self): self.handle_request('POST')
    def handle_request(self,method):
        try: self.route(method)
        except (ValueError,KeyError,TypeError,json.JSONDecodeError) as e: self.send(400,{'error':str(e)})
        except Exception: self.send(500,{'error':'처리에 실패했습니다. 자료를 확인한 뒤 재시도하세요.'})
    def route(self,method):
        path=self.path.split('?')[0]
        if path=='/health': return self.send(200,{'status':'ok'})
        if not path.startswith('/api/'):
            if method!='GET': return self.send(405,{'error':'허용되지 않는 요청'})
            files={'/':'index.html','/app.js':'app.js','/style.css':'style.css','/paperwork.js':'paperwork.js','/print.css':'print.css','/print.js':'print.js','/logo.png':'logo.png'}
            if path not in files: return self.send(404,{'error':'없음'})
            types={'.png':'image/png','.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8'}
            file=ROOT/'static'/files[path]; return self.send(200,file.read_bytes(),types[file.suffix])
        if method=='POST':
            origin=self.headers.get('Origin')
            if origin and origin.split('://',1)[-1]!=self.headers.get('Host'): return self.send(403,{'error':'외부 출처 요청 차단'})
        if path in ('/api/register','/api/login') and method=='POST':
            with LOGIN_LOCK:
                key=self.client_address[0]; attempts=[t for t in LOGIN_ATTEMPTS.get(key,[]) if t>time.time()-900]
                if len(attempts)>=20: return self.send(429,{'error':'로그인 시도가 많습니다. 15분 후 다시 시도하세요.'})
                LOGIN_ATTEMPTS[key]=attempts+[time.time()]
            p=json.loads(self.body()); username=p['username'].strip(); secret=p['password']
            if not 3<=len(username)<=80 or not 12<=len(secret)<=200: raise ValueError('아이디 3~80자, 비밀번호 12~200자가 필요합니다.')
            with connect() as c:
                user=c.execute('SELECT * FROM users WHERE username=?',(username,)).fetchone()
                if path.endswith('register'):
                    if os.environ.get('SONG_GUARD_ALLOW_REGISTRATION','false')!='true': return self.send(403,{'error':'신규 가입이 비활성화되어 있습니다.'})
                    if user: raise ValueError('사용할 수 없는 아이디')
                    salt=secrets.token_hex(16); uid=c.execute('INSERT INTO users(username,salt,password) VALUES(?,?,?)',(username,salt,password(secret,salt))).lastrowid
                else:
                    salt=user['salt'] if user else '00'*16
                    valid=hmac.compare_digest(password(secret,salt),user['password'] if user else '0'*64)
                    if not user or not valid: return self.send(401,{'error':'로그인 정보를 확인하세요.'})
                    uid=user['id']
                token,csrf=secrets.token_urlsafe(32),secrets.token_urlsafe(32)
                c.execute('DELETE FROM sessions WHERE expires<?',(time.time(),))
                c.execute('INSERT INTO sessions VALUES(?,?,?,?)',(token,uid,csrf,time.time()+28800))
            secure='; Secure' if os.environ.get('SONG_GUARD_SECURE_COOKIE','true')=='true' else ''
            return self.send(200,{'csrf':csrf},headers={'Set-Cookie':f'sg_session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800{secure}'})
        s=self.session()
        if not s: return self.send(401,{'error':'로그인이 필요합니다.'})
        uid=s['user_id']
        if method=='POST' and not hmac.compare_digest(self.headers.get('X-CSRF-Token',''),s['csrf']): return self.send(403,{'error':'인증 토큰을 확인하세요.'})
        if path=='/api/state' and method=='GET':
            with connect() as c:
                records=[{**dict(r),'payload':json.loads(r['payload'])} for r in c.execute('SELECT id,kind,payload,version FROM records WHERE user_id=?',(uid,))]
                logs=[dict(r) for r in c.execute('SELECT at,action,record_id FROM audit WHERE user_id=? ORDER BY id DESC LIMIT 100',(uid,))]
                evidence=[dict(r) for r in c.execute('SELECT id,record_id,name FROM evidence WHERE user_id=?',(uid,))]
            return self.send(200,{'csrf':s['csrf'],'records':records,'audit':logs,'evidence':evidence,'variables':VARIABLES,'stages':STAGES,'forms':schemas(),'connectors':{'court':'사람이 출력서류 접수 · 접수증 등록','registry':'미연동 · 등기 원문 등록','bank':'미연동 · 입금 증빙 등록'}})
        if path.startswith('/api/print/') and method=='GET':
            rid=path.rsplit('/',1)[-1]
            with connect() as c: row=c.execute('SELECT payload FROM records WHERE id=? AND user_id=? AND kind=\'filing\'',(rid,uid)).fetchone()
            if not row: return self.send(404,{'error':'접수서류 없음'})
            return self.send(200,filing_html({**json.loads(row['payload']),'id':rid}).encode(),'text/html; charset=utf-8')
        if path=='/api/filing' and method=='POST':
            p=json.loads(self.body()); action=p['action']; rid=p.get('id') or secrets.token_hex(12)
            with connect() as c:
                old=c.execute('SELECT * FROM records WHERE id=? AND user_id=? AND kind=\'filing\'',(rid,uid)).fetchone()
                if p.get('id') and not old: return self.send(404,{'error':'접수서류 없음'})
                if old and p.get('version')!=old['version']: return self.send(409,{'error':'서류가 변경되었습니다. 새로고침하세요.'})
                doc=json.loads(old['payload']) if old else {}
                if action=='save':
                    if doc and doc['status']!='작성중': raise ValueError('확정된 문서는 수정할 수 없습니다. 새 문서를 생성하세요.')
                    kind=p['form_kind']; data=p['data']; cid=p['case_id']
                    if kind not in schemas() or not isinstance(data,dict): raise ValueError('잘못된 서식')
                    if len(json.dumps(data))>100000: raise ValueError('서류 크기 초과')
                    allowed={x['key'] for x in schemas()[kind]['fields']}
                    data={k:str(v) for k,v in data.items() if k in allowed}
                    case_row=c.execute('SELECT * FROM records WHERE id=? AND user_id=? AND kind=\'case\'',(cid,uid)).fetchone()
                    if not case_row: raise ValueError('연결 경매사건을 선택하세요.')
                    case=json.loads(case_row['payload']); snapshot={'case':dict(case_row)}
                    for key in ('claim','asset'):
                        source=c.execute('SELECT id,payload,version FROM records WHERE id=? AND user_id=?',(case.get(key+'_id',''),uid)).fetchone()
                        if source: snapshot[key]=dict(source)
                    doc={'title':schemas()[kind]['title'],'form_kind':kind,'case_id':cid,'data':data,'status':'작성중','checks':{},'snapshot':snapshot}
                elif action=='approve':
                    if doc.get('status')!='작성중': raise ValueError('작성중 문서만 확정할 수 있습니다.')
                    errors=missing(doc['form_kind'],doc['data'])
                    if errors: raise ValueError('필수 입력 확인: '+', '.join(errors))
                    checks=p.get('checks',{})
                    if any(checks.get(k) is not True for k in CHECKS): raise ValueError('제출 전 확인사항을 모두 확인하세요.')
                    if doc['form_kind']=='petition':
                        source=doc['snapshot'].get('asset'); asset=json.loads(source['payload']) if source else {}
                        if asset.get('ownership')!='근저당': raise ValueError('이 임의경매 서식은 근저당 실행용입니다. 지분이전·가등기담보는 별도 검토하세요.')
                    if doc['form_kind']=='preemption':
                        case=json.loads(doc['snapshot']['case']['payload'])
                        if case.get('type')!='share': raise ValueError('전체·공유물분할·일괄매각에는 이 우선매수 서식을 바로 확정할 수 없습니다.')
                        source=doc['snapshot'].get('asset'); asset=json.loads(source['payload']) if source else {}
                        if asset.get('ownership')!='공유지분 소유': raise ValueError('공유자 지위를 확인한 공유지분 자산을 연결하세요. 담보 목적 이전은 법률 검토 후 분류해야 합니다.')
                    doc.update(status='출력준비',checks=checks,approved_at=time.time())
                elif action=='printed':
                    if doc.get('status')!='출력준비': raise ValueError('확정된 출력준비 문서만 출력확인할 수 있습니다.')
                    if p.get('confirmed') is not True: raise ValueError('실제 출력본 확인이 필요합니다.')
                    doc.update(status='출력확인',printed_at=time.time())
                elif action=='submit':
                    if doc.get('status')!='출력확인': raise ValueError('출력·서명·첨부 준비를 확인한 뒤 접수를 등록하세요.')
                    receipt=p.get('receipt',{}); date.fromisoformat(receipt['date'])
                    if receipt.get('signed') is not True: raise ValueError('서명·첨부자료를 갖춘 실제 접수를 확인하세요.')
                    if not receipt.get('number') or not receipt.get('by'): raise ValueError('접수번호/사건번호와 접수자를 입력하세요.')
                    proof=c.execute('SELECT 1 FROM evidence WHERE id=? AND user_id=? AND record_id=?',(receipt.get('evidence',''),uid,doc['case_id'])).fetchone()
                    if not proof: raise ValueError('해당 사건에 접수증 증빙을 먼저 업로드하세요.')
                    doc.update(status='접수완료',receipt={k:receipt.get(k,'') for k in ('date','number','by','evidence','notes','case_number')})
                    if doc['form_kind']=='petition':
                        row=c.execute('SELECT payload FROM records WHERE id=? AND user_id=?',(doc['case_id'],uid)).fetchone(); case=json.loads(row['payload'])
                        if case['stage'] in ('관리','집행준비'): case['stage']='경매접수'
                        if receipt.get('case_number'): case['number']=receipt['case_number']
                        c.execute('UPDATE records SET payload=?,version=version+1 WHERE id=? AND user_id=?',(json.dumps(case,ensure_ascii=False),doc['case_id'],uid))
                        audit(c,uid,'사람 접수 확인 후 사건 갱신',doc['case_id'])
                    task={'title':doc['title']+' 접수 후 진행·보정 안내 확인','due':(date.fromisoformat(receipt['date'])+timedelta(days=7)).isoformat(),'case_id':doc['case_id'],'done':False,'notes':'접수 7일 후 내부 확인일입니다. 법정기한이 아니며 법원 통지의 실제 기한을 별도 등록하세요.'}
                    tid=secrets.token_hex(12);c.execute('INSERT INTO records VALUES(?,?,?,?,1)',(tid,uid,'task',json.dumps(task,ensure_ascii=False)))
                    audit(c,uid,'접수 후 확인업무 생성',tid)
                else: raise ValueError('지원되지 않는 접수 작업')
                c.execute('INSERT INTO records VALUES(?,?,?,?,1) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,version=records.version+1',(rid,uid,'filing',json.dumps(doc,ensure_ascii=False)))
                audit(c,uid,'접수서류 '+action,rid)
            return self.send(200,{'id':rid})
        if path=='/api/logout' and method=='POST':
            with connect() as c: c.execute('DELETE FROM sessions WHERE token=?',(s['token'],))
            return self.send(200,{},headers={'Set-Cookie':'sg_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'})
        if path.startswith('/api/draft/') and method=='GET':
            rid=path.rsplit('/',1)[-1]
            kind=parse_qs(urlsplit(self.path).query).get('kind',['statement'])[0]
            with connect() as c:
                row=c.execute('SELECT payload FROM records WHERE id=? AND user_id=? AND kind=\'case\'',(rid,uid)).fetchone()
                if not row: return self.send(404,{'error':'사건 없음'})
                case=json.loads(row['payload']); linked={}
                for key in ('claim','asset'):
                    record=c.execute('SELECT payload FROM records WHERE id=? AND user_id=?',(case.get(key+'_id',''),uid)).fetchone()
                    linked[key]=json.loads(record['payload']) if record else {}
            text=draft(kind,case,linked['claim'],linked['asset'])
            return self.send(200,text.encode(),'text/plain; charset=utf-8',{'Content-Disposition':'attachment; filename="Song_Guard_draft.txt"'})
        if path in ('/api/calculate','/api/scenario','/api/preemption') and method=='POST':
            p=json.loads(self.body()); return self.send(200,{'result':{'/api/calculate':ledger,'/api/scenario':scenario,'/api/preemption':preemption}[path](p)})
        if path=='/api/record' and method=='POST':
            p=json.loads(self.body()); kind=p['kind']; data=p['payload']; validate(kind,data); rid=p.get('id') or secrets.token_hex(12)
            with connect() as c:
                for key in ('claim_id','asset_id','case_id'):
                    if data.get(key) and not c.execute('SELECT 1 FROM records WHERE id=? AND user_id=? AND kind=?',(data[key],uid,key.removesuffix('_id'))).fetchone(): raise ValueError('연결 자료 유형이 맞지 않거나 접근할 수 없습니다.')
                for key in ('evidence','completion_evidence'):
                    if data.get(key) and not c.execute('SELECT 1 FROM evidence WHERE id=? AND user_id=?',(data[key],uid)).fetchone(): raise ValueError('증빙 파일을 먼저 업로드하세요.')
                if data.get('completion_evidence') and not c.execute('SELECT 1 FROM evidence WHERE id=? AND user_id=? AND record_id=?',(data['completion_evidence'],uid,rid)).fetchone(): raise ValueError('종결 증빙은 해당 사건에 연결되어야 합니다.')
                old=c.execute('SELECT * FROM records WHERE id=?',(rid,)).fetchone()
                if old and old['user_id']!=uid: return self.send(404,{'error':'자료 없음'})
                if old and (p.get('version')!=old['version'] or old['kind']!=kind): return self.send(409,{'error':'자료가 변경되었습니다. 새로고침 후 다시 저장하세요.'})
                c.execute('INSERT INTO records VALUES(?,?,?,?,1) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,version=records.version+1',(rid,uid,kind,json.dumps(data,ensure_ascii=False)))
                audit(c,uid,'수정' if old else '등록',rid)
                if kind=='case':
                    schedules=[('auction_date','직접 입찰·공유자 우선매수 검토',7),('distribution_date','배당표·채권액·수령 요건 검토',3),('claim_deadline','채권신고·배당요구 필요 여부 및 제출 확인',3),('special_deadline','채권자 매수 특별지급 신고 검토',1)]
                    for key,label,lead in schedules:
                        tid=hashlib.sha256((rid+key).encode()).hexdigest()[:24]
                        previous=c.execute('SELECT payload FROM records WHERE id=? AND user_id=?',(tid,uid)).fetchone()
                        if previous and json.loads(previous['payload']).get('done'): continue
                        if not data.get(key):
                            if previous: c.execute('DELETE FROM records WHERE id=? AND user_id=?',(tid,uid)); audit(c,uid,'자동 업무 기일 해제',tid)
                            continue
                        task={'title':label,'due':(date.fromisoformat(data[key])-timedelta(days=lead)).isoformat(),'case_id':rid,'done':False,'notes':'자동 준비일. 원문 기한: '+data[key]+'. 등록 기일의 정확성과 변경 여부를 확인하세요.','source_date':data[key],'automated':True}
                        c.execute('INSERT INTO records VALUES(?,?,?,?,1) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,version=records.version+1',(tid,uid,'task',json.dumps(task,ensure_ascii=False)))
                        audit(c,uid,'사건 기일 준비업무 갱신',tid)
                if kind=='event' and not old:
                    category=data.get('category','미분류 변수'); actions=VARIABLES.get(category,VARIABLES['미분류 변수'])
                    task={'title':category+' 검토','due':data['due'],'case_id':data.get('case_id',''),'notes':' / '.join(actions),'done':False}
                    validate('task',task); tid=secrets.token_hex(12)
                    c.execute('INSERT INTO records VALUES(?,?,?,?,1)',(tid,uid,'task',json.dumps(task,ensure_ascii=False))); audit(c,uid,'변수 대응업무 생성',tid)
            return self.send(200,{'id':rid})
        if path.startswith('/api/upload/') and method=='POST':
            rid=path.rsplit('/',1)[-1]
            with connect() as c:
                if not c.execute('SELECT 1 FROM records WHERE id=? AND user_id=?',(rid,uid)).fetchone(): return self.send(404,{'error':'자료 없음'})
                raw=self.body(); name=self.headers.get('X-File-Name','evidence'); eid=secrets.token_hex(12)
                if not raw: raise ValueError('빈 파일')
                c.execute('INSERT INTO evidence VALUES(?,?,?,?,?)',(eid,uid,rid,name[:200],raw)); audit(c,uid,'증빙 업로드',rid)
            return self.send(200,{'id':eid})
        if path.startswith('/api/evidence/') and method=='GET':
            with connect() as c: row=c.execute('SELECT body FROM evidence WHERE id=? AND user_id=?',(path.rsplit('/',1)[-1],uid)).fetchone()
            if not row: return self.send(404,{'error':'자료 없음'})
            return self.send(200,row['body'],'application/octet-stream',{'Content-Disposition':'attachment; filename="evidence.bin"'})
        if path=='/api/export' and method=='GET':
            buf=io.BytesIO()
            with connect() as c,zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
                rows=[{**dict(r),'payload':json.loads(r['payload'])} for r in c.execute('SELECT id,kind,payload,version FROM records WHERE user_id=?',(uid,))]
                z.writestr('records.json',json.dumps(rows,ensure_ascii=False,indent=2))
                z.writestr('audit.json',json.dumps([dict(r) for r in c.execute('SELECT at,action,record_id FROM audit WHERE user_id=?',(uid,))],ensure_ascii=False))
                for r in c.execute('SELECT * FROM evidence WHERE user_id=?',(uid,)): z.writestr('evidence/'+r['id'],r['body'])
            return self.send(200,buf.getvalue(),'application/zip',{'Content-Disposition':'attachment; filename="Song_Guard_export.zip"'})
        return self.send(404,{'error':'지원되지 않는 경로'})

if __name__=='__main__':
    init(); ThreadingHTTPServer(('0.0.0.0',int(os.environ.get('PORT','8000'))),Handler).serve_forever()
