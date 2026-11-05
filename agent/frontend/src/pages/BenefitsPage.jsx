import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowRight, ArrowUpRight, Baby, Brain, Briefcase, FileSearch, GraduationCap, HeartPulse, Info, Landmark, MapPin,
  FileDown, School, Smile, Sparkle, Users,
} from 'lucide-react'
import { getBenefits } from '../api.js'
import { FACILITY_META } from '../facilityTypes.js'
import { useRegion } from '../region.jsx'

// 가은 데이터 life_cycle_names 원문 분류명 (복지로 생애주기)
const LIFE_CYCLES = [
  { value: '', label: '전체', icon: Sparkle },
  { value: '영유아', label: '영유아', icon: Baby },
  { value: '아동', label: '아동', icon: Smile },
  { value: '청소년', label: '청소년', icon: School },
  { value: '청년', label: '청년', icon: GraduationCap },
  { value: '중장년', label: '중장년', icon: Briefcase },
  { value: '노년', label: '노년', icon: Users },
  { value: '임신·출산', label: '임신·출산', icon: HeartPulse },
]

// 가은 데이터의 theme_codes (의료 관련 3개 주제)
const THEMES = [
  { code: '010', label: '신체건강', icon: HeartPulse },
  { code: '020', label: '정신건강', icon: Brain },
  { code: '080', label: '임신·출산', icon: Baby },
]

const STATUS = {
  open: { label: '신청 가능', tone: 'mint' },
  scheduled: { label: '신청 예정', tone: 'blue' },
  closed: { label: '마감', tone: 'pink' },
  unknown: { label: '기간 확인', tone: 'gray' },
}

// search_benefits가 원문 확인으로 분리한 조건 이름
const REVIEW_LABELS = { life_cycle_names: '생애주기', target_group_names: '대상특성', region: '지역' }

const iconFor = (b) => LIFE_CYCLES.find((c) => c.value && b.life_cycle_names?.includes(c.value))?.icon ?? HeartPulse

// 둘 다 원문 미확인이면 '대상 원문 확인 · 대상 원문 확인'처럼 반복되지 않게 한 번만
const audienceOf = (b) => [...new Set([b.display.life_cycle, b.display.target_group])].join(' · ')

const periodOf = (b) =>
  b.application_start_date || b.application_deadline
    ? `${b.application_start_date ?? ''} ~ ${b.application_deadline ?? ''}`
    : null

export default function BenefitsPage() {
  const { region, label: regionLabel, shortLabel } = useRegion()
  const [lifeCycle, setLifeCycle] = useState('')
  const [themes, setThemes] = useState([])
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!region) return
    setError(null)
    getBenefits({ province: region.province, municipality: region.municipality, life_cycle: lifeCycle, themes })
      .then(setData)
      .catch((e) => setError(e.message))
  }, [region, lifeCycle, themes])

  const matched = data?.matched ?? []
  const needsReview = data?.needs_review ?? []

  const toggleTheme = (code) =>
    setThemes((t) => (t.includes(code) ? t.filter((c) => c !== code) : [...t, code]))

  return (
    <section className="page">
      <header className="page-head">
        <span className="eyebrow">혜택 추천</span>
        <h1>{regionLabel ? `${shortLabel} · ${lifeCycle || '전체 연령'}` : '나에게 맞는 의료·복지 혜택'}</h1>
        <p>{regionLabel} 주민이 받을 수 있는 혜택을 모았어요. 지역은 왼쪽 메뉴에서 바꿀 수 있어요.</p>
      </header>

      <div className="toolbar glass">
        <div className="segmented" role="tablist" aria-label="생애주기">
          {LIFE_CYCLES.map(({ value, label, icon: Icon }) => (
            <button
              key={label}
              role="tab"
              aria-selected={lifeCycle === value}
              className={lifeCycle === value ? 'active' : ''}
              onClick={() => setLifeCycle(value)}
            >
              <Icon size={16} strokeWidth={1.8} />{label}
            </button>
          ))}
        </div>
      </div>
      <div className="theme-row">
        <span>분야</span>
        {THEMES.map(({ code, label, icon: Icon }) => (
          <button
            key={code}
            aria-pressed={themes.includes(code)}
            className={`toggle ${themes.includes(code) ? 'on' : ''}`}
            onClick={() => toggleTheme(code)}
          >
            <Icon size={15} strokeWidth={1.8} />{label}
          </button>
        ))}
      </div>

      <p className="callout"><Info size={16} strokeWidth={1.8} />소득 정보는 묻지 않아요. 각 혜택의 공식 선정기준을 보고 직접 확인해 주세요.</p>
      {error && <p className="error">{error}</p>}

      <ul className="benefit-grid">
        {matched.map((b, i) => <BenefitCard key={b.id} b={b} no={i + 1} />)}
      </ul>
      {data && matched.length === 0 && !error && <p className="empty">조건에 딱 맞는 혜택이 없어요.</p>}

      {needsReview.length > 0 && (
        <>
          <h2 className="section-title"><FileSearch size={20} strokeWidth={1.8} />원문 확인이 필요한 혜택 {needsReview.length}건</h2>
          <p className="callout"><Info size={16} strokeWidth={1.8} />고른 조건과 다르지는 않지만, 원문에 해당 정보가 없어 일치 여부를 확인하지 못한 혜택이에요.</p>
          <ul className="benefit-grid">
            {needsReview.map((b, i) => <BenefitCard key={b.id} b={b} no={i + 1} />)}
          </ul>
        </>
      )}
      {data?.notice && <p className="data-source">{data.notice}</p>}
      <p className="data-source">출처: 한국사회보장정보원 중앙부처·지자체 복지서비스 (공공데이터포털)</p>
    </section>
  )
}

function BenefitCard({ b, no }) {
  const Icon = iconFor(b)
  const status = STATUS[b.application_status] ?? STATUS.unknown
  const facility = FACILITY_META[b.related_facility_type]
  const period = periodOf(b)
  return (
    <li className="benefit-card glass">
      <div className="benefit-top">
        <span className="icon-tile blue"><Icon size={20} strokeWidth={1.8} /></span>
        <span className="benefit-no">{String(no).padStart(2, '0')}</span>
      </div>
      <div className="benefit-tags">
        <span className={`tag ${b.source === 'central' ? 'blue' : 'pink'}`}>{b.source === 'central' ? '중앙부처' : '지자체'}</span>
        <span className={`tag ${status.tone}`}>{status.label}</span>
        {b.review_fields.map((f) => <span key={f} className="tag gray">{REVIEW_LABELS[f] ?? f} 확인</span>)}
      </div>
      <h3>{b.name}</h3>
      <p>{b.summary_text}</p>
      <dl className="benefit-facts">
        <dt>대상</dt><dd>{audienceOf(b)}</dd>
        {b.criteria_text && <><dt>공식 기준</dt><dd className="hl"><ClampText text={b.criteria_text} /></dd></>}
        {period && <><dt>신청기간</dt><dd>{period}</dd></>}
        {b.application_method && <><dt>신청</dt><dd>{b.application_method}</dd></>}
        {b.application_forms?.length > 0 && (
          <><dt>서식</dt><dd className="form-links">{b.application_forms.map((f) => <FormLink key={f.name + f.link} form={f} />)}</dd></>
        )}
        {b.legal_basis?.length > 0 && <><dt>근거법령</dt><dd>{b.legal_basis.join(', ')}</dd></>}
      </dl>
      <div className="benefit-foot">
        <span>
          {b.region_scope === 'nationwide' ? <Landmark size={14} /> : <MapPin size={14} />}
          {b.display.region}
        </span>
        {b.source_url && (
          <a href={b.source_url} target="_blank" rel="noreferrer">자세히 <ArrowUpRight size={14} /></a>
        )}
      </div>
      {facility && (
        <Link className="benefit-cta" to={`/map?types=${b.related_facility_type}`}>
          가까운 {facility.label} 보기 <ArrowRight size={16} />
        </Link>
      )}
    </li>
  )
}

// 신청 서식은 복지로 첨부파일 링크. http(s) 링크만 걸고 나머지는 이름만 보여준다
function FormLink({ form }) {
  const safe = /^https?:\/\//.test(form.link ?? '')
  return safe
    ? <a href={form.link} target="_blank" rel="noreferrer"><FileDown size={13} />{form.name}</a>
    : <span>{form.name}</span>
}

// 선정기준 원문은 최대 1,500자 넘게 길어서 3줄까지만 보여주고 펼칠 수 있게 한다
function ClampText({ text }) {
  const [open, setOpen] = useState(false)
  const long = text.length > 90
  return (
    <>
      <span className={long && !open ? 'clamp' : undefined}>{text}</span>
      {long && (
        <button type="button" className="more-btn" onClick={() => setOpen((o) => !o)}>
          {open ? '접기' : '더보기'}
        </button>
      )}
    </>
  )
}
