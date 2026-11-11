import { useEffect, useState } from 'react'
import { useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import {
  ArrowLeft, ArrowUpRight, CalendarDays, FileText, Landmark, MapPin,
  MessageCircleHeart, Scale, UserCheck,
} from 'lucide-react'
import { getBenefits } from '../api.js'
import { useRegion } from '../regionContext.js'
import FormLink from '../components/FormLink.jsx'
import { REVIEW_LABELS, STATUS, hasRegion, iconFor, periodOf, toneFor } from '../benefitMeta.js'

// '신청기관: … 조사기관: …' 한 줄 원문을 단계별로 나눈다
const STEP_RE = /([가-힣]+기관(?:목록)?)\s*:/g
function splitSteps(text) {
  const marks = [...text.matchAll(STEP_RE)]
  if (marks.length < 2) return null
  return marks.map((m, i) => ({
    label: m[1].replace(/목록$/, ''),
    body: text.slice(m.index + m[0].length, marks[i + 1]?.index ?? text.length).trim(),
  })).filter((s) => s.body)
}

// 선정기준 원문을 항목 기호(❶·①·○·※ 등) 앞에서 줄바꿈
const BULLET_RE = /\s*([❶-❿①-⑳○●■□▶※]|\(\d+\)|\d+\)\s)/g
const formatCriteria = (text) => text.replace(BULLET_RE, '\n$1').replace(/^\n/, '').replace(/\n{2,}/g, '\n')

export default function BenefitDetailPage() {
  const { id } = useParams()
  const [search] = useSearchParams()
  const location = useLocation()
  const navigate = useNavigate()
  const { region } = useRegion()
  // 화면 이동으로 받은 혜택을 쓰고, 없으면 다시 조회
  const passed = String(location.state?.benefit?.id) === id ? location.state.benefit : null
  const [fetched, setFetched] = useState(null) // { id, benefit } | { id, error }
  const current = fetched?.id === id ? fetched : null
  const benefit = passed ?? current?.benefit ?? null
  const error = passed ? null : current?.error ?? null

  const province = search.get('province') ?? region?.province
  const municipality = search.get('municipality') ?? (search.get('province') ? null : region?.municipality)

  // 맨 위부터 보여준다
  useEffect(() => {
    window.scrollTo(0, 0)
    document.querySelector('.content')?.scrollTo(0, 0)
  }, [id])

  useEffect(() => {
    if (passed || !province) return
    let cancelled = false
    getBenefits({ province, municipality })
      .then((data) => {
        if (cancelled) return
        const found = [...(data.matched ?? []), ...(data.needs_review ?? [])].find((b) => String(b.id) === id)
        setFetched(found
          ? { id, benefit: found }
          : { id, error: '혜택 정보를 찾을 수 없어요. 혜택 목록에서 다시 골라 주세요.' })
      })
      .catch((e) => !cancelled && setFetched({ id, error: e.message }))
    return () => {
      cancelled = true
    }
  }, [id, province, municipality, passed])

  // 직접 들어온 경우엔 혜택 목록으로
  const goBack = () => (location.key !== 'default' ? navigate(-1) : navigate('/benefits'))
  const back = <button type="button" className="back" onClick={goBack}><ArrowLeft size={18} />뒤로</button>

  if (error) return <section className="page benefit-detail">{back}<p className="error">{error}</p></section>
  if (!benefit) return <section className="page benefit-detail">{back}<p className="empty">불러오는 중…</p></section>

  const b = benefit
  const Icon = iconFor(b)
  // 아는 정보만 보여 준다 ('○○ 확인'류는 뺀다)
  const status = b.application_status !== 'unknown' ? STATUS[b.application_status] : null
  const reviews = b.review_fields.filter((f) => f !== 'region')
  const audience = [...new Set([...(b.life_cycle_names ?? []), ...(b.target_group_names ?? [])].map((t) => t?.trim()).filter(Boolean))]
  const period = periodOf(b)
  const steps = b.application_method ? splitSteps(b.application_method) : null
  // 선정기준이 '없음'뿐이면 숨긴다 (대상이 없다는 뜻으로 읽혀서)
  const criteria = b.criteria_text?.trim() && b.criteria_text.trim() !== '없음' ? b.criteria_text : null
  const hasForms = b.application_forms?.length > 0 || b.legal_basis?.length > 0

  return (
    <section className="page benefit-detail">
      {back}

      <article className="bd-card glass">
        <header className="bd-head">
          <span className={`icon-tile lg ${toneFor(b)}`}><Icon size={28} strokeWidth={1.6} /></span>
          <div className="bd-head-text">
            <div className="benefit-tags">
              <span className={`tag ${b.source === 'central' ? 'blue' : 'pink'}`}>{b.source === 'central' ? '중앙부처' : '지자체'}</span>
              {status && <span className={`tag ${status.tone}`}>{status.label}</span>}
              {reviews.map((f) => <span key={f} className="tag gray">{REVIEW_LABELS[f] ?? f} 확인</span>)}
            </div>
            <h1>{b.name}</h1>
            {b.summary_text && <p className="lead">{b.summary_text}</p>}
            {(hasRegion(b) || period) && (
              <dl className="bd-info">
                {hasRegion(b) && (
                  <div>
                    <dt>{b.region_scope === 'nationwide' ? <Landmark size={16} /> : <MapPin size={16} />}지역</dt>
                    <dd>{b.display.region}</dd>
                  </div>
                )}
                {period && <div><dt><CalendarDays size={16} />신청기간</dt><dd>{period}</dd></div>}
              </dl>
            )}
          </div>
        </header>

        {(audience.length > 0 || criteria) && (
          <section className="bd-block">
            <h2 className="section-title"><UserCheck size={20} strokeWidth={1.8} />누가 받을 수 있나요</h2>
            {audience.length > 0 && (
              <div className="benefit-tags bd-audience">{audience.map((t) => <span key={t} className="tag mint">{t}</span>)}</div>
            )}
            {criteria && <p className="bd-text">{formatCriteria(criteria)}</p>}
          </section>
        )}

        {b.application_method && (
          <section className="bd-block">
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
          </section>
        )}

        {hasForms && (
          <section className="bd-block">
            <h2 className="section-title"><Scale size={20} strokeWidth={1.8} />서식 · 근거법령</h2>
            <dl className="benefit-facts">
              {b.application_forms?.length > 0 && (
                <><dt>서식</dt><dd className="form-links">{b.application_forms.map((f) => <FormLink key={f.name + f.link} form={f} />)}</dd></>
              )}
              {b.legal_basis?.length > 0 && <><dt>근거법령</dt><dd>{b.legal_basis.join(', ')}</dd></>}
            </dl>
          </section>
        )}

        <div className="bd-actions">
          {/^https?:\/\//.test(b.source_url ?? '') && (
            <a className="benefit-cta outline" href={b.source_url} target="_blank" rel="noreferrer">
              복지로 원문 보기 <ArrowUpRight size={16} />
            </a>
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
      </article>
    </section>
  )
}
