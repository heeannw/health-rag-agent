"""최초 추출 근거와 XML을 대조하여 클라우드 의료 혜택에 주제 코드를 보충."""
import json
import os
from datetime import datetime, timezone

import psycopg
from dotenv import load_dotenv

from create_healty_benefit import BASE, THEMES, parse_xml, text_of


def main():
    reports = list((BASE / "data/exports").glob("*_healty_benefit.json"))
    if len(reports) != 1:
        raise ValueError("최초 추출 보고서를 하나로 특정해야 합니다.")
    evidence = json.loads(reports[0].read_text(encoding="utf-8"))["evidence"]
    expected = {}
    for item in evidence:
        path = (BASE / item["xml"]).resolve()
        if not path.is_relative_to((BASE / "data").resolve()):
            raise ValueError("원문 경로 범위 오류")
        root = parse_xml(path.read_bytes())
        services = [s for s in root.findall(".//servList")
                    if text_of(s, "servId") == item["source_service_id"]]
        if len(services) != 1:
            raise ValueError("원문 서비스 식별 오류")
        service = services[0]
        tag = "intrsThemaNmArray" if item["source"] == "local" else "intrsThemaArray"
        labels = {v.strip() for v in (text_of(service, tag) or "").split(",")}
        codes = [code for code, label in THEMES.items() if label in labels]
        if not codes or codes != item["codes"] or text_of(service, "servNm") != item["name"]:
            raise ValueError("최초 추출 근거와 XML 불일치")
        key = (item["source"], item["source_service_id"])
        if key in expected:
            raise ValueError("중복 추출 근거")
        expected[key] = (item["id"], item["name"], codes)

    load_dotenv(BASE / ".env", override=True)
    if not os.environ["PGHOST"].endswith(".supabase.com"):
        raise ValueError("Supabase 클라우드 연결 설정 확인 필요")
    with psycopg.connect(
        host=os.environ["PGHOST"], port=os.environ["PGPORT"],
        dbname=os.environ["PGDATABASE"], user=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"], sslmode="require", connect_timeout=15,
    ) as conn:
        conn.execute("SET LOCAL lock_timeout='10s'")
        conn.execute("LOCK TABLE public.healty_benefit IN ACCESS EXCLUSIVE MODE")
        before = [r[0] for r in conn.execute("SELECT row_to_json(b) FROM public.healty_benefit b ORDER BY id")]
        if len(before) != len(expected):
            raise ValueError("DB 건수와 추출 근거 불일치")
        for row in before:
            value = expected.get((row["source"], row["source_service_id"]))
            if value is None or value[:2] != (row["id"], row["name"]):
                raise ValueError("DB 서비스와 추출 근거 불일치")
        folder = BASE / "data/backups" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ_themes")
        folder.mkdir(parents=True)
        (folder / "healty_benefit.json").write_text(
            json.dumps(before, ensure_ascii=False, indent=2), encoding="utf-8")
        conn.execute("ALTER TABLE public.healty_benefit ADD COLUMN IF NOT EXISTS theme_codes TEXT[]")
        with conn.cursor() as cur:
            cur.executemany(
                "UPDATE public.healty_benefit SET theme_codes=%s WHERE source=%s AND source_service_id=%s",
                [(value[2], *key) for key, value in expected.items()])
        conn.execute("ALTER TABLE public.healty_benefit ALTER COLUMN theme_codes SET NOT NULL")
        if not conn.execute("""
            SELECT 1 FROM pg_constraint WHERE conrelid='public.healty_benefit'::regclass
            AND conname='healty_benefit_theme_codes_check'
        """).fetchone():
            conn.execute("""
                ALTER TABLE public.healty_benefit ADD CONSTRAINT healty_benefit_theme_codes_check
                CHECK (cardinality(theme_codes)>0 AND array_ndims(theme_codes)=1
                    AND array_position(theme_codes,NULL) IS NULL
                    AND theme_codes <@ ARRAY['010','020','080']::text[])
            """)
        conn.execute("CREATE INDEX IF NOT EXISTS healty_benefit_theme_codes_gin ON public.healty_benefit USING gin(theme_codes)")
        after = [r[0] for r in conn.execute("SELECT row_to_json(b) FROM public.healty_benefit b ORDER BY id")]
        if len(after) != len(before):
            raise ValueError("변경 후 건수 불일치")
        for old, new in zip(before, after):
            codes = new.pop("theme_codes")
            if codes != expected[old["source"], old["source_service_id"]][2]:
                raise ValueError("저장된 코드 불일치")
            if new != {k: v for k, v in old.items() if k != "theme_codes"}:
                raise ValueError("기존 컬럼 변경 감지")
        counts = conn.execute("""
            SELECT code,count(*) FROM public.healty_benefit,
            unnest(theme_codes) AS code GROUP BY code ORDER BY code
        """).fetchall()
    print(json.dumps({"updated": len(after), "counts": counts,
                      "existing_columns_unchanged": True, "backup": str(folder)}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(str(exc) if isinstance(exc, ValueError) else f"작업 실패: {type(exc).__name__}")
        raise SystemExit(1) from None
