"""최초 추출 XML에서 생애주기·대상특성을 클라우드 의료 혜택에 보충."""
import json
import os
from datetime import datetime, timezone

import psycopg
from dotenv import load_dotenv

from health_benefits.preprocessing.create_healty_benefit import BASE, THEMES, parse_xml, text_of


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
        tags = ("lifeNmArray", "trgterIndvdlNmArray") if item["source"] == "local" else ("lifeArray", "trgterIndvdlArray")
        values = []
        for field in tags:
            labels = list(dict.fromkeys(v.strip() for v in (text_of(service, field) or "").split(",") if v.strip()))
            values.append(labels or None)
        expected[key] = (item["id"], item["name"], *values)

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
        folder = BASE / "data/backups" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ_audience")
        folder.mkdir(parents=True)
        (folder / "healty_benefit.json").write_text(
            json.dumps(before, ensure_ascii=False, indent=2), encoding="utf-8")
        conn.execute("ALTER TABLE public.healty_benefit ADD COLUMN IF NOT EXISTS life_cycle_names TEXT[]")
        conn.execute("ALTER TABLE public.healty_benefit ADD COLUMN IF NOT EXISTS target_group_names TEXT[]")
        with conn.cursor() as cur:
            cur.executemany(
                "UPDATE public.healty_benefit SET life_cycle_names=%s,target_group_names=%s WHERE source=%s AND source_service_id=%s",
                [(value[2], value[3], *key) for key, value in expected.items()])
        for column in ("life_cycle_names", "target_group_names"):
            conn.execute(f"CREATE INDEX IF NOT EXISTS healty_benefit_{column}_gin ON public.healty_benefit USING gin({column})")
        after = [r[0] for r in conn.execute("SELECT row_to_json(b) FROM public.healty_benefit b ORDER BY id")]
        if len(after) != len(before):
            raise ValueError("변경 후 건수 불일치")
        for old, new in zip(before, after):
            values = (new.pop("life_cycle_names"), new.pop("target_group_names"))
            if values != expected[old["source"], old["source_service_id"]][2:]:
                raise ValueError("저장된 분류 불일치")
            if new != {k: v for k, v in old.items() if k not in ("life_cycle_names", "target_group_names")}:
                raise ValueError("기존 컬럼 변경 감지")
        counts = conn.execute("SELECT source,count(*),count(life_cycle_names),count(target_group_names) FROM public.healty_benefit GROUP BY source ORDER BY source").fetchall()
        missing = [{"source": key[0], "source_service_id": key[1], "id": value[0], "name": value[1],
                    "missing_fields": [field for field, data in zip(("life_cycle_names", "target_group_names"), value[2:]) if data is None]}
                   for key, value in expected.items() if None in value[2:]]
        report_path = BASE / "data/exports" / (folder.name + "_missing.json")
        report_path.write_text(json.dumps(missing, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"updated": len(after), "counts_source_total_life_target": counts,
                      "existing_columns_unchanged": True, "backup": str(folder), "missing_report": str(report_path)}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(str(exc) if isinstance(exc, ValueError) else f"작업 실패: {type(exc).__name__}")
        raise SystemExit(1) from None
