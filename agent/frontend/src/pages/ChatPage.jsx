import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  ArrowUp, Baby, Brain, ExternalLink, FileText, Gift, HeartPulse, History, MapPinned, Stethoscope, X,
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

/** 출처 보조 설명: 근거법령 > 소관부처 > 주소 > 지역 (중앙부처는 '전국') */
const sourceNote = (s) =>
  s.metadata?.근거법령 || s.metadata?.소관부처 || s.metadata?.주소 || s.metadata?.지역 ||
  (s.source === 'welfare_central' ? '전국' : '')

/** 원문 링크 (http(s)만) */
const sourceUrl = (s) => {
  const url = s.metadata?.source_url || s.metadata?.url
  return /^https?:\/\//.test(url ?? '') ? url : null
}

/** 혜택 상세로 열 수 있는 출처의 서비스 코드 */
const benefitServiceId = (s) =>
  (s.source === 'welfare_central' || s.source === 'welfare_local') ? s.metadata?.source_service_id : null

/** 답변 끝 '[출처]' 목록은 인용 출처와 겹쳐서 뗀다 (**[출처]**, ### [출처] 같은 꾸밈 포함) */
const stripSourceList = (text) =>
  text.replace(/\n+(-{3,}\s*\n+)?[ \t]*(#{1,6}[ \t]*)?(\*\*)?\[출처\](\*\*)?[\s\S]*$/, '').trim()

/** 저장된 메시지 → 이전 대화 최근 10개 (오류·차단된 답변과 그 질문은 뺀다) */
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
  const { label: regionLabel } = useRegion()
  const [params, setParams] = useSearchParams()
  const navigate = useNavigate()

  // 복지 출처 → 서비스 코드로 혜택 상세 열기
  const openBenefit = useCallback(async (s) => {
    try {
      const b = await getBenefitByService(s.source, benefitServiceId(s))
      const region = b.provider_province ? { province: b.provider_province, municipality: b.provider_municipality } : null
      navigate(benefitPath(b, region), { state: { benefit: b } })
    } catch (e) {
      // 혜택 DB에 없으면 원문으로
      if (sourceUrl(s)) window.open(sourceUrl(s), '_blank', 'noreferrer')
      else window.alert(`혜택 정보를 열 수 없어요: ${e.message}`)
    }
  }, [navigate])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, loading])

  // 들어오면 항상 새 대화
  useEffect(() => {
    startNew()
  }, [startNew])

  // 다른 대화를 열면 맨 아래로
  useEffect(() => {
    endRef.current?.scrollIntoView({ block: 'end' })
  }, [active?.id])

  const send = useCallback(async (query) => {
    if (!query.trim() || loading) return
    const continuing = Boolean(active)
    const id = continuing ? active.id : create(query)
    // 후속 질문 이해용으로 이전 대화를 같이 보낸다
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

  // "챗봇에 물어보기"로 온 질문(?q=)은 입력창에만 채운다
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
        {/* 모바일: 대화 기록 서랍 */}
        <div className="chat-topbar">
          <button onClick={() => setDrawerOpen(true)}><History size={17} />대화 기록</button>
        </div>
        {empty ? (
          <div className="welcome">
            <h1>필요한 도움, 곁에서 같이 찾아볼게요</h1>
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
                  {m.role === 'bot' ? (
                    // 마크다운 (원문 HTML은 렌더링 안 함)
                    <div className="markdown"><Markdown remarkPlugins={[remarkGfm]}>{stripSourceList(m.text)}</Markdown></div>
                  ) : (
                    <p>{m.text}</p>
                  )}
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
