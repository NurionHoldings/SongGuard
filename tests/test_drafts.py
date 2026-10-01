import unittest
from drafts import draft

class Drafts(unittest.TestCase):
    def test_missing_facts_are_explicit(self):
        for kind in ('petition','statement','preemption','special'):
            text=draft(kind,{}, {}, {})
            self.assertIn('확인',text)
            self.assertIn('자동 접수되지 않음',text)
    def test_calculation_and_parties(self):
        c={'principal':1000000,'rate':10,'start':'2025-01-01','as_of':'2026-01-01','cap':1200000,'creditor':'가상 채권자','debtor':'가상 채무자'}
        text=draft('statement',{'number':'2026타경00000'},c,{})
        self.assertIn('1,100,000원',text);self.assertIn('가상 채권자',text)
    def test_special_payment_not_total_claim_offset(self):
        text=draft('special',{}, {}, {})
        self.assertIn('채권총액과 구분',text);self.assertIn('이의',text)
    def test_invalid_kind(self):
        with self.assertRaises(ValueError): draft('invalid',{}, {}, {})
