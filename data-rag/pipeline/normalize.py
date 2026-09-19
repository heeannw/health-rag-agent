"""API별 원시 응답(dict)을 공통 Document 스키마로 변환한다.

Document = {
    "id": str,            # 소스 내 고유 ID
    "source": str,        # 데이터 출처 구분자 (예: "welfare_central")
    "title": str,         # 청크/검색 결과에 표시할 제목
    "text": str,          # 임베딩 대상 본문 (정제 + 섹션 결합 완료)
    "metadata": dict,     # 답변 근거 표시용 출처 메타데이터
}
"""

from pipeline.clean import clean_text, join_sections


def normalize_welfare_central_detail(detail: dict) -> dict:
    d = detail["wantedDtl"]
    text = join_sections(
        {
            "서비스 개요": d.get("wlfareInfoOutlCn", ""),
            "지원 대상": d.get("tgtrDtlCn", ""),
            "선정 기준": d.get("slctCritCn", ""),
            "서비스 내용": d.get("alwServCn", ""),
        }
    )
    return {
        "id": d["servId"],
        "source": "welfare_central",
        "title": d.get("servNm", ""),
        "text": text,
        "metadata": {
            "소관부처": d.get("jurMnofNm"),
            "지원주기": d.get("sprtCycNm"),
            "제공방식": d.get("srvPvsnNm"),
            "생애주기": d.get("lifeArray"),
            "대상특성": d.get("trgterIndvdlArray"),
            "관심주제": d.get("intrsThemaArray"),
            "기준연도": d.get("crtrYr"),
            "문의처": d.get("rprsCtadr"),
        },
    }


def normalize_welfare_local_detail(detail: dict) -> dict:
    d = detail["wantedDtl"]
    text = join_sections(
        {
            "서비스 개요": d.get("servDgst", ""),
            "지원 대상": d.get("sprtTrgtCn", ""),
            "선정 기준": d.get("slctCritCn", ""),
            "서비스 내용": d.get("alwServCn", ""),
            "신청 방법": d.get("aplyMtdCn", ""),
        }
    )
    region = " ".join(filter(None, [d.get("ctpvNm"), d.get("sggNm")]))
    return {
        "id": d["servId"],
        "source": "welfare_local",
        "title": d.get("servNm", ""),
        "text": text,
        "metadata": {
            "지역": region,
            "담당부서": d.get("bizChrDeptNm"),
            "생애주기": d.get("lifeNmArray"),
            "대상특성": d.get("trgterIndvdlNmArray"),
            "관심주제": d.get("intrsThemaNmArray"),
            "지원방식": d.get("aplyMtdNm"),
        },
    }


def normalize_law_item(item: dict) -> dict:
    """법제처 법령정보 목록 항목. 조문 원문은 미포함(목록조회 API 한계) — 메타데이터 중심."""
    title = item.get("법령명한글", "")
    text = clean_text(
        f"{title}은(는) {item.get('소관부처명', '')}이(가) 소관하는 {item.get('법령구분명', '')}입니다. "
        f"공포일자 {item.get('공포일자', '')}, 시행일자 {item.get('시행일자', '')}, "
        f"제개정구분: {item.get('제개정구분명', '')}."
    )
    return {
        "id": item.get("법령ID", item.get("@id", "")),
        "source": "law",
        "title": title,
        "text": text,
        "metadata": {
            "소관부처": item.get("소관부처명"),
            "법령구분": item.get("법령구분명"),
            "공포일자": item.get("공포일자"),
            "시행일자": item.get("시행일자"),
            "상세링크": item.get("법령상세링크"),
        },
    }


def normalize_hospital_item(item: dict) -> dict:
    grades = {k: v for k, v in item.items() if k.startswith("asmGrd")}
    grade_text = ", ".join(f"{k}: {v}" for k, v in grades.items())
    text = clean_text(f"{item.get('yadmNm', '')} ({item.get('clCdNm', '')}) 평가등급 - {grade_text}")
    return {
        "id": item.get("ykiho", item.get("yadmNm", "")),
        "source": "hospital",
        "title": item.get("yadmNm", ""),
        "text": text,
        "metadata": {
            "주소": item.get("addr"),
            "종별": item.get("clCdNm"),
            **grades,
        },
    }


def normalize_dementia_center_item(item: dict) -> dict:
    text = join_sections(
        {
            "개요": f"{item.get('cnterNm', '')} ({item.get('cnterSe', '')})",
            "주요 프로그램": item.get("imbcltyIntrcn", ""),
        }
    )
    return {
        "id": item.get("cnterNm", ""),
        "source": "dementia_center",
        "title": item.get("cnterNm", ""),
        "text": text,
        "metadata": {
            "주소": item.get("rdnmadr") or item.get("lnmadr"),
            "운영기관": item.get("operInstitutionNm"),
            "전화번호": item.get("phoneNumber"),
            "의사인원수": item.get("doctrCo"),
            "간호사인원수": item.get("nurseCo"),
        },
    }


def normalize_ltc_institution_item(item: dict) -> dict:
    text = clean_text(f"{item.get('adminNm', '')} 관할 청구그린기관 정보")
    return {
        "id": f"{item.get('adminNm', '')}-{item.get('BDongCd', '')}",
        "source": "ltc_institution",
        "title": item.get("adminNm", ""),
        "text": text,
        "metadata": {k: v for k, v in item.items()},
    }
