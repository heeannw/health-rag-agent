"""원문 관심주제로 클라우드 benefit에서 의료 관련 항목을 별도 복사합니다."""
import json
import os
from collections import Counter
from datetime import datetime, timezone

import psycopg
from psycopg import sql
from dotenv import load_dotenv

from health_benefits.collection.collect_many import BASE, parse_xml, text_of

THEMES = {"010": "신체건강", "020": "정신건강", "080": "임신·출산"}
EXCLUDED = {"collected_at", "detail_collected_at"}


def load_themes():
    """가장 최근 목록을 사용합니다. 여러 분류는 OR 조건으로 판단합니다."""
    records = {}
    paths = list((BASE / "data" / "batches").glob("*/list_*.xml"))
    sample = BASE / "data" / "welfare_list.xml"
    if sample.exists():
        paths.append(sample)
    for path in sorted(paths, key=lambda p: (p.stat().st_mtime_ns, str(p))):
        root = parse_xml(path.read_bytes())
        for service in root.findall(".//servList"):
            # 지자체 목록은 지역 필드를 제공하며, 중앙 목록은 소관부처를 제공합니다.
            if service.find("ctpvNm") is not None:
                source, tag = "local", "intrsThemaNmArray"
            elif service.find("jurMnofNm") is not None:
                source, tag = "central", "intrsThemaArray"
            else:
                raise ValueError(f"목록 출처 확인 불가: {path.name}")
            sid = text_of(service, "servId")
            if not sid:
                raise ValueError(f"목록 ID 누락: {path.name}")
            themes = {v.strip() for v in (text_of(service, tag) or "").split(",") if v.strip()}
            records[source, sid] = {
                "name": text_of(service, "servNm"),
                "themes": themes,
                "path": str(path.relative_to(BASE)),
            }
    return records


def main():
    records = load_themes()
    load_dotenv(BASE / ".env", override=True)
    host = os.environ["PGHOST"]
    if not host.endswith(".supabase.com"):
        raise ValueError("설정된 Supabase 클라우드 호스트인지 확인이 필요합니다.")
    report = {"table": "public.healty_benefit", "themes": THEMES,
              "excluded_columns": sorted(EXCLUDED), "host": host}
    with psycopg.connect(
        host=host, port=os.environ["PGPORT"], dbname=os.environ["PGDATABASE"],
        user=os.environ["PGUSER"], password=os.environ["PGPASSWORD"],
        sslmode="require", connect_timeout=15,
    ) as conn:
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        conn.execute("SET LOCAL lock_timeout = '10s'")
        if conn.execute("SELECT to_regclass('public.healty_benefit')").fetchone()[0]:
            raise ValueError("healty_benefit가 이미 존재합니다. 기존 테이블은 덮어쓰지 않습니다.")
        columns = [r[0] for r in conn.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema='public' AND table_name='benefit' ORDER BY ordinal_position
        """)]
        if not EXCLUDED.issubset(columns):
            raise ValueError("benefit 스키마 확인 필요")
        kept = [c for c in columns if c not in EXCLUDED]
        rows = conn.execute("SELECT id,source,source_service_id,name FROM public.benefit").fetchall()
        selected, evidence, missing, empty, mismatched = [], [], [], [], []
        for bid, source, sid, name in rows:
            record = records.get((source, sid))
            if record is None:
                missing.append([source, sid])
                continue
            if record["name"] != name:
                mismatched.append([source, sid])
                continue
            if not record["themes"]:
                empty.append([source, sid])
            codes = [code for code, label in THEMES.items() if label in record["themes"]]
            if codes:
                selected.append(bid)
                evidence.append({"id": bid, "source": source, "source_service_id": sid,
                                 "name": name, "codes": codes, "xml": record["path"]})
        if missing or mismatched:
            raise ValueError(f"원문 대조 실패: 목록 없음 {len(missing)}, 이름 불일치 {len(mismatched)}")
        if not selected:
            raise ValueError("선택된 서비스가 없습니다.")
        conn.execute("CREATE TABLE public.healty_benefit (LIKE public.benefit INCLUDING ALL)")
        for column in sorted(EXCLUDED):
            conn.execute(sql.SQL("ALTER TABLE public.healty_benefit DROP COLUMN {}").format(sql.Identifier(column)))
        names = sql.SQL(",").join(map(sql.Identifier, kept))
        conn.execute(sql.SQL("""
            INSERT INTO public.healty_benefit ({0}) OVERRIDING SYSTEM VALUE
            SELECT {0} FROM public.benefit WHERE id = ANY(%s)
        """).format(names), (selected,))
        conn.execute("""
            SELECT setval(pg_get_serial_sequence('public.healty_benefit','id'),
                          (SELECT max(id) FROM public.healty_benefit), true)
        """)
        # 새로운 테이블이 API를 통해 공개되지 않도록 기존 테이블의 RLS 여부를 따릅니다.
        rls = conn.execute("""
            SELECT relrowsecurity FROM pg_class WHERE oid='public.benefit'::regclass
        """).fetchone()[0]
        if rls:
            conn.execute("ALTER TABLE public.healty_benefit ENABLE ROW LEVEL SECURITY")
        difference = conn.execute(sql.SQL("""
            SELECT count(*) FROM (
                (SELECT {0} FROM public.benefit WHERE id=ANY(%s)
                 EXCEPT SELECT {0} FROM public.healty_benefit)
                UNION ALL
                (SELECT {0} FROM public.healty_benefit
                 EXCEPT SELECT {0} FROM public.benefit WHERE id=ANY(%s))
            ) d
        """).format(names), (selected, selected)).fetchone()[0]
        count = conn.execute("SELECT count(*) FROM public.healty_benefit").fetchone()[0]
        if difference or count != len(selected):
            raise ValueError("복사 결과 대조 실패")
        report.update(
            original_count=len(rows), copied_count=count, columns=kept,
            sources=dict(Counter(e["source"] for e in evidence)),
            theme_counts=dict(Counter(code for e in evidence for code in e["codes"])),
            no_theme_count=len(empty), no_theme_services=empty,
            difference_count=difference, rls_enabled=rls, evidence=evidence,
        )
        folder = BASE / "data" / "exports"
        folder.mkdir(parents=True, exist_ok=True)
        output = folder / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "_healty_benefit.json")
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in ("evidence", "no_theme_services")},
                     ensure_ascii=False, indent=2))
    print(f"추출 근거: {output}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # 연결 오류에 인증정보가 포함될 수 있으므로 일반 예외 원문은 출력하지 않습니다.
        print(str(exc) if isinstance(exc, ValueError) else f"작업 실패: {type(exc).__name__}")
        raise SystemExit(1) from None
