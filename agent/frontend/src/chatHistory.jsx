import { useCallback, useEffect, useMemo, useState } from 'react'
import { ChatHistoryContext } from './chatHistoryContext.js'

/**
 * 챗봇 대화 기록. 로그인이 없어서 이 브라우저(localStorage)에만 저장한다.
 * 한 대화 = { id, title, createdAt, updatedAt, messages: [{ role, text, sources? }] }
 */
const STORAGE_KEY = 'health-agent:conversations:v1'
const MAX_CONVERSATIONS = 100

function load() {
  try {
    const list = JSON.parse(localStorage.getItem(STORAGE_KEY))
    return Array.isArray(list) ? list : []
  } catch {
    return []
  }
}

function persist(list) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(list))
  } catch {
    // 저장이 막힌 환경(시크릿 창 등)이면 이번 방문 동안만 유지
  }
}

const newId = () =>
  globalThis.crypto?.randomUUID?.() ?? `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`

const titleOf = (text) => {
  const t = text.replace(/\s+/g, ' ').trim()
  return t.length > 40 ? `${t.slice(0, 40)}…` : t
}

export function ChatHistoryProvider({ children }) {
  const [conversations, setConversations] = useState(load)
  const [activeId, setActiveId] = useState(null) // null = 새 대화(아직 저장 전)
  const [pending, setPending] = useState(() => new Set()) // 답변을 기다리는 대화 id

  useEffect(() => persist(conversations), [conversations])

  // 다른 탭에서 바꾼 기록도 반영
  useEffect(() => {
    const onStorage = (e) => { if (e.key === STORAGE_KEY) setConversations(load()) }
    window.addEventListener('storage', onStorage)
    return () => window.removeEventListener('storage', onStorage)
  }, [])

  /** 대화를 새로 만들고 id를 돌려준다. 첫 질문이 제목이 된다. */
  const create = useCallback((firstQuestion) => {
    const now = Date.now()
    const conv = { id: newId(), title: titleOf(firstQuestion), createdAt: now, updatedAt: now, messages: [] }
    setConversations((list) => [conv, ...list].slice(0, MAX_CONVERSATIONS))
    setActiveId(conv.id)
    return conv.id
  }, [])

  /** 해당 대화 끝에 메시지를 붙인다. 답변이 늦게 와도 보낸 대화에 들어간다. */
  const append = useCallback((id, message) => {
    setConversations((list) =>
      list.map((c) => (c.id === id ? { ...c, messages: [...c.messages, message], updatedAt: Date.now() } : c)),
    )
  }, [])

  const remove = useCallback((ids) => {
    const drop = new Set(ids)
    setConversations((list) => list.filter((c) => !drop.has(c.id)))
    setActiveId((cur) => (drop.has(cur) ? null : cur))
  }, [])

  const setPendingFor = useCallback((id, on) => {
    setPending((prev) => {
      const next = new Set(prev)
      if (on) next.add(id)
      else next.delete(id)
      return next
    })
  }, [])

  const startNew = useCallback(() => setActiveId(null), [])

  const value = useMemo(() => {
    const sorted = [...conversations].sort((a, b) => b.updatedAt - a.updatedAt)
    return {
      conversations: sorted,
      active: conversations.find((c) => c.id === activeId) ?? null,
      activeId,
      open: setActiveId,
      startNew,
      create,
      append,
      remove,
      pending,
      setPendingFor,
    }
  }, [conversations, activeId, startNew, create, append, remove, pending, setPendingFor])

  return <ChatHistoryContext.Provider value={value}>{children}</ChatHistoryContext.Provider>
}
