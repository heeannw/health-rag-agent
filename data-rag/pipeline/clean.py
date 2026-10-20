import html
import re

_WHITESPACE_RE = re.compile(r"[ \t\xa0]+")
_BLANK_LINES_RE = re.compile(r"\n{3,}")


def clean_text(raw: str) -> str:
    """API 응답 텍스트 정제: HTML 엔티티/개행 정규화, 중복 공백 제거."""
    if not raw:
        return ""

    text = html.unescape(raw)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _WHITESPACE_RE.sub(" ", text)
    text = _BLANK_LINES_RE.sub("\n\n", text)
    return text.strip()


def join_sections(sections: dict) -> str:
    """{섹션제목: 내용} 딕셔너리를 "## 제목\n내용" 형태로 이어붙인다. 빈 내용은 제외."""
    parts = []
    for title, content in sections.items():
        cleaned = clean_text(content)
        if cleaned:
            parts.append(f"## {title}\n{cleaned}")
    return "\n\n".join(parts)
