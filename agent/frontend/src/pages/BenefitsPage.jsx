import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  ChevronLeft, ChevronRight, Info, Search, X,
} from 'lucide-react'
import { getBenefits } from '../api.js'
import { useRegion } from '../regionContext.js'
import {
  LIFE_CYCLES, REVIEW_LABELS, STATUS, THEMES, benefitPath, hasRegion, iconFor, periodOf, toneFor,
} from '../benefitMeta.js'

// 검색은 이미 받아온 혜택 안에서 한다. 띄어쓰기는 무시하고, 여러 단어는 모두 들어간 것만(AND)
const squash = (t) => (t ?? '').replace(/\s+/g, '').toLowerCase()
const haystack = (b) => squash([
  b.name, b.summary_text, b.criteria_text, b.application_method, b.display?.target_group, b.display?.life_cycle,
  ...(b.legal_basis ?? []),
].join(' '))

function searchBenefits(list, query) {
  const words = query.trim().split(/\s+/).map(squash).filter(Boolean)
  if (!words.length) return list
  return list
    .filter((b) => { const text = haystack(b); return words.every((w) => text.includes(w)) })
    // 이름에 검색어가 들어간 혜택을 위로
    .map((b) => ({ b, inName: words.filter((w) => squash(b.name).includes(w)).length }))
    .sort((x, y) => y.inName - x.inName)
    .map(({ b }) => b)
}

export default function BenefitsPage() {
  const { region, label: regionLabel, shortLabel } = useRegion()
  const [lifeCycles, setLifeCycles] = useState([])
  const [themes, setThemes] = useState([])
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  // 검색어는 주소(?q=)에 둬서 상세 페이지에 갔다가 뒤로 와도 남아 있게 한다
  const [params, setParams] = useSearchParams()
  const query = params.get('q') ?? ''
  // 검색어·페이지·한 페이지 개수 모두 주소에 둔다. 값이 비거나 기본값이면 주소에서 뺀다
  const updateParams = (patch) => setParams((prev) => {
    const next = new URLSearchParams(prev)
    for (const [k, v] of Object.entries(patch)) {
      if (v === '' || v == null || (k === 'page' && v === 1) || (k === 'size' && v === PAGE_SIZES[0])) next.delete(k)
      else next.set(k, String(v))
    }
    return next
  }, { replace: true })
  const setQuery = (q) => updateParams({ q, page: 1 })
  const pageSize = PAGE_SIZES.includes(Number(params.get('size'))) ? Number(params.get('size')) : PAGE_SIZES[0]
  const requestedPage = Math.max(1, Number(params.get('page')) || 1)
  // 입력 중인 글자(draft)와 실제 검색어(query)를 나눠서, 엔터나 검색 아이콘을 눌렀을 때만 결과를 바꾼다
  const [draft, setDraft] = useState(query)
  useEffect(() => { setDraft(query) }, [query]) // 뒤로가기 등으로 주소의 검색어가 바뀌면 입력창도 맞춘다
  const submitSearch = (e) => {
    e.preventDefault()
    // 한글 입력 중 엔터를 눌러도 마지막 글자까지 들어가게 state 대신 입력창 값을 읽는다
    setQuery(e.currentTarget.elements.q.value.trim())
  }
  const clearSearch = () => { setDraft(''); setQuery('') }

  useEffect(() => {
    if (!region) return
    setError(null)
    getBenefits({ province: region.province, municipality: region.municipality, life_cycle: lifeCycles, themes })
      .then(setData)
      .catch((e) => setError(e.message))
  }, [region, lifeCycles, themes])

  // '조건 일치'와 '원문 확인 필요'를 한 목록으로 합친다 (일치하는 것 먼저).
  // 원문 확인이 필요한 혜택은 카드에 '○○ 확인' 태그가 붙어서 구분된다
  const results = useMemo(
    () => searchBenefits([...(data?.matched ?? []), ...(data?.needs_review ?? [])], query),
    [data, query],
  )
  const searching = query.trim() !== ''
  const pageCount = Math.max(1, Math.ceil(results.length / pageSize))
  const page = Math.min(requestedPage, pageCount)
  const pageItems = results.slice((page - 1) * pageSize, page * pageSize)

  const goPage = (p) => {
    updateParams({ page: p })
    window.scrollTo({ top: 0, behavior: 'smooth' })
    document.querySelector('.content')?.scrollTo({ top: 0, behavior: 'smooth' })
  }
  // '' (전체)는 선택을 모두 풀고, 나머지는 켜고 끈다
  const toggleLifeCycle = (v) => {
    setLifeCycles((cur) => (!v ? [] : cur.includes(v) ? cur.filter((c) => c !== v) : [...cur, v]))
    updateParams({ page: 1 })
  }
  const toggleTheme = (code) => {
    setThemes((t) => (t.includes(code) ? t.filter((c) => c !== code) : [...t, code]))
    updateParams({ page: 1 })
  }

  return (
    <section className="page page-wide">
      <header className="page-head">
        <h1>{regionLabel ? `${shortLabel} · ${lifeCycleTitle(lifeCycles)}` : '나에게 맞는 의료·복지 혜택'}</h1>
        <p>{regionLabel} 주민이 받을 수 있는 혜택을 모았어요. 지역은 왼쪽 메뉴에서 바꿀 수 있어요.</p>
      </header>

      {/* 검색 · 생애주기 · 분야를 한 패널로 묶는다 (따로 떠 있으면 서로 관계없어 보여서) */}
      <div className="filter-panel glass">
      <form className="search benefit-search" role="search" onSubmit={submitSearch}>
        <button type="submit" className="search-submit" aria-label="검색">
          <Search size={18} strokeWidth={1.8} />
        </button>
        <input
          name="q"
          type="search"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="혜택 이름, 질환, 대상으로 검색 (예: 치매, 임산부 의료비)"
          aria-label="혜택 검색어"
          enterKeyHint="search"
        />
        {(draft || query) && (
          <button type="button" className="search-clear" onClick={clearSearch} aria-label="검색어 지우기">
            <X size={16} />
          </button>
        )}
      </form>

      <div className="filter-row">
        <span className="filter-label">연령</span>
        {/* 여러 개 고를 수 있다(OR). '전체'는 고른 걸 모두 푼다 */}
        <div className="segmented" role="group" aria-label="생애주기 (여러 개 선택 가능)">
          {LIFE_CYCLES.map(({ value, label, icon: Icon }) => {
            const on = value ? lifeCycles.includes(value) : lifeCycles.length === 0
            return (
            <button
              key={label}
              type="button"
              aria-pressed={on}
              className={on ? 'active' : ''}
              onClick={() => toggleLifeCycle(value)}
            >
              <Icon size={16} strokeWidth={1.8} />{label}
            </button>
            )
          })}
        </div>
      </div>
      <div className="filter-row">
        <span className="filter-label">분야</span>
        <div className="filter-chips">
        {THEMES.map(({ code, label, icon: Icon, tone }) => (
          <button
            key={code}
            aria-pressed={themes.includes(code)}
            className={`toggle ${tone} ${themes.includes(code) ? 'on' : ''}`}
            onClick={() => toggleTheme(code)}
          >
            <Icon size={15} strokeWidth={1.8} />{label}
          </button>
        ))}
        </div>
      </div>
      <p className="filter-note"><Info size={14} strokeWidth={1.8} />소득 정보는 묻지 않아요. 각 혜택의 공식 선정기준을 보고 직접 확인해 주세요.</p>
      </div>

      {error && <p className="error">{error}</p>}

      {data && (
        <div className="results-bar">
          <p className={searching ? 'search-summary' : ''}>
            {searching ? <>‘{query.trim()}’ 검색 결과 </> : '전체 '}
            <strong>{results.length}건</strong>
            {results.length > 0 && <span className="results-range"> · {(page - 1) * pageSize + 1}–{Math.min(page * pageSize, results.length)}번째</span>}
          </p>
          <label className="page-size">
            <span>한 페이지에</span>
            <select value={pageSize} onChange={(e) => updateParams({ size: Number(e.target.value), page: 1 })}>
              {PAGE_SIZES.map((n) => <option key={n} value={n}>{n}개씩</option>)}
            </select>
          </label>
        </div>
      )}

      <ul className="benefit-grid">
        {pageItems.map((b) => <BenefitCard key={b.id} b={b} region={region} />)}
      </ul>
      {data && results.length === 0 && !error && (
        <p className="empty">
          {searching
            ? '검색어와 맞는 혜택이 없어요. 다른 단어로 찾아보거나 생애주기·분야 조건을 풀어 보세요.'
            : '조건에 맞는 혜택이 없어요.'}
        </p>
      )}
      {pageCount > 1 && <Pagination page={page} pageCount={pageCount} onChange={goPage} />}

      {data?.notice && <p className="data-source">{data.notice}</p>}
      <p className="data-source">출처: 한국사회보장정보원 중앙부처·지자체 복지서비스 (공공데이터포털)</p>
    </section>
  )
}

const PAGE_SIZES = [10, 50, 100]
// search_benefits가 분류가 비어 있을 때 넣는 표시 문구 (UNKNOWN_LABEL)
const UNKNOWN_AUDIENCE = '대상 원문 확인'

/** 제목에 쓸 연령 이름. 화면 표기(label)로, LIFE_CYCLES 순서대로 '영유아, 아동' 처럼 잇는다 */
function lifeCycleTitle(selected) {
  if (!selected.length) return '전체 연령'
  return LIFE_CYCLES.filter((c) => c.value && selected.includes(c.value)).map((c) => c.label).join(', ')
}

/** 1 … 4 5 [6] 7 8 … 20 처럼 현재 페이지 주변만 번호로 보여준다 */
function pageNumbers(page, count) {
  const set = new Set([1, count, page - 2, page - 1, page, page + 1, page + 2])
  const nums = [...set].filter((n) => n >= 1 && n <= count).sort((a, b) => a - b)
  return nums.flatMap((n, i) => (i > 0 && n - nums[i - 1] > 1 ? ['gap' + n, n] : [n]))
}

function Pagination({ page, pageCount, onChange }) {
  return (
    <nav className="pagination" aria-label="혜택 페이지">
      <button type="button" disabled={page === 1} onClick={() => onChange(page - 1)} aria-label="이전 페이지">
        <ChevronLeft size={18} />
      </button>
      {pageNumbers(page, pageCount).map((n) =>
        typeof n === 'string'
          ? <span key={n} className="page-gap">…</span>
          : (
            <button
              key={n}
              type="button"
              className={n === page ? 'active' : ''}
              aria-current={n === page ? 'page' : undefined}
              onClick={() => onChange(n)}
            >
              {n}
            </button>
          ),
      )}
      <button type="button" disabled={page === pageCount} onClick={() => onChange(page + 1)} aria-label="다음 페이지">
        <ChevronRight size={18} />
      </button>
    </nav>
  )
}

// 카드 한 장: 아이콘·구분 태그 | 이름(2줄) | 요약(3줄) | 대상·지역·기간.
// 넓은 화면에선 한 줄에 5장이라 기본 10개씩이면 2줄이 된다. 긴 원문은 상세 페이지에서 보여준다
function BenefitCard({ b, region }) {
  const Icon = iconFor(b)
  // 카드에선 신청 기간을 알 때만 상태 태그를 단다 ('기간 확인'은 빼고, 자세한 건 상세 페이지에서)
  const status = b.application_status !== 'unknown' ? STATUS[b.application_status] : null
  const period = periodOf(b)
  // '지역 확인'도 카드에선 뺀다. 지역을 모르는 혜택은 아래 '지역' 줄이 이미 빠져 있다
  const reviews = b.review_fields.filter((f) => f !== 'region')
  // '대상 원문 확인'(분류가 비어 있음)은 카드에서 빼고, 아는 대상만 보여 준다. 둘 다 모르면 '대상' 줄을 뺀다
  const audience = [b.display.life_cycle, b.display.target_group].filter((t) => t && t !== UNKNOWN_AUDIENCE).join(' · ')
  return (
    <li className="benefit-card glass">
      <Link className="bc-link" to={benefitPath(b, region)} state={{ benefit: b }}>
        <div className="bc-top">
          <span className={`icon-tile ${toneFor(b)}`}><Icon size={20} strokeWidth={1.8} /></span>
          <div className="bc-tags">
            <span className={`tag ${b.source === 'central' ? 'blue' : 'pink'}`}>{b.source === 'central' ? '중앙부처' : '지자체'}</span>
            {status && <span className={`tag ${status.tone}`}>{status.label}</span>}
          </div>
        </div>
        <h3 className="clamp-2" title={b.name}>{b.name}</h3>
        {b.summary_text && <p className="clamp-3" title={b.summary_text}>{b.summary_text}</p>}
        {reviews.length > 0 && (
          <div className="bc-tags">
            {reviews.map((f) => <span key={f} className="tag gray">{REVIEW_LABELS[f] ?? f} 확인</span>)}
          </div>
        )}
        <dl className="bc-meta">
          {audience && <><dt>대상</dt><dd title={audience}>{audience}</dd></>}
          {/* 제공 지역 정보가 없는 혜택('대상 원문 확인')은 위치 표시를 뺀다 */}
          {hasRegion(b) && <><dt>지역</dt><dd title={b.display.region}>{b.display.region}</dd></>}
          {period && <><dt>기간</dt><dd title={period}>{period}</dd></>}
        </dl>
        <span className="bc-more">자세히 보기<ChevronRight size={15} /></span>
      </Link>
    </li>
  )
}
