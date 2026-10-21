import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowRight, ArrowUpRight, Baby, Brain, Briefcase, GraduationCap, HeartPulse, Info, Landmark, MapPin, School, Smile,
  Sparkle, Users,
} from 'lucide-react'
import { getBenefits } from '../api.js'
import { FACILITY_META } from '../facilityTypes.js'
import { useRegion } from '../region.jsx'

// TODO: 가은 데이터의 실제 생애주기 분류값으로 교체
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

const iconFor = (b) => LIFE_CYCLES.find((c) => b.life_cycle_names.includes(c.value))?.icon ?? HeartPulse

export default function BenefitsPage() {
  const { region, label: regionLabel } = useRegion()
  const [lifeCycle, setLifeCycle] = useState('')
  const [themes, setThemes] = useState([])
  const [items, setItems] = useState([])
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!region) return
    getBenefits({ province: region.province, municipality: region.municipality, life_cycle: lifeCycle, themes })
      .then(setItems)
      .catch((e) => setError(e.message))
  }, [region, lifeCycle, themes])

  const toggleTheme = (code) =>
    setThemes((t) => (t.includes(code) ? t.filter((c) => c !== code) : [...t, code]))

  return (
    <section className="page">
      <header className="page-head">
        <span className="eyebrow">혜택 추천</span>
        <h1>{regionLabel ? `${region.municipality} · ${lifeCycle || '전체 연령'}` : '나에게 맞는 의료·복지 혜택'}</h1>
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
        {items.map((b, i) => {
          const Icon = iconFor(b)
          const status = STATUS[b.application_status] ?? STATUS.unknown
          const facility = FACILITY_META[b.related_facility_type]
          return (
            <li key={b.id} className="benefit-card glass">
              <div className="benefit-top">
                <span className="icon-tile blue"><Icon size={20} strokeWidth={1.8} /></span>
                <span className="benefit-no">{String(i + 1).padStart(2, '0')}</span>
              </div>
              <div className="benefit-tags">
                <span className={`tag ${b.source === 'central' ? 'blue' : 'pink'}`}>
                  {b.source === 'central' ? '중앙부처' : `지자체 · ${b.provider_municipality ?? ''}`}
                </span>
                <span className={`tag ${status.tone}`}>{status.label}</span>
              </div>
              <h3>{b.name}</h3>
              <p>{b.summary_text}</p>
              <dl className="benefit-facts">
                {b.criteria_text && <><dt>공식 기준</dt><dd className="hl">{b.criteria_text}</dd></>}
                {b.apply_method && <><dt>신청</dt><dd>{b.apply_method}</dd></>}
                {b.documents && <><dt>구비서류</dt><dd>{b.documents}</dd></>}
                {b.legal_basis && <><dt>근거법령</dt><dd>{b.legal_basis}</dd></>}
              </dl>
              <div className="benefit-foot">
                <span>
                  {b.source === 'central'
                    ? <><Landmark size={14} />전국</>
                    : <><MapPin size={14} />{b.provider_province} {b.provider_municipality}</>}
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
        })}
      </ul>
      {items.length === 0 && !error && <p className="empty">조건에 맞는 혜택이 없어요.</p>}
      <p className="data-source">출처: 한국사회보장정보원 중앙부처·지자체 복지서비스</p>
    </section>
  )
}
