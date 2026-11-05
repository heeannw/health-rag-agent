import {
  Baby, Briefcase, FileDown, GraduationCap, HeartPulse, School, Smile, Sparkle, Users,
} from 'lucide-react'

// 가은 데이터 life_cycle_names 원문 분류명 (복지로 생애주기)
export const LIFE_CYCLES = [
  { value: '', label: '전체', icon: Sparkle },
  { value: '영유아', label: '영유아', icon: Baby },
  { value: '아동', label: '아동', icon: Smile },
  { value: '청소년', label: '청소년', icon: School },
  { value: '청년', label: '청년', icon: GraduationCap },
  { value: '중장년', label: '중장년', icon: Briefcase },
  { value: '노년', label: '노년', icon: Users },
  { value: '임신·출산', label: '임신·출산', icon: HeartPulse },
]

export const STATUS = {
  open: { label: '신청 가능', tone: 'mint' },
  scheduled: { label: '신청 예정', tone: 'blue' },
  closed: { label: '마감', tone: 'pink' },
  unknown: { label: '기간 확인', tone: 'gray' },
}

// search_benefits가 원문 확인으로 분리한 조건 이름
export const REVIEW_LABELS = { life_cycle_names: '생애주기', target_group_names: '대상특성', region: '지역' }

export const iconFor = (b) => LIFE_CYCLES.find((c) => c.value && b.life_cycle_names?.includes(c.value))?.icon ?? HeartPulse

// 둘 다 원문 미확인이면 '대상 원문 확인 · 대상 원문 확인'처럼 반복되지 않게 한 번만
export const audienceOf = (b) => [...new Set([b.display.life_cycle, b.display.target_group])].join(' · ')

export const periodOf = (b) =>
  b.application_start_date || b.application_deadline
    ? `${b.application_start_date ?? ''} ~ ${b.application_deadline ?? ''}`
    : null

/** 혜택 상세 페이지 경로. 새로고침해도 다시 찾을 수 있게 혜택의 지역을 쿼리로 같이 넘긴다 */
export const benefitPath = (b, region) => {
  const params = new URLSearchParams()
  if (region?.province) params.set('province', region.province)
  if (region?.municipality) params.set('municipality', region.municipality)
  const q = params.toString()
  return `/benefits/${encodeURIComponent(b.id)}${q ? `?${q}` : ''}`
}

// 신청 서식은 복지로 첨부파일 링크. http(s) 링크만 걸고 나머지는 이름만 보여준다
export function FormLink({ form }) {
  const safe = /^https?:\/\//.test(form.link ?? '')
  return safe
    ? <a href={form.link} target="_blank" rel="noreferrer"><FileDown size={13} />{form.name}</a>
    : <span>{form.name}</span>
}
