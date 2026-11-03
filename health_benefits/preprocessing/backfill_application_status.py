"""저장한 상세 XML과 DB 내용을 대조하여 명시적인 신청 기간을 보충합니다."""
import json
import os
from datetime import datetime, timezone
import psycopg
from dotenv import load_dotenv
from health_benefits.collection.collect_many import BASE, parse_xml, text_of
from health_benefits.preprocessing.application_period import extract_period


def norm(v):
    return v.replace('\r\n','\n').replace('\r','\n') if v else v


def main():
    archive = {}
    for path in (BASE / 'data' / 'batches').glob('*/detail*.xml'):
        try:
            root = parse_xml(path.read_bytes())
        except Exception:
            continue
        source = 'local' if root.find('.//enfcBgngYmd') is not None else 'central'
        key = (source, text_of(root,'servId'), norm(text_of(root,'servNm')),
               norm(text_of(root,'sprtTrgtCn' if source == 'local' else 'tgtrDtlCn')),
               norm(text_of(root,'slctCritCn')), norm(text_of(root,'alwServCn')))
        archive[key] = extract_period(root)
    load_dotenv(BASE / '.env', override=True)
    with psycopg.connect(host=os.environ['PGHOST'],port=os.environ['PGPORT'],
                         dbname=os.environ['PGDATABASE'],user=os.environ['PGUSER'],
                         password=os.environ['PGPASSWORD'],connect_timeout=10) as conn:
        conn.execute("SET LOCAL lock_timeout = '10s'")
        conn.execute('LOCK TABLE benefit IN ACCESS EXCLUSIVE MODE')
        snapshot = [r[0] for r in conn.execute('SELECT row_to_json(b) FROM benefit b')]
        folder = BASE / 'data' / 'backups' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ_status')
        folder.mkdir(parents=True)
        (folder / 'benefit.json').write_text(json.dumps(snapshot,ensure_ascii=False),encoding='utf-8')
        conn.execute((BASE / 'database/sql/application_status.sql').read_text(encoding='utf-8'))
        matched = 0
        for row in conn.execute('SELECT id,source,source_service_id,name,target_text,criteria_text,benefit_text FROM benefit WHERE detail_collected_at IS NOT NULL').fetchall():
            key = tuple(norm(v) for v in row[1:])
            if key not in archive:
                continue
            start,end,evidence = archive[key]
            conn.execute('UPDATE benefit SET application_start_date=%s,application_deadline=%s,application_period_text=%s WHERE id=%s',(start,end,evidence,row[0]))
            matched += 1
        conn.execute('SELECT refresh_benefit_application_status()')
        after = [r[0] for r in conn.execute('SELECT row_to_json(b) FROM benefit b')]
        original = {r['id']:r for r in snapshot}
        for row in after:
            old = original[row['id']]
            for key in old:
                if key not in ('application_start_date','application_deadline','application_status','application_period_text','status_checked_at'):
                    assert row[key] == old[key], (row['id'],key)
        assert len(after) == len(snapshot)
        counts = conn.execute('SELECT application_status,count(*) FROM benefit GROUP BY 1 ORDER BY 1').fetchall()
        examples = conn.execute("SELECT name,application_start_date,application_deadline,application_status FROM benefit WHERE application_deadline IS NOT NULL").fetchall()
    print(json.dumps({'matched_details':matched,'status_counts':counts,'examples':examples,'backup':str(folder)},ensure_ascii=False,default=str,indent=2))


if __name__ == '__main__':
    main()
