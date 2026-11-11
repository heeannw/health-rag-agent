import {
  Baby, Brain, Briefcase, GraduationCap, HeartPulse, School, Smile, Sparkle, Users,
} from 'lucide-react'

// life_cycle_names 원문 분류명
export const LIFE_CYCLES = [
  { value: '', label: '전체', icon: Sparkle },
  { value: '영유아', label: '영유아', icon: Baby },
  { value: '아동', label: '아동', icon: Smile },
  { value: '청소년', label: '청소년', icon: School },
  { value: '청년', label: '청년', icon: GraduationCap },
  { value: '중장년', label: '중장년', icon: Briefcase },
  { value: '노년', label: '노년', icon: Users },
  // DB 원문은 가운뎃점 앞뒤에 공백
  { value: '임신 · 출산', label: '임신·출산', icon: HeartPulse },
]

// theme_codes (DB에는 의료 관련 3개 주제만). tone은 칩·아이콘 타일 색
export const THEMES = [
  { code: '010', label: '신체건강', icon: HeartPulse, tone: 'pink' },
  { code: '020', label: '정신건강', icon: Brain, tone: 'violet' },
  { code: '080', label: '임신·출산', icon: Baby, tone: 'mint' },
]

export const STATUS = {
  open: { label: '신청 가능', tone: 'mint' },
  scheduled: { label: '신청 예정', tone: 'blue' },
  closed: { label: '마감', tone: 'pink' },
  unknown: { label: '기간 확인', tone: 'gray' },
}

// review_fields 표시 이름
export const REVIEW_LABELS = { life_cycle_names: '생애주기', target_group_names: '대상특성', region: '지역' }

// 분야별 아이콘·색 (여러 개면 THEMES 순서로 앞의 것, 없으면 회색 하트)
const themeOf = (b) => THEMES.find((t) => b.theme_codes?.includes(t.code))
export const iconFor = (b) => themeOf(b)?.icon ?? HeartPulse
export const toneFor = (b) => themeOf(b)?.tone ?? 'gray'

// 제공 지역을 모르는 혜택은 위치를 숨긴다
export const hasRegion = (b) => b.region_scope !== 'unknown' && Boolean(b.display?.region)

export const periodOf = (b) =>
  b.application_start_date || b.application_deadline
    ? `${b.application_start_date ?? ''} ~ ${b.application_deadline ?? ''}`
    : null

/** 혜택 상세 경로 (새로고침해도 찾도록 지역을 쿼리로) */
export const benefitPath = (b, region) => {
  const params = new URLSearchParams()
  if (region?.province) params.set('province', region.province)
  if (region?.municipality) params.set('municipality', region.municipality)
  const q = params.toString()
  return `/benefits/${encodeURIComponent(b.id)}${q ? `?${q}` : ''}`
}
