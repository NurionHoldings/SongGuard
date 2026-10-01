import unittest
from paperwork import schemas, missing, html, EXTRA, COMMON

class Paperwork(unittest.TestCase):
    def data(self,kind):
        d={k:'가상 검증 자료' for k,_ in COMMON+EXTRA[kind]}
        d.update(signed_date='2026-10-01',amount='1000000',price='2000000',dividend='1000000')
        return d
    def test_seven_complete_forms(self):
        self.assertEqual(len(schemas()),7)
        for kind in schemas():
            d=self.data(kind);self.assertEqual(missing(kind,d),[])
            rendered=html({'id':'test','status':'출력준비','form_kind':kind,'data':d})
            self.assertIn(schemas()[kind]['title'],rendered)
            self.assertIn('서명 또는 인',rendered)
            self.assertNotIn('id="print" disabled',rendered)
    def test_incomplete_forms_not_ready(self):
        for kind in schemas(): self.assertTrue(missing(kind,{}))
        rendered=html({'id':'test','status':'작성중','form_kind':'special','data':{'price':'abc'}})
        self.assertIn('id="print" disabled',rendered)
    def test_html_escapes_user_text(self):
        d=self.data('petition');d['basis']='<script>alert(1)</script>'
        rendered=html({'id':'test','status':'출력준비','form_kind':'petition','data':d})
        self.assertIn('&lt;script&gt;',rendered);self.assertNotIn('<script>alert',rendered)
        self.assertIn('별지 부동산 목록',rendered)
    def test_special_payment_validation(self):
        d=self.data('special');d['dividend']='3000000';self.assertTrue(missing('special',d))
        for n in ('NaN','-1','1.5'):
            d['price']=n;self.assertTrue(missing('special',d))
