> 실행 예시는 저장소 루트 기준입니다. 파일별 새 위치와 실행 방법은 [README](../README.md)를 참고하세요.

# 단일 benefit 테이블

## 파이썬 의료 혜택 필터 추출

`search_benefits.py`는 `.env`로 연결한 `public.healty_benefit`을 읽기 전용으로
조회하고 생애주기·대상특성·제공기관 지역을 파이썬에서 필터링합니다.
DB와 원본 NULL은 변경하지 않습니다. 별도 패키지 `psycopg[binary]`,
`python-dotenv`가 필요하며 `--input` 사용 시 표준 라이브러리만으로 실행됩니다.

저장소 루트에서 실행:

```powershell
python health_benefits/run.py search --life-cycle 청년 --target-group 장애인 --province 서울특별시
python health_benefits/run.py search --life-cycle 영유아 --life-cycle 아동
python health_benefits/run.py search --province 전국
python health_benefits/run.py search --input benefits.json --life-cycle 청년 --output result.json
python -m unittest discover -s health_benefits/tests -p test_search_benefits.py
```

각 옵션을 생략하면 해당 분류를 제한하지 않습니다. 화면의 ‘전체’ 선택은 옵션 생략에
해당합니다. `--province 전국`은 명시적 전국 항목을 선택하며 지역 필터 생략과 다릅니다.
분류명과 지역명은 DB 원문명과 정확히 일치해야 합니다. 같은 분류의 반복 옵션은 OR,
생애주기·대상특성·지역 사이는 AND입니다. 시군구 선택에는 시도가 필요합니다.

기본 결과 파일은 `health_benefits/data/exports/filtered_benefits.json`이며 다시 실행하면
덮어씁니다. 다른 결과를 보관하려면 `--output`을 지정합니다. 입력 JSON은 행 객체 배열입니다.

- `matched`: 선택한 분류에 일치한 후보입니다. 신청 자격 확정을 의미하지 않습니다.
- `needs_review`: 알려진 불일치는 없지만 선택 조건의 정보가 없어 원문 확인이 필요한 후보입니다.
- 알려진 조건이 하나라도 불일치하면 두 목록 모두에서 제외합니다.
- 원본 필드는 그대로 보존하며 `display.life_cycle`, `display.target_group`,
  `display.region`에 화면 표시 문구를 제공합니다. NULL·빈 배열은 ‘대상 원문 확인’입니다.
- 생애주기·대상특성의 명시적 `전체`/`전체 대상`만 전체로 인정합니다.
  NULL을 ‘전 연령 지원’ 또는 전체 대상으로 바꾸지 않습니다.
- `region_scope`는 `nationwide`/`regional`/`unknown`입니다. 시도가 `전국`이고
  시군구가 없거나 `전국`인 경우만 전국으로 인정합니다. 중앙 사업 또는 지역 NULL이라는
  이유로 전국으로 추정하지 않습니다. 특정 지역 검색에는 명시적인 전국 항목도 포함합니다.
- 시군구가 NULL이면 시도 전체 지원이라고 추정하지 않습니다. 해당 시군구 검색에서는
  원문 확인 후보로 분리합니다. 제공기관 지역은 실제 신청자의 거주 요건과 다를 수 있습니다.
- 필터를 생략한 분류의 NULL은 후보를 제외하지 않지만 표시 문구는 계속 원문 확인입니다.
  `filter_status`는 선택 조건별 판정, `review_fields`는 미확인인 선택 조건입니다.

기존 수집/보충 스크립트 → `healty_benefit` → `search_benefits.py` → 결과 JSON 순서로
연결됩니다. 화면은 아직 연결하지 않았으며 JSON의 표시 문구를 사용할 수 있습니다.

## 생애주기·대상특성 보충

`backfill_audience_fields.py`는 최초 의료 혜택 추출 보고서와 원문 XML,
DB의 출처·서비스 ID·이름을 대조해 Supabase `healty_benefit`에 다음을 저장합니다.

| DB 컬럼 (TEXT[]) | 중앙 원문 | 지자체 원문 |
|---|---|---|
| life_cycle_names | lifeArray | lifeNmArray |
| target_group_names | trgterIndvdlArray | trgterIndvdlNmArray |

쉼표로 분리하고 앞뒤 공백과 중복만 제거합니다. 분류명 내부 표기는 유지합니다.
원문 값이 없으면 NULL이며 전체 대상이라는 뜻이 아닙니다.
생애주기 분류는 정확한 신청 연령 조건을 의미하지 않습니다.
2026-10-20 결과: 770건 중 생애주기 662건 저장 / 108건 NULL,
대상특성 239건 저장 / 531건 NULL. 기존 17컬럼과 행 수는 그대로 검증했습니다.
현재 의료 테이블은 이 두 컬럼을 포함하여 19컬럼입니다.
배열 필터용 GIN 인덱스를 추가했으며 자동 갱신은 아닙니다.
변경 전 데이터는 `data/backups/*_audience/healty_benefit.json`,
누락된 서비스와 필드 목록은 `data/exports/*_audience_missing.json`에 저장됩니다.
DB 갱신과 검증은 한 트랜잭션으로 실행합니다.

```sql
SELECT * FROM public.healty_benefit WHERE life_cycle_names @> ARRAY['청년']::text[];
SELECT * FROM public.healty_benefit WHERE target_group_names @> ARRAY['장애인']::text[];
```

## 의료 혜택 주제 코드 보충

`backfill_theme_codes.py`는 최초 `data/exports/*_healty_benefit.json`의 추출
근거와 해당 목록 XML을 대조하고, `.env`에 설정된 Supabase의
`public.healty_benefit`에 `theme_codes TEXT[]` 컬럼을 추가합니다.
연결 키는 `(source, source_service_id)`이며 ID와 이름도 검증합니다.
010=신체건강, 020=정신건강, 080=임신·출산이고 복수 코드를 유지합니다.
이 컬럼은 선별에 사용한 세 주제만 담으며 원문의 다른 주제까지 담지는 않습니다.

2026-10-20 적용: 770건, 코드별 010 274건 / 020 53건 / 080 504건.
복수 분류로 코드별 합계에는 중복이 있습니다. 기존 16컬럼과 행 수는 변함없습니다.
변경 전 전체 행은 `data/backups/*_themes/healty_benefit.json`에 보관합니다.
검증과 갱신은 하나의 트랜잭션이며 실패하면 DB 변경을 롤백합니다.
코드는 필수이며 허용 코드 검사 제약조건과 배열 검색용 GIN 인덱스를 추가합니다.
기존 생성 스크립트는 16컬럼 복사본을 만들므로 새로 생성할 경우 이 보충
스크립트도 실행해야 합니다. 자동 동기화나 화면 필터는 아직 구현하지 않았습니다.

```sql
-- 신체건강
SELECT * FROM public.healty_benefit WHERE theme_codes @> ARRAY['010']::text[];
-- 신체건강 또는 정신건강
SELECT * FROM public.healty_benefit WHERE theme_codes && ARRAY['010','020']::text[];
```

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
python health_benefits/run.py collect_catalog --source central
python health_benefits/run.py collect_catalog --source local
python health_benefits/run.py collect_many --source central --limit 0 --max-calls 1000 --refresh --skip-collected-today
python health_benefits/run.py collect_many --source local --limit 0 --max-calls 1100 --refresh --skip-collected-today
python health_benefits/run.py verify_collection
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

기존 XML 보충: python health_benefits/run.py backfill_application_status (DB 백업 후 기존 상세 본문과 일치하는 XML만 적용).
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
