"""임시 테이블에서 실제 PostgreSQL upsert를 검사합니다. 운영 행은 변경하지 않습니다."""
import os
from datetime import datetime, timedelta, timezone
import psycopg
from dotenv import load_dotenv
from collect_many import BASE, parse_xml
from benefit_store import save_listing, save_detail


def main():
    load_dotenv(BASE / '.env', override=True)
    with psycopg.connect(host=os.environ['PGHOST'], port=os.environ['PGPORT'],
                         dbname=os.environ['PGDATABASE'], user=os.environ['PGUSER'],
                         password=os.environ['PGPASSWORD'], connect_timeout=10) as conn:
        conn.execute((BASE / 'benefit_schema.sql').read_text(encoding='utf-8').replace(
            'CREATE TABLE benefit', 'CREATE TEMP TABLE benefit'))
        listing = parse_xml('<servList><servId>TEST</servId><servNm>혜택</servNm><servDgst>요약</servDgst><ctpvNm>서울</ctpvNm></servList>')
        detail = parse_xml('<detail><servId>TEST</servId><servNm>혜택</servNm><sprtTrgtCn>지역 대상</sprtTrgtCn><tgtrDtlCn>중앙 대상</tgtrDtlCn><slctCritCn>기준</slctCritCn><alwServCn>금액</alwServCn></detail>')
        t = datetime.now(timezone.utc)
        save_listing(conn, 'local', listing, t)
        assert conn.execute('SELECT detail_collected_at FROM benefit').fetchone()[0] is None
        save_detail(conn, 'local', detail, t)
        before = conn.execute('SELECT id,target_text,criteria_text,benefit_text,detail_collected_at FROM benefit').fetchone()
        assert before[1:4] == ('지역 대상','기준','금액')
        save_listing(conn, 'local', listing, t + timedelta(seconds=1))
        assert conn.execute('SELECT id,target_text,criteria_text,benefit_text,detail_collected_at FROM benefit').fetchone() == before
        assert save_detail(conn, 'local', detail, t - timedelta(days=1)) is None
        save_detail(conn, 'central', detail, t)
        assert conn.execute("SELECT target_text FROM benefit WHERE source='central'").fetchone()[0] == '중앙 대상'
        assert conn.execute('SELECT count(*) FROM benefit').fetchone()[0] == 2
        assert conn.execute("SELECT summary_text FROM benefit WHERE source='local'").fetchone()[0] == '요약'
        conn.rollback()
    print('PASS: 목록→상세 병합, 상세 보존, 출처 분리, 오래된 상세 차단, ID 유지')


if __name__ == '__main__':
    main()
