import { useState } from 'react'
import { useLocation } from 'react-router-dom'
import { CheckSquare, LoaderCircle, MessageSquare, Trash2, X } from 'lucide-react'
import { groupByDate, useChatHistory } from '../chatHistory.jsx'

/**
 * 챗봇 대화 기록 목록. 데스크톱은 왼쪽 사이드바, 모바일은 챗봇 화면의 서랍에 들어간다.
 * 챗봇 메뉴(/)가 열려 있을 때만 보인다. 새 대화는 '챗봇' 메뉴를 누르면 시작된다.
 * - 항목 클릭: 그 대화를 열고 이어서 질문
 * - 휴지통: 한 건 삭제 / '선택': 여러 건 골라 삭제
 */
export default function ConversationList({ onNavigate }) {
  const { conversations, activeId, open, remove, pending } = useChatHistory()
  const [selecting, setSelecting] = useState(false)
  const [selected, setSelected] = useState(() => new Set())
  const { pathname } = useLocation()

  const toggle = (id) =>
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })

  const exitSelect = () => { setSelecting(false); setSelected(new Set()) }

  const deleteOne = (c) => {
    if (window.confirm(`'${c.title}' 대화를 삭제할까요?`)) remove([c.id])
  }

  const deleteSelected = () => {
    if (!selected.size) return
    if (window.confirm(`선택한 대화 ${selected.size}개를 삭제할까요?`)) {
      remove([...selected])
      exitSelect()
    }
  }

  if (pathname !== '/') return null

  const allSelected = conversations.length > 0 && selected.size === conversations.length

  return (
    <div className="history">
      <div className="history-head">
        <span>대화 기록</span>
        {conversations.length > 0 && (
          selecting ? (
            <button onClick={exitSelect}><X size={14} />취소</button>
          ) : (
            <button onClick={() => setSelecting(true)}><CheckSquare size={14} />선택</button>
          )
        )}
      </div>

      {selecting && (
        <div className="history-bulk">
          <label>
            <input
              type="checkbox"
              checked={allSelected}
              onChange={() => setSelected(allSelected ? new Set() : new Set(conversations.map((c) => c.id)))}
            />
            전체 선택
          </label>
          <button className="danger" disabled={!selected.size} onClick={deleteSelected}>
            <Trash2 size={14} />삭제{selected.size ? ` ${selected.size}` : ''}
          </button>
        </div>
      )}

      <div className="history-scroll">
        {conversations.length === 0 && <p className="history-empty">아직 저장된 대화가 없어요.</p>}
        {groupByDate(conversations).map(({ label, items }) => (
          <section key={label}>
            <h3>{label}</h3>
            <ul>
              {items.map((c) => {
                const isActive = c.id === activeId
                return (
                  <li key={c.id} className={`${isActive ? 'active' : ''} ${selected.has(c.id) ? 'checked' : ''}`}>
                    {selecting ? (
                      <label className="history-item">
                        <input type="checkbox" checked={selected.has(c.id)} onChange={() => toggle(c.id)} />
                        <span>{c.title}</span>
                      </label>
                    ) : (
                      <>
                        <button
                          className="history-item"
                          onClick={() => { open(c.id); onNavigate?.() }}
                          aria-current={isActive ? 'page' : undefined}
                          title={c.title}
                        >
                          {pending.has(c.id)
                            ? <LoaderCircle size={15} className="spin" />
                            : <MessageSquare size={15} strokeWidth={1.8} />}
                          <span>{c.title}</span>
                        </button>
                        <button className="history-del" onClick={() => deleteOne(c)} aria-label={`'${c.title}' 대화 삭제`}>
                          <Trash2 size={14} />
                        </button>
                      </>
                    )}
                  </li>
                )
              })}
            </ul>
          </section>
        ))}
      </div>
    </div>
  )
}
