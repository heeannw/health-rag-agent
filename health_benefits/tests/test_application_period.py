import unittest
from datetime import date
from xml.etree import ElementTree as ET
from health_benefits.preprocessing.application_period import extract_period

class PeriodTest(unittest.TestCase):
    def parse(self, text):
        root=ET.Element('detail');ET.SubElement(root,'alwServCn').text=text
        return extract_period(root)
    def test_explicit(self):
        start,end,_=self.parse('(신청기간) 2026년 1월 2일 ~ 2026년 1월 30일\n카드 발급신청 기간 내 발급')
        self.assertEqual((start,end),(date(2026,1,2),date(2026,1,30)))
    def test_ambiguous(self):
        for text in ['사용기간: 2026.1.1 ~ 2026.12.31', '신청기간: 출산일로부터 1년', '신청기간: 1.1 ~ 12.31', '신청기간: 2026.2.30 ~ 2026.3.1', '신청기간: 2026.1.1 ~ 2026.12.31 예산 소진 시', '신청기간: 2026.12.1 ~ 2026.1.1']:
            self.assertEqual(self.parse(text)[:2],(None,None))
    def test_multiple(self):
        self.assertEqual(self.parse('신청기간: 2026.1.1 ~ 2026.1.2\n접수기간: 2026.2.1 ~ 2026.2.2')[:2],(None,None))

if __name__=='__main__':unittest.main()
