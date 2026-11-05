import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  ArrowUp, Baby, Brain, FileText, Gift, HeartPulse, History, MapPinned, Sparkles, Stethoscope, X,
} from 'lucide-react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { SOURCE_LABELS, askChat } from '../api.js'
import { useRegion } from '../region.jsx'
import { useChatHistory } from '../chatHistory.jsx'
import ConversationList from '../components/ConversationList.jsx'

const NO_MESSAGES = []

const EXAMPLES = [
  { icon: HeartPulse, tone: 'blue', title: '어르신 의료 혜택', query: '65세 이상 받을 수 있는 의료 혜택 뭐 있어?' },
  { icon: Brain, tone: 'pink', title: '치매 지원', query: '치매 검사 무료로 받는 곳 알려줘' },
  { icon: Baby, tone: 'mint', title: '임신·출산', query: '임산부가 받을 수 있는 의료 지원은?' },
  { icon: Stethoscope, tone: 'blue', title: '법·제도', query: '고혈압 관련 법 제도 알려줘' },
]

/** 인용 출처 한 건의 보조 설명 (근거법령 > 소관부처 > 출처 종류) */
const sourceNote = (s) => s.metadata?.근거법령 || s.metadata?.소관부처 || s.metadata?.주소 || ''

/** LLM 답변 끝의 '[출처]' 목록은 아래 출처 칩·인용 패널과 겹쳐서 뗀다 */
const stripSourceList = (text) => text.replace(/\n+(-{3,}\s*\n+)?\[출처\][\s\S]*$/, '').trim()

/** 저장된 메시지 → API에 보낼 이전 대화 (최근 10개, 오류 답변 제외) */
const toHistory = (messages) =>
  messages
    .filter((m) => !m.error)
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

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, loading])

  // 챗봇 화면에 들어오면 이전 대화 대신 항상 새 대화로 시작
  useEffect(() => { startNew() }, [startNew])

  // 다른 대화를 열면 맨 아래(최근 메시지)로
  useEffect(() => {
    endRef.current?.scrollIntoView({ block: 'end' })
  }, [active?.id])

  const send = useCallback(async (query, { fresh = false } = {}) => {
    if (!query.trim() || (loading && !fresh)) return
    // 열린 대화가 있으면 그 대화에 이어서, 없거나 fresh면 새 대화로 저장
    const continuing = active && !fresh
    const id = continuing ? active.id : create(query)
    // 이전 대화를 같이 보내야 "신청은 어떻게 해?" 같은 후속 질문을 이해한다. 오류 답변은 뺀다
    const history = continuing ? toHistory(active.messages) : []
    append(id, { role: 'user', text: query })
    setInput('')
    setPendingFor(id, true)
    try {
      const res = await askChat(query, regionLabel, history)
      append(id, { role: 'bot', text: res.answer, sources: res.sources })
    } catch (e) {
      append(id, { role: 'bot', text: `오류가 발생했어요: ${e.message}`, sources: [], error: true })
    } finally {
      setPendingFor(id, false)
    }
  }, [loading, active, create, append, setPendingFor, regionLabel])
  const sendRef = useRef(send)
  useEffect(() => { sendRef.current = send }, [send])

  // 기관 상세 화면의 "챗봇에 물어보기"로 들어온 질문을 바로 보낸다
  const handledQuery = useRef(null)
  useEffect(() => {
    const q = params.get('q')
    if (q && regionLabel && handledQuery.current !== q) {
      handledQuery.current = q
      setParams({}, { replace: true })
      startNew()
      sendRef.current(q, { fresh: true })
    }
  }, [params, regionLabel, setParams, startNew])

  const empty = messages.length === 0
  const lastSources = [...messages].reverse().find((m) => m.role === 'bot')?.sources ?? []

  return (
    <div className={`chat-layout ${empty ? '' : 'has-thread'}`}>
      <section className={`chat ${empty ? 'is-empty' : ''}`}>
        {/* 모바일: 사이드바가 없어서 대화 기록을 서랍으로 연다 */}
        <div className="chat-topbar">
          <button onClick={() => setDrawerOpen(true)}><History size={17} />대화 기록</button>
        </div>
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
          </div>
        ) : (
          <div className="thread">
            {messages.map((m, i) => (
              <div key={i} className={`msg ${m.role}`}>
                {m.role === 'bot' && <span className="avatar"><Sparkles size={16} /></span>}
                <div className={`bubble ${m.role === 'bot' ? 'glass' : ''}`}>
                  {m.role === 'bot' && (
                    <div className="answer-meta">
                      <span>에이전트 답변 · 근거 {m.sources?.length ?? 0}건</span>
                    </div>
                  )}
                  {m.role === 'bot' ? (
                    // 답변은 마크다운(굵게·목록·제목). 원문 HTML은 렌더링하지 않는다(react-markdown 기본값)
                    <div className="markdown"><Markdown remarkPlugins={[remarkGfm]}>{stripSourceList(m.text)}</Markdown></div>
                  ) : (
                    <p>{m.text}</p>
                  )}
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
