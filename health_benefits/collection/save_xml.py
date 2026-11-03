"""중앙부처 XML 파일을 benefit에 저장하며 더 최근 상세를 보호합니다."""
import os
from datetime import datetime, timezone
import psycopg
from dotenv import load_dotenv
from health_benefits.collection.collect_many import BASE, parse_xml, text_of
from health_benefits.database.benefit_store import save_listing, save_detail


def main():
    load_dotenv(BASE / '.env', override=True)
    path = BASE / 'data' / 'welfare_detail.xml'
    listing_path = BASE / 'data' / 'welfare_list.xml'
    detail = parse_xml(path.read_bytes())
    sid = text_of(detail, 'servId')
    stamp = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
    with psycopg.connect(host=os.environ['PGHOST'], port=os.environ['PGPORT'],
                         dbname=os.environ['PGDATABASE'], user=os.environ['PGUSER'],
                         password=os.environ['PGPASSWORD'], connect_timeout=10) as conn:
        current = conn.execute("SELECT detail_collected_at FROM benefit WHERE source='central' AND source_service_id=%s", (sid,)).fetchone()
        if current and current[0] and current[0] > stamp:
            print('DB 상세가 더 최신이므로 오래된 XML을 건너뜁니다.')
            return
        if listing_path.exists():
            for service in parse_xml(listing_path.read_bytes()).findall('.//servList'):
                if text_of(service, 'servId') == sid:
                    save_listing(conn, 'central', service, datetime.fromtimestamp(listing_path.stat().st_mtime, timezone.utc))
                    break
        result = save_detail(conn, 'central', detail, stamp)
    print('저장 완료:', result)


if __name__ == '__main__':
    main()
