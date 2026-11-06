import { createContext, useContext } from 'react'

/** 챗봇 대화 기록 컨텍스트. Provider는 chatHistory.jsx */
export const ChatHistoryContext = createContext(null)

export function useChatHistory() {
  const ctx = useContext(ChatHistoryContext)
  if (!ctx) throw new Error('useChatHistory는 ChatHistoryProvider 안에서만 쓸 수 있어요')
  return ctx
}

/** 사이드바 묶음 이름: 오늘 / 어제 / 지난 7일 / 지난 30일 / 그 이전 */
export function groupByDate(conversations, now = new Date()) {
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime()
  const day = 24 * 60 * 60 * 1000
  const buckets = [
    ['오늘', startOfToday],
    ['어제', startOfToday - day],
    ['지난 7일', startOfToday - 7 * day],
    ['지난 30일', startOfToday - 30 * day],
    ['그 이전', -Infinity],
  ]
  const groups = []
  for (const c of conversations) {
    const [label] = buckets.find(([, from]) => c.updatedAt >= from)
    const last = groups[groups.length - 1]
    if (last?.label === label) last.items.push(c)
    else groups.push({ label, items: [c] })
  }
  return groups
}
