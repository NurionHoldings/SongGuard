import unittest
from core import ledger, scenario, preemption

class Calculations(unittest.TestCase):
    def test_interest_and_payment_allocation(self):
        c={'principal':1000000,'rate':10,'start':'2025-01-01','as_of':'2026-01-01','cap':1200000,'costs':10000,'payments':[{'date':'2026-01-01','amount':210000}]}
        r=ledger(c)
        self.assertEqual(r['principal'],900000); self.assertEqual(r['interest'],0); self.assertEqual(r['costs'],0)
    def test_interest_after_partial_payment(self):
        r=ledger({'principal':365000,'rate':10,'start':'2026-01-01','as_of':'2026-01-21','payments':[{'date':'2026-01-11','amount':101000}]})
        self.assertEqual(r['principal'],265000); self.assertEqual(r['interest'],726)
    def test_negative_and_invalid_period(self):
        for p in (-1,'NaN','Infinity'):
            with self.assertRaises(ValueError): ledger({'principal':p,'start':'2026-01-01','as_of':'2026-01-02'})
        with self.assertRaises(ValueError): ledger({'principal':1,'start':'2026-02-01','as_of':'2026-01-01'})
    def test_overpayment_requires_review(self):
        with self.assertRaises(ValueError): ledger({'principal':1,'start':'2026-01-01','as_of':'2026-01-01','payments':[{'date':'2026-01-01','amount':2}]})
    def test_dividend_caps_and_cash(self):
        r=scenario({'price':1000,'priority':100,'execution':100,'claim':900,'cap':700,'deposit':100,'taxes':50,'resale':1200})
        self.assertEqual(r['dividend'],700); self.assertEqual(r['shortfall'],200)
        self.assertEqual(r['remaining_special'],200); self.assertEqual(r['cash_with_special_payment'],350)
        self.assertEqual(r['economic_recovery'],850)
    def test_no_surplus(self):
        self.assertEqual(scenario({'price':10,'priority':20,'claim':100,'cap':100})['dividend'],0)
    def test_preemption_requires_verified_share(self):
        for kind in ('whole','partition','bundle'):
            self.assertEqual(preemption({'type':kind,'coowner_verified':True,'other_share_verified':True})['status'],'review')
        self.assertEqual(preemption({'type':'share'})['status'],'review')
        self.assertEqual(preemption({'type':'share','coowner_verified':True,'other_share_verified':True})['status'],'candidate')

if __name__=='__main__': unittest.main()
