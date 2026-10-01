import unittest, tempfile, threading, json, urllib.request, urllib.error, http.cookiejar, sqlite3, os
import server

class API(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(); server.DB=cls.tmp.name+'/test.db'
        os.environ['SONG_GUARD_ALLOW_REGISTRATION']='true'; os.environ['SONG_GUARD_SECURE_COOKIE']='false'
        server.init(); cls.http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        cls.base='http://127.0.0.1:'+str(cls.http.server_port)
        threading.Thread(target=cls.http.serve_forever,daemon=True).start()
    @classmethod
    def tearDownClass(cls): cls.http.shutdown(); cls.http.server_close(); cls.tmp.cleanup()
    def client(self): return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    def request(self,client,path,data=None,csrf='',raw=None,headers=None):
        h={'X-CSRF-Token':csrf,**(headers or {})}; body=raw if raw is not None else json.dumps(data).encode() if data is not None else None
        req=urllib.request.Request(self.base+path,data=body,headers=h)
        try:
            with client.open(req) as r: return r.status,r.read(),r.headers
        except urllib.error.HTTPError as e: return e.code,e.read(),e.headers
    def user(self,name):
        c=self.client(); status,body,_=self.request(c,'/api/register',{'username':name,'password':'long-test-password-123'})
        self.assertEqual(status,200);return c,json.loads(body)['csrf']
    def test_full_workflow_and_isolation(self):
        a,csrf=self.user('owner-a'); b,other=self.user('owner-b')
        p={'kind':'case','payload':{'title':'Test case','stage':'매각진행','auction_date':'2026-11-20'}}
        status,body,_=self.request(a,'/api/record',p,csrf);self.assertEqual(status,200);rid=json.loads(body)['id']
        _,body,_=self.request(a,'/api/state');state=json.loads(body);self.assertEqual(len(state['records']),2)
        task=next(r for r in state['records'] if r['kind']=='task');self.assertEqual(task['payload']['due'],'2026-11-13')
        status,draft_body,_=self.request(a,'/api/draft/'+rid+'?kind=preemption');self.assertEqual(status,200);self.assertIn('공유자 우선매수신고서',draft_body.decode())
        self.assertEqual(self.request(b,'/api/draft/'+rid+'?kind=preemption')[0],404)
        _,body,_=self.request(b,'/api/state');self.assertEqual(json.loads(body)['records'],[])
        self.assertEqual(self.request(b,'/api/record',{**p,'id':rid,'version':1},other)[0],404)
        self.assertEqual(self.request(a,'/api/record',p,'invalid')[0],403)
        _,body,_=self.request(a,'/api/upload/'+rid,csrf=csrf,raw=b'bank proof',headers={'X-File-Name':'proof.txt'});eid=json.loads(body)['id']
        self.assertEqual(self.request(b,'/api/evidence/'+eid)[0],404)
        complete={'kind':'case','id':rid,'version':1,'payload':{'title':'Test case','stage':'전액회수','completion_evidence':eid}}
        self.assertEqual(self.request(a,'/api/record',complete,csrf)[0],200)
        self.assertEqual(self.request(a,'/api/record',complete,csrf)[0],409)
        status,body,h=self.request(a,'/api/export');self.assertEqual(status,200);self.assertTrue(body.startswith(b'PK'))
    def test_events_generate_tasks_and_completion_requires_evidence(self):
        c,csrf=self.user('event-owner')
        p={'kind':'event','payload':{'title':'Unknown issue','category':'미분류 변수','due':'2026-11-01'}}
        self.assertEqual(self.request(c,'/api/record',p,csrf)[0],200)
        _,body,_=self.request(c,'/api/state');tasks=[r for r in json.loads(body)['records'] if r['kind']=='task'];self.assertEqual(len(tasks),1)
        task=tasks[0];task['payload']['done']=True
        self.assertEqual(self.request(c,'/api/record',task,csrf)[0],400)
        self.assertEqual(self.request(c,'/api/record',{'kind':'case','payload':{'title':'Invalid','stage':'직접취득'}},csrf)[0],400)
    def test_security_and_logout(self):
        c,csrf=self.user('security-owner')
        self.assertEqual(self.request(c,'/api/record',{'kind':'task','payload':{'title':'x','due':'2026-11-01'}},csrf,headers={'Origin':'https://evil.example'})[0],403)
        self.assertEqual(self.request(c,'/api/logout',{},csrf)[0],200)
        self.assertEqual(self.request(c,'/api/state')[0],401)
        self.assertEqual(self.request(c,'/../../server.py')[0],404)
        _,_,headers=self.request(c,'/');self.assertIn("frame-ancestors 'none'",headers['Content-Security-Policy'])
    def test_paper_filing_lifecycle(self):
        from paperwork import COMMON,EXTRA,CHECKS
        c,csrf=self.user('paper-owner');other,other_csrf=self.user('paper-other')
        _,body,_=self.request(c,'/api/record',{'kind':'asset','payload':{'title':'Mortgage','ownership':'근저당'}},csrf);aid=json.loads(body)['id']
        _,body,_=self.request(c,'/api/record',{'kind':'case','payload':{'title':'Paper case','stage':'집행준비','type':'share','asset_id':aid}},csrf);cid=json.loads(body)['id']
        data={k:'가상 입력' for k,_ in COMMON+EXTRA['petition']};data.update(signed_date='2026-10-01',amount='1000000')
        _,body,_=self.request(c,'/api/filing',{'action':'save','case_id':cid,'form_kind':'petition','data':data},csrf);fid=json.loads(body)['id']
        self.assertEqual(self.request(other,'/api/print/'+fid)[0],404)
        self.assertEqual(self.request(c,'/api/filing',{'action':'approve','id':fid,'version':1,'checks':{}},csrf)[0],400)
        self.assertEqual(self.request(c,'/api/filing',{'action':'approve','id':fid,'version':1,'checks':{k:True for k in CHECKS}},csrf)[0],200)
        self.assertEqual(self.request(c,'/api/filing',{'action':'save','id':fid,'version':2,'case_id':cid,'form_kind':'petition','data':data},csrf)[0],400)
        status,body,_=self.request(c,'/api/print/'+fid);self.assertEqual(status,200);self.assertIn('별지 부동산 목록',body.decode())
        self.assertEqual(self.request(c,'/api/filing',{'action':'printed','id':fid,'version':2,'confirmed':True},csrf)[0],200)
        receipt={'date':'2026-10-01','number':'접수123','by':'가상 접수자','signed':True}
        self.assertEqual(self.request(c,'/api/filing',{'action':'submit','id':fid,'version':3,'receipt':receipt},csrf)[0],400)
        _,body,_=self.request(c,'/api/upload/'+cid,csrf=csrf,raw=b'receipt');receipt['evidence']=json.loads(body)['id'];receipt['case_number']='2026타경123'
        self.assertEqual(self.request(c,'/api/filing',{'action':'submit','id':fid,'version':3,'receipt':receipt},csrf)[0],200)
        _,body,_=self.request(c,'/api/state');state=json.loads(body);case=next(x for x in state['records'] if x['id']==cid)
        self.assertEqual(case['payload']['stage'],'경매접수');self.assertEqual(case['payload']['number'],'2026타경123')
        self.assertTrue(any(x['kind']=='task' and '접수 후' in x['payload']['title'] for x in state['records']))

if __name__=='__main__': unittest.main()
