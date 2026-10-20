# 단일 benefit 테이블

목록과 상세는 모두 public.benefit에 저장합니다. 기본키는 자동 생성 id,
중복 방지 키는 (source, source_service_id)입니다. source는 central/local입니다.

컬럼은 id, source, source_service_id, name, target_text, summary_text,
criteria_text, source_url, provider_province, provider_municipality,
collected_at, benefit_text, detail_collected_at 총 13개입니다.

collected_at은 목록 또는 상세를 마지막으로 수집한 시각,
detail_collected_at은 상세를 마지막으로 수집한 시각입니다.
상세 미수집 행의 detail_collected_at/target_text/criteria_text/benefit_text는 NULL입니다.
상세 수집 여부는 내용의 NULL 여부가 아니라 detail_collected_at으로 판단합니다.
provider 지역은 제공기관 지역이며 신청자 거주 요건과 동일하지 않습니다.

```powershell
python collect_catalog.py --source central
python collect_catalog.py --source local
python collect_many.py --source central --limit 0 --max-calls 1000 --refresh --skip-collected-today
python collect_many.py --source local --limit 0 --max-calls 1100 --refresh --skip-collected-today
python verify_collection.py
```

collect_catalog.py는 목록 컬럼만 갱신합니다. 상세 내용과 상세 수집 시각은 유지합니다.
collect_many.py는 benefit_store.py의 공통 함수를 통해 목록/상세를 한 행에 저장합니다.
기존 행이 있어도 상세 수집 전이면 건너뛰지 않습니다. 오늘 수집한 상세만 생략할 수 있습니다.
API 한도 오류가 나오면 중단하며 원본 XML은 data/batches에 보존합니다.
DB에는 XML 컬럼이 없습니다. save_xml.py는 파일 시각을 사용하며 더 최신 DB 상세는 덮어쓰지 않습니다.

```sql
SELECT name, summary_text, target_text, criteria_text, benefit_text
FROM public.benefit LIMIT 100;
SELECT * FROM public.benefit WHERE detail_collected_at IS NULL;
```

기존 DB 전환은 migrate_to_benefit.py로 수행합니다. 기존 테이블 전체를 data/backups에
JSON으로 보관하고 13개 컬럼을 전수 대조한 뒤 이전 테이블/뷰/함수를 삭제합니다.
모든 DB 변경은 하나의 트랜잭션이며 오류 발생 시 롤백됩니다. 기존 상세 ID는 유지합니다.
benefit_schema.sql은 새 스키마, health_rag_DB.sql은 초기 생성용입니다.
setup_regions.py/regions.sql은 폐기된 구조를 재생성하지 않도록 비활성화했습니다.


## 신청 기간과 상태 (추가 5컬럼)
application_start_date: 명시된 신청 시작일, application_deadline: 명시된 신청 마감일.
application_status: unknown(확인 필요), scheduled(접수 예정), open(기간상 접수 중), closed(기간상 마감).
application_period_text: 판정 근거 원문, status_checked_at: 날짜 기준 상태를 계산한 시각.
신청/접수 기간으로 명시된 단일 절대 날짜 구간만 추출합니다. 사업 시행일이나 사용기간은 사용하지 않습니다.
상시, 출산 후 N일, 예산 소진, 여러 차수, 연도 없는 일정은 자동 확정하지 않습니다.
마감일 당일은 open으로 계산하며 시각 단위 조기 마감이나 실제 모집 여부는 공식 안내로 확인해야 합니다.
상태는 저장된 값이므로 시간이 지나면 자동 변경되지 않습니다. 수집 시 갱신하며,
조회 전에 아래 SQL로 한국 시간 오늘 기준 상태를 갱신할 수 있습니다.

```sql
SELECT refresh_benefit_application_status();
SELECT name, application_start_date, application_deadline, application_status,
       application_period_text, status_checked_at FROM benefit;
```

기존 XML 보충: python backfill_application_status.py (DB 백업 후 기존 상세 본문과 일치하는 XML만 적용).
현재 스키마는 총 18컬럼이며 이전 문단의 13개는 기본 컬럼입니다.

## 의료 관련 별도 테이블: healty_benefit

`create_healty_benefit.py`는 `.env`의 Supabase 클라우드 DB에 연결하여
`public.benefit`에서 `public.healty_benefit`을 생성하고 선택한 행을 복사합니다.
저장된 최신 목록 XML의 중앙 `intrsThemaArray`, 지자체 `intrsThemaNmArray`를
사용하며, 010(신체건강), 020(정신건강), 080(임신·출산) 중 하나 이상이면 포함합니다.
서비스 식별자는 `(source, source_service_id)`로 대조하며 이름도 일치해야 합니다.
분류가 없는 항목은 제외하고, 목록 자체가 없거나 이름이 다르면 작업을 중단합니다.

원본 18컬럼 중 `collected_at`, `detail_collected_at`만 제외한 16컬럼을 복사합니다.
신청일과 마감일, 신청 상태 및 상태 확인 시각 `status_checked_at`은 유지합니다.
원본 ID도 유지하며 새 테이블의 identity 시퀀스는 복사된 최대 ID로 맞춥니다.
원본의 제약조건과 인덱스를 복제하며, 원본 RLS가 켜져 있으면 새 테이블에도 켭니다.
RLS 정책은 복제하지 않으므로 클라이언트 API 접근은 별도 정책이 필요합니다.

2026-10-20 실행 결과: 전체 5,286건 중 770건(중앙 141, 지자체 629).
주제별 건수는 010 274건, 020 53건, 080 504건이며 복수 주제 때문에 중복됩니다.
분류가 없는 1,228건은 제외했습니다. 복사된 모든 컬럼의 원본 대비 차이는 0건입니다.
선택 ID, 분류 코드, 근거 XML 경로는 `data/exports/*_healty_benefit.json`에 기록합니다.

이 테이블은 실행 당시의 복사본이며 기존 수집기 및 신청 상태 갱신 함수는 계속
`benefit`에만 적용됩니다. 자동 동기화되지 않습니다. 스크립트는 기존
`healty_benefit`이 있으면 덮어쓰지 않고 중단하며, 생성과 검증은 한 트랜잭션입니다.
