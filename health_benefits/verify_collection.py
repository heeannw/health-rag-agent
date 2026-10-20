"""단일 benefit의 구조, 중복, 출처별 상세 수집 현황을 읽기 전용으로 검증."""
import json
import os
import psycopg
from dotenv import load_dotenv
from collect_many import BASE

COLUMNS = ['id','source','source_service_id','name','target_text','summary_text',
           'criteria_text','source_url','provider_province','provider_municipality',
           'collected_at','benefit_text','detail_collected_at', 'application_start_date',
           'application_deadline','application_status','application_period_text','status_checked_at']


def main():
    load_dotenv(BASE / '.env', override=True)
    with psycopg.connect(host=os.environ['PGHOST'], port=os.environ['PGPORT'],
                         dbname=os.environ['PGDATABASE'], user=os.environ['PGUSER'],
                         password=os.environ['PGPASSWORD'], connect_timeout=10) as conn:
        conn.execute('SET TRANSACTION READ ONLY')
        columns = [r[0] for r in conn.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='benefit' ORDER BY ordinal_position")]
        if columns != COLUMNS:
            raise RuntimeError('컬럼 구조 불일치')
        duplicates = conn.execute('SELECT count(*) FROM (SELECT source,source_service_id FROM benefit GROUP BY 1,2 HAVING count(*)>1) d').fetchone()[0]
        if duplicates:
            raise RuntimeError('중복 서비스 발견')
        rows = conn.execute('SELECT source,count(*),count(detail_collected_at) FROM benefit GROUP BY source ORDER BY source').fetchall()
        tables = conn.execute("SELECT table_name,table_type FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name").fetchall()
        report = {'columns':columns,'tables':tables,'duplicate_count':duplicates,
                  'sources':{r[0]:{'total':r[1],'with_detail':r[2],'without_detail':r[1]-r[2]} for r in rows}}
    (BASE / 'data' / 'benefit_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
