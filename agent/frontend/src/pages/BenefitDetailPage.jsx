import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import {
  ArrowLeft, ArrowRight, ArrowUpRight, CalendarDays, ClipboardList, FileText, Landmark, MapPin,
  MessageCircleHeart, Scale, UserCheck,
} from 'lucide-react'
import { getBenefits } from '../api.js'
import { FACILITY_META } from '../facilityTypes.js'
import { useRegion } from '../region.jsx'
import { FormLink, REVIEW_LABELS, STATUS, audienceOf, iconFor, periodOf } from '../benefitMeta.jsx'

// 신청방법 원문은 '신청기관: … 조사기관: … 결정기관: …'이 한 줄로 이어져 와서 단계별로 나눈다
const STEP_RE = /([가-힣]+기관(?:목록)?)\s*:/g
function splitSteps(text) {
  const marks = [...text.matchAll(STEP_RE)]
  if (marks.length < 2) return null
  return marks.map((m, i) => ({
    label: m[1].replace(/목록$/, ''),
    body: text.slice(m.index + m[0].length, marks[i + 1]?.index ?? text.length).trim(),
  })).filter((s) => s.body)
}

// 선정기준 원문도 줄바꿈 없이 이어져 와서 ❶·①·○·※ 같은 항목 기호 앞에서 줄을 나눈다
const BULLET_RE = /\s*([❶-❿①-⑳○●■□▶※]|\(\d+\)|\d+\)\s)/g
const formatCriteria = (text) => text.replace(BULLET_RE, '\n$1').replace(/^\n/, '').replace(/\n{2,}/g, '\n')

export default function BenefitDetailPage() {
  const { id } = useParams()
  const [search] = useSearchParams()
  const location = useLocation()
  const navigate = useNavigate()
  const { region } = useRegion()
  // 목록·기관 화면에서 넘어오면 혜택 데이터를 그대로 받고, 새로고침 등으로 없으면 다시 조회한다
  const [benefit, setBenefit] = useState(String(location.state?.benefit?.id) === id ? location.state.benefit : null)
  const [error, setError] = useState(null)

  const province = search.get('province') ?? region?.province
  const municipality = search.get('municipality') ?? (search.get('province') ? null : region?.municipality)

  // 목록에서 내려온 스크롤 위치가 남지 않게 맨 위부터 보여준다
  useEffect(() => {
    window.scrollTo(0, 0)
    document.querySelector('.content')?.scrollTo(0, 0)
  }, [id])

  useEffect(() => {
    if (benefit && String(benefit.id) === id) return
    if (!province) return
    setError(null)
    getBenefits({ province, municipality })
      .then((data) => {
        const found = [...(data.matched ?? []), ...(data.needs_review ?? [])].find((b) => String(b.id) === id)
        if (found) setBenefit(found)
        else setError('혜택 정보를 찾을 수 없어요. 혜택 목록에서 다시 골라 주세요.')
      })
      .catch((e) => setError(e.message))
  }, [id, province, municipality, benefit])

  // 이전 화면(혜택 목록·기관 상세)으로 돌아간다. 직접 들어온 경우엔 혜택 목록으로
  const goBack = () => (location.key !== 'default' ? navigate(-1) : navigate('/benefits'))
  const back = <button type="button" className="back" onClick={goBack}><ArrowLeft size={18} />뒤로</button>

  if (error) return <section className="page">{back}<p className="error">{error}</p></section>
  if (!benefit) return <section className="page">{back}<p className="empty">불러오는 중…</p></section>

  const b = benefit
  const Icon = iconFor(b)
  const status = STATUS[b.application_status] ?? STATUS.unknown
  const facility = FACILITY_META[b.related_facility_type]
  const period = periodOf(b)
  const steps = b.application_method ? splitSteps(b.application_method) : null

  return (
    <section className="page benefit-detail">
      {back}

      <div className="detail-hero glass">
        <span className="icon-tile lg blue"><Icon size={28} strokeWidth={1.6} /></span>
        <div className="detail-hero-text">
          <div className="benefit-tags">
            <span className={`tag ${b.source === 'central' ? 'blue' : 'pink'}`}>{b.source === 'central' ? '중앙부처' : '지자체'}</span>
            <span className={`tag ${status.tone}`}>{status.label}</span>
            {b.review_fields.map((f) => <span key={f} className="tag gray">{REVIEW_LABELS[f] ?? f} 확인</span>)}
          </div>
          <h1>{b.name}</h1>
          {b.summary_text && <p className="lead">{b.summary_text}</p>}
        </div>
      </div>

      <ul className="bd-facts glass">
        <li><UserCheck size={18} /><span>대상</span><strong>{audienceOf(b)}</strong></li>
        <li>
          {b.region_scope === 'nationwide' ? <Landmark size={18} /> : <MapPin size={18} />}
          <span>지역</span><strong>{b.display.region}</strong>
        </li>
        <li><CalendarDays size={18} /><span>신청기간</span><strong>{period ?? '상시 · 원문 확인'}</strong></li>
      </ul>

      <div className="bd-sections">
        {b.criteria_text && (
          <article className="bd-section glass">
            <h2 className="section-title"><ClipboardList size={20} strokeWidth={1.8} />누가 받을 수 있나요 · 공식 선정기준</h2>
            <p className="bd-text">{formatCriteria(b.criteria_text)}</p>
          </article>
        )}

        {b.application_method && (
          <article className="bd-section glass">
            <h2 className="section-title"><FileText size={20} strokeWidth={1.8} />어떻게 신청하나요</h2>
            {steps ? (
              <ol className="bd-steps">
                {steps.map((s, i) => (
                  <li key={s.label + i}><span className="bd-step-no">{i + 1}</span><div><strong>{s.label}</strong><p>{s.body}</p></div></li>
                ))}
              </ol>
            ) : (
              <p className="bd-text">{b.application_method}</p>
            )}
          </article>
        )}

        {(b.application_forms?.length > 0 || b.legal_basis?.length > 0) && (
          <article className="bd-section glass">
            <h2 className="section-title"><Scale size={20} strokeWidth={1.8} />서식 · 근거법령</h2>
            <dl className="benefit-facts">
              {b.application_forms?.length > 0 && (
                <><dt>서식</dt><dd className="form-links">{b.application_forms.map((f) => <FormLink key={f.name + f.link} form={f} />)}</dd></>
              )}
              {b.legal_basis?.length > 0 && <><dt>근거법령</dt><dd>{b.legal_basis.join(', ')}</dd></>}
            </dl>
          </article>
        )}
      </div>

      <div className="bd-actions">
        {b.source_url && (
          <a className="benefit-cta" href={b.source_url} target="_blank" rel="noreferrer">
            복지로 원문 보기 <ArrowUpRight size={16} />
          </a>
        )}
        {facility && (
          <Link className="benefit-cta" to={`/map?types=${b.related_facility_type}`}>
            가까운 {facility.label} 보기 <ArrowRight size={16} />
          </Link>
        )}
        <button
          type="button"
          className="benefit-cta dark"
          onClick={() => navigate(`/?q=${encodeURIComponent(`${b.name} 신청 방법과 대상 알려줘`)}`)}
        >
          <MessageCircleHeart size={16} />챗봇에 물어보기
        </button>
      </div>

      <p className="data-source">출처: 한국사회보장정보원 중앙부처·지자체 복지서비스 (공공데이터포털)</p>
    </section>
  )
}
