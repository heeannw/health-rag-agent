import { useEffect, useState } from 'react'

const REDUCE_QUERY = '(prefers-reduced-motion: reduce)'

/** OS/브라우저의 '동작 줄이기' 설정을 따른다. */
export function usePrefersReducedMotion() {
  const [reduced, setReduced] = useState(() => window.matchMedia(REDUCE_QUERY).matches)
  useEffect(() => {
    const mq = window.matchMedia(REDUCE_QUERY)
    const onChange = () => setReduced(mq.matches)
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])
  return reduced
}

/** 탭이 안 보일 때 그래픽 애니메이션을 멈추기 위해 쓴다. */
export function useTabVisible() {
  const [visible, setVisible] = useState(!document.hidden)
  useEffect(() => {
    const onChange = () => setVisible(!document.hidden)
    document.addEventListener('visibilitychange', onChange)
    return () => document.removeEventListener('visibilitychange', onChange)
  }, [])
  return visible
}

/** 동작 줄이기 설정이 없고 탭이 보일 때만 true */
export function useShouldAnimate() {
  const reduced = usePrefersReducedMotion()
  const visible = useTabVisible()
  return !reduced && visible
}
