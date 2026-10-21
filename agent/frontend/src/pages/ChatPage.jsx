import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  ArrowRight, ArrowUp, Baby, Brain, FileText, Gift, HeartPulse, History, MapPinned, Sparkles, Stethoscope,
} from 'lucide-react'
import { SOURCE_LABELS, askChat } from '../api.js'
import { useRegion } from '../region.jsx'

const EXAMPLES = [
  { icon: HeartPulse, tone: 'blue', title: '어르신 의료 혜택', query: '65세 이상 받을 수 있는 의료 혜택 뭐 있어?' },
  { icon: Brain, tone: 'pink', title: '치매 지원', query: '치매 검사 무료로 받는 곳 알려줘' },
  { icon: Baby, tone: 'mint', title: '임신·출산', query: '임산부가 받을 수 있는 의료 지원은?' },
  { icon: Stethoscope, tone: 'blue', title: '법·제도', query: '고혈압 관련 법 제도 알려줘' },
]

const RECENT_KEY = 'health-agent:recent-questions'

function loadRecent() {
  try {
    return JSON.parse(localStorage.getItem(RECENT_KEY)) ?? []
  } catch {
    return []
  }
}

function saveRecent(list) {
  try {
    localStorage.setItem(RECENT_KEY, JSON.stringify(list))
  } catch {
    // 저장 불가 환경이면 무시
  }
}

/** 인용 출처 한 건의 보조 설명 (근거법령 > 소관부처 > 출처 종류) */
const sourceNote = (s) => s.metadata?.근거법령 || s.metadata?.소관부처 || s.metadata?.주소 || ''

export default function ChatPage() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [recent, setRecent] = useState(loadRecent)
  const endRef = useRef(null)
  const { label: regionLabel, shortLabel } = useRegion()
  const [params, setParams] = useSearchParams()
  const navigate = useNavigate()

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, loading])

  const send = useCallback(async (query) => {
    if (!query.trim() || loading) return
    setMessages((m) => [...m, { role: 'user', text: query }])
    setInput('')
    setLoading(true)
    setRecent((prev) => {
      const next = [query, ...prev.filter((q) => q !== query)].slice(0, 5)
      saveRecent(next)
      return next
    })
    try {
      const res = await askChat(query, regionLabel)
      setMessages((m) => [...m, { role: 'bot', text: res.answer, sources: res.sources, mock: res.mock }])
    } catch (e) {
      setMessages((m) => [...m, { role: 'bot', text: `오류가 발생했어요: ${e.message}`, sources: [] }])
    } finally {
      setLoading(false)
    }
  }, [loading, regionLabel])

  // 기관 상세 화면의 "챗봇에 물어보기"로 들어온 질문을 바로 보낸다
  const handledQuery = useRef(null)
  useEffect(() => {
    const q = params.get('q')
    if (q && regionLabel && handledQuery.current !== q) {
      handledQuery.current = q
      setParams({}, { replace: true })
      send(q)
    }
  }, [params, regionLabel, send, setParams])

  const empty = messages.length === 0
  const lastSources = [...messages].reverse().find((m) => m.role === 'bot')?.sources ?? []

  return (
    <div className={`chat-layout ${empty ? '' : 'has-thread'}`}>
      <section className={`chat ${empty ? 'is-empty' : ''}`}>
        {empty ? (
          <div className="welcome">
            <span className="eyebrow"><Sparkles size={14} /> 공공데이터 기반 RAG</span>
            <h1>무엇이든 물어보세요.<br />근거와 출처까지 찾아드릴게요.</h1>
            <p>{shortLabel ? `${regionLabel} 기준으로 ` : ''}복지 혜택, 신청 방법, 관련 법령, 의료기관 정보를 안내해요.</p>
            <div className="prompt-grid">
              {EXAMPLES.map(({ icon: Icon, tone, title, query }) => (
                <button key={title} className="prompt-card glass" onClick={() => send(query)}>
                  <span className={`icon-tile ${tone}`}><Icon size={20} strokeWidth={1.8} /></span>
                  <strong>{title}</strong>
                  <span>{query}</span>
                </button>
              ))}
            </div>
            {recent.length > 0 && (
              <div className="recent">
                <h2><History size={15} strokeWidth={1.8} />최근 질문</h2>
                <ul>
                  {recent.map((q) => (
                    <li key={q}><button onClick={() => send(q)}>{q}<ArrowRight size={15} /></button></li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ) : (
          <div className="thread">
            {messages.map((m, i) => (
              <div key={i} className={`msg ${m.role}`}>
                {m.role === 'bot' && <span className="avatar"><Sparkles size={16} /></span>}
                <div className={`bubble ${m.role === 'bot' ? 'glass' : ''}`}>
                  {m.role === 'bot' && (
                    <div className="answer-meta">
                      {m.mock && <span className="tag pink">샘플 응답</span>}
                      <span>에이전트 답변 · 근거 {m.sources?.length ?? 0}건</span>
                    </div>
                  )}
                  <p>{m.text}</p>
                  {m.sources?.length > 0 && (
                    <div className="sources">
                      {m.sources.map((s, j) => (
                        <span key={j} className="source-pill"><b>{j + 1}</b><FileText size={13} />{s.title}</span>
                      ))}
                    </div>
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
                <span className="avatar"><Sparkles size={16} /></span>
                <div className="bubble glass typing"><i /><i /><i /></div>
              </div>
            )}
            <div ref={endRef} />
          </div>
        )}

        <form className="composer glass" onSubmit={(e) => { e.preventDefault(); send(input) }}>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="건강 혜택, 법 제도, 기관을 물어보세요"
            aria-label="질문 입력"
          />
          <button className="send" disabled={loading || !input.trim()} aria-label="보내기">
            <ArrowUp size={20} strokeWidth={2.2} />
          </button>
        </form>
      </section>

      {!empty && (
        <aside className="citations glass">
          <header>
            <h2>인용 출처</h2>
            <span>답변에 실제 쓰인 문서</span>
          </header>
          {lastSources.length === 0 && <p className="empty small">인용된 출처가 없어요.</p>}
          <ol>
            {lastSources.map((s, j) => (
              <li key={j}>
                <span className="cite-kind"><b>{j + 1}</b>{SOURCE_LABELS[s.source] ?? s.source}</span>
                <strong>{s.title}</strong>
                {sourceNote(s) && <small>{sourceNote(s)}</small>}
              </li>
            ))}
          </ol>
          <footer>BGE-M3 + BM25 하이브리드 검색</footer>
        </aside>
      )}
    </div>
  )
}
