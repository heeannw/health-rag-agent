import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  ArrowUp, Baby, Brain, ExternalLink, FileText, Gift, HeartHandshake, HeartPulse, History, MapPinned, Stethoscope, X,
} from 'lucide-react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { SOURCE_LABELS, askChat, getBenefitByService } from '../api.js'
import { benefitPath } from '../benefitMeta.js'
import { useRegion } from '../regionContext.js'
import { useChatHistory } from '../chatHistoryContext.js'
import ConversationList from '../components/ConversationList.jsx'
import { BodeumAvatar } from '../components/BrandMark.jsx'

const NO_MESSAGES = []

const EXAMPLES = [
  { icon: HeartPulse, tone: 'blue', title: '어르신 의료 혜택', query: '65세 이상 받을 수 있는 의료 혜택 뭐 있어?' },
  { icon: Brain, tone: 'pink', title: '치매 지원', query: '치매 검사 무료로 받는 곳 알려줘' },
  { icon: Baby, tone: 'mint', title: '임신·출산', query: '임산부가 받을 수 있는 의료 지원은?' },
  { icon: Stethoscope, tone: 'blue', title: '법·제도', query: '고혈압 관련 법 제도 알려줘' },
]

/**
 * 인용 출처 한 건의 보조 설명 (근거법령 > 소관부처 > 주소 > 지역).
 * 혜택 DB로 다시 만든 복지 인덱스엔 근거법령·소관부처가 없어 지역을 보여주고, 중앙부처 사업은 전국
 */
const sourceNote = (s) =>
  s.metadata?.근거법령 || s.metadata?.소관부처 || s.metadata?.주소 || s.metadata?.지역 ||
  (s.source === 'welfare_central' ? '전국' : '')

/** 원문 링크 (http(s)만) */
const sourceUrl = (s) => {
  const url = s.metadata?.source_url || s.metadata?.url
  return /^https?:\/\//.test(url ?? '') ? url : null
}

/** 혜택 상세 페이지로 열 수 있는 출처 (복지 인덱스의 서비스 코드가 있을 때) */
const benefitServiceId = (s) =>
  (s.source === 'welfare_central' || s.source === 'welfare_local') ? s.metadata?.source_service_id : null

/** LLM 답변 끝의 '[출처]' 목록은 답변 아래 인용 출처 목록과 겹쳐서 뗀다 */
const stripSourceList = (text) => text.replace(/\n+(-{3,}\s*\n+)?\[출처\][\s\S]*$/, '').trim()

/**
 * 저장된 메시지 → API에 보낼 이전 대화 (최근 10개).
 * 오류 답변이나 범위 밖이라 막힌 답변은 그 답변과 바로 앞 질문까지 같이 뺀다
 */
const toHistory = (messages) =>
  messages
    .filter((m, i) => {
      const skip = (x) => x?.role === 'bot' && (x.error || x.blocked)
      return !skip(m) && !(m.role === 'user' && skip(messages[i + 1]))
    })
    .slice(-10)
    .map((m) => ({ role: m.role === 'bot' ? 'assistant' : 'user', content: m.role === 'bot' ? stripSourceList(m.text) : m.text }))

export default function ChatPage() {
  const { active, create, append, pending, setPendingFor, startNew } = useChatHistory()
  const messages = active?.messages ?? NO_MESSAGES
  const loading = active ? pending.has(active.id) : false
  const [input, setInput] = useState('')
  const [drawerOpen, setDrawerOpen] = useState(false)
  const endRef = useRef(null)
  const { label: regionLabel, shortLabel } = useRegion()
  const [params, setParams] = useSearchParams()
  const navigate = useNavigate()

  // 복지 출처를 누르면 서비스 코드로 혜택을 찾아 상세 화면으로. 새로고침해도 찾게 제공기관 지역을 넘긴다
  const openBenefit = useCallback(async (s) => {
    try {
      const b = await getBenefitByService(s.source, benefitServiceId(s))
      const region = b.provider_province ? { province: b.provider_province, municipality: b.provider_municipality } : null
      navigate(benefitPath(b, region), { state: { benefit: b } })
    } catch (e) {
      // 혜택 DB에 없는 출처(예: 예전 인덱스)면 원문으로 대신 연다
      if (sourceUrl(s)) window.open(sourceUrl(s), '_blank', 'noreferrer')
      else window.alert(`혜택 정보를 열 수 없어요: ${e.message}`)
    }
  }, [navigate])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, loading])

  // 챗봇 화면에 들어오면 이전 대화 대신 항상 새 대화로 시작
  useEffect(() => {
    startNew()
  }, [startNew])

  // 다른 대화를 열면 맨 아래(최근 메시지)로
  useEffect(() => {
    endRef.current?.scrollIntoView({ block: 'end' })
  }, [active?.id])

  const send = useCallback(async (query) => {
    if (!query.trim() || loading) return
    // 열린 대화가 있으면 그 대화에 이어서, 없으면 새 대화로 저장
    const continuing = Boolean(active)
    const id = continuing ? active.id : create(query)
    // 이전 대화를 같이 보내야 "신청은 어떻게 해?" 같은 후속 질문을 이해한다. 오류 답변은 뺀다
    const history = continuing ? toHistory(active.messages) : []
    append(id, { role: 'user', text: query })
    setInput('')
    setPendingFor(id, true)
    try {
      const res = await askChat(query, regionLabel, history)
      append(id, { role: 'bot', text: res.answer, sources: res.sources, blocked: res.blocked ?? null })
    } catch (e) {
      append(id, { role: 'bot', text: `오류가 발생했어요: ${e.message}`, sources: [], error: true })
    } finally {
      setPendingFor(id, false)
    }
  }, [loading, active, create, append, setPendingFor, regionLabel])

  // 기관·혜택 상세의 "챗봇에 물어보기"로 들어온 질문은 바로 보내지 않고 입력창에 채워만 둔다.
  // 사용자가 문장을 고치거나 덧붙인 뒤 직접 보낸다
  const inputRef = useRef(null)
  useEffect(() => {
    const q = params.get('q')
    if (!q) return
    setParams({}, { replace: true })
    setInput(q)
    requestAnimationFrame(() => {
      const el = inputRef.current
      if (!el) return
      el.focus()
      el.setSelectionRange(q.length, q.length)
    })
  }, [params, setParams])

  const empty = messages.length === 0

  return (
    <div className="chat-layout">
      <section className={`chat ${empty ? 'is-empty' : ''}`}>
        {/* 모바일: 사이드바가 없어서 대화 기록을 서랍으로 연다 */}
        <div className="chat-topbar">
          <button onClick={() => setDrawerOpen(true)}><History size={17} />대화 기록</button>
        </div>
        {empty ? (
          <div className="welcome">
            <h1>필요한 도움, 곁에서 같이 찾아볼게요.</h1>
            <p>{shortLabel ? `${regionLabel} 기준으로 ` : ''}복지 혜택, 신청 방법, 관련 법령, 의료기관 정보를 차근차근 안내해요.</p>
            <div className="prompt-grid">
              {EXAMPLES.map(({ icon: Icon, tone, title, query }) => (
                <button key={title} className="prompt-card glass" onClick={() => send(query)}>
                  <span className={`icon-tile ${tone}`}><Icon size={20} strokeWidth={1.8} /></span>
                  <strong>{title}</strong>
                  <span>{query}</span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="thread">
            {messages.map((m, i) => (
              <div key={i} className={`msg ${m.role}`}>
                {m.role === 'bot' && <BodeumAvatar />}
                <div className={`bubble ${m.role === 'bot' ? 'glass' : ''}`}>
                  {m.role === 'bot' && (
                    <div className="answer-meta">
                      {/* 범위 밖 질문에 대한 안내 문구는 검색 근거가 없으니 '안내'로 표시 */}
                      {m.blocked
                        ? <span className={`tag ${m.blocked === 'crisis' ? 'pink' : 'gray'}`}>{m.blocked === 'crisis' ? '도움 안내' : '안내'}</span>
                        : <span>근거 {m.sources?.length ?? 0}건</span>}
                    </div>
                  )}
                  {m.role === 'bot' ? (
                    // 답변은 마크다운(굵게·목록·제목). 원문 HTML은 렌더링하지 않는다(react-markdown 기본값)
                    <div className="markdown"><Markdown remarkPlugins={[remarkGfm]}>{stripSourceList(m.text)}</Markdown></div>
                  ) : (
                    <p>{m.text}</p>
                  )}
                  {/* 답변에 실제로 쓰인 문서를 답변 바로 아래에 번호와 함께 보여준다 */}
                  {m.sources?.length > 0 && (
                    <section className="answer-sources" aria-label="인용 출처">
                      <h4><FileText size={14} />인용 출처 <span>답변에 실제로 쓰인 자료</span></h4>
                      <ol>
                        {m.sources.map((s, j) => (
                          <li key={j}>
                            <b>{j + 1}</b>
                            <div>
                              {benefitServiceId(s)
                                ? <button type="button" className="source-title-link" onClick={() => openBenefit(s)}>{s.title}</button>
                                : <strong>{s.title}</strong>}
                              <small>
                                {SOURCE_LABELS[s.source] ?? s.source}
                                {sourceNote(s) && <> · {sourceNote(s)}</>}
                                {sourceUrl(s) && (
                                  <> · <a href={sourceUrl(s)} target="_blank" rel="noreferrer">원문 보기<ExternalLink size={11} /></a></>
                                )}
                              </small>
                            </div>
                          </li>
                        ))}
                      </ol>
                    </section>
                  )}
                  {m.role === 'bot' && i === messages.length - 1 && !loading && (
                    <div className="answer-actions">
                      <button onClick={() => navigate('/benefits')}><Gift size={15} />내 지역 혜택 더 보기</button>
                      <button onClick={() => navigate('/map')}><MapPinned size={15} />가까운 기관 찾기</button>
                    </div>
                  )}
                </div>
              </div>
            ))}
            {loading && (
              <div className="msg bot">
                <BodeumAvatar />
                <div className="bubble glass typing"><i /><i /><i /></div>
              </div>
            )}
            <div ref={endRef} />
          </div>
        )}

        <form className="composer glass" onSubmit={(e) => { e.preventDefault(); send(input) }}>
          <input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="보듬이에게 혜택, 제도, 기관을 물어보세요"
            aria-label="질문 입력"
          />
          <button className="send" disabled={loading || !input.trim()} aria-label="보내기">
            <ArrowUp size={20} strokeWidth={2.2} />
          </button>
        </form>
      </section>

      {drawerOpen && (
        <div className="history-drawer" role="dialog" aria-modal="true" aria-label="대화 기록">
          <button className="history-drawer-backdrop" aria-label="닫기" onClick={() => setDrawerOpen(false)} />
          <div className="history-drawer-panel glass">
            <button className="history-drawer-close" aria-label="닫기" onClick={() => setDrawerOpen(false)}><X size={18} /></button>
            <ConversationList onNavigate={() => setDrawerOpen(false)} />
          </div>
        </div>
      )}
    </div>
  )
}
