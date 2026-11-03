"""명시적인 단일 신청/접수 기간만 추출합니다. 사업 시행일은 사용하지 않습니다."""
import html
import re
from datetime import date

DATE = r'(20\d{2})\s*[년./-]\s*(\d{1,2})\s*[월./-]\s*(\d{1,2})\s*일?'


def extract_period(root):
    candidates = []
    for tag in ('aplyMtdCn', 'alwServCn', 'slctCritCn'):
        for node in root.findall('.//' + tag):
            text = html.unescape(''.join(node.itertext()))
            text = re.sub(r'<br\s*/?>', '\n', text, flags=re.I)
            for line in re.split(r'[\r\n]+', text):
                if re.search(r'(?<![가-힣])(신청|접수)\s*기간\s*[:：)]', line):
                    candidates.append(line.strip())
    evidence = '\n'.join(dict.fromkeys(candidates)) or None
    # 여러 차수/대상별 일정, 상대 날짜, 연도 없는 일정은 자동 판정하지 않습니다.
    if len(set(candidates)) != 1:
        return None, None, evidence
    line = candidates[0]
    if any(x in line for x in ('소진', '선착순', '별도', '차수')):
        return None, None, evidence
    dates = re.findall(DATE, line)
    if len(dates) != 2 or not re.search(r'[~∼～]|부터', line):
        return None, None, evidence
    try:
        start, end = [date(*map(int, parts)) for parts in dates]
    except ValueError:
        return None, None, evidence
    if start > end:
        return None, None, evidence
    return start, end, evidence
