"""목록과 상세를 단일 benefit 테이블에 저장하는 공통 함수."""
from datetime import datetime, timezone
from health_benefits.preprocessing.application_period import extract_period


def text_of(root, tag):
    node = root.find(f".//{tag}")
    return ("".join(node.itertext()).strip() or None) if node is not None else None


def save_listing(conn, source, service, collected_at=None):
    sid, name = text_of(service, "servId"), text_of(service, "servNm")
    if not sid or not name:
        raise ValueError("목록 ID/이름 누락")
    conn.execute("""
        INSERT INTO benefit (source, source_service_id, name, summary_text,
            source_url, provider_province, provider_municipality, collected_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (source, source_service_id) DO UPDATE SET
            name=EXCLUDED.name, summary_text=EXCLUDED.summary_text,
            source_url=COALESCE(EXCLUDED.source_url, benefit.source_url),
            provider_province=EXCLUDED.provider_province,
            provider_municipality=EXCLUDED.provider_municipality,
            collected_at=GREATEST(benefit.collected_at, EXCLUDED.collected_at)
    """, (source, sid, name, text_of(service, "servDgst"),
          text_of(service, "servDtlLink"), text_of(service, "ctpvNm"),
          text_of(service, "sggNm"), collected_at or datetime.now(timezone.utc)))


def save_detail(conn, source, detail, collected_at=None):
    sid, name = text_of(detail, "servId"), text_of(detail, "servNm")
    if not sid or not name:
        raise ValueError("상세 ID/이름 누락")
    stamp = collected_at or datetime.now(timezone.utc)
    start, end, evidence = extract_period(detail)
    result = conn.execute("""
        INSERT INTO benefit (source, source_service_id, name, target_text,
            criteria_text, benefit_text, collected_at, detail_collected_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (source, source_service_id) DO UPDATE SET
            name=EXCLUDED.name, target_text=EXCLUDED.target_text,
            criteria_text=EXCLUDED.criteria_text, benefit_text=EXCLUDED.benefit_text,
            collected_at=GREATEST(benefit.collected_at, EXCLUDED.collected_at),
            detail_collected_at=EXCLUDED.detail_collected_at
        WHERE benefit.detail_collected_at IS NULL
           OR benefit.detail_collected_at <= EXCLUDED.detail_collected_at
        RETURNING id, name
    """, (source, sid, name, text_of(detail, "sprtTrgtCn" if source == "local" else "tgtrDtlCn"),
          text_of(detail, "slctCritCn"), text_of(detail, "alwServCn"), stamp, stamp)).fetchone()
    if result:
        conn.execute("""UPDATE benefit SET application_start_date=%s, application_deadline=%s,
            application_period_text=%s WHERE id=%s""", (start, end, evidence, result[0]))
        conn.execute("SELECT refresh_benefit_application_status()")
    return result
