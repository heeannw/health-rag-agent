import {
  Baby, Brain, Briefcase, GraduationCap, HeartPulse, School, Smile, Sparkle, Users,
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
  // DB 원문 표기는 가운뎃점 앞뒤에 공백이 있다 ('임신 · 출산')
  { value: '임신 · 출산', label: '임신·출산', icon: HeartPulse },
]

// 가은 데이터의 theme_codes (의료 관련 3개 주제만 DB에 있다).
// tone은 분야 칩을 골랐을 때 색이자 혜택 목록·상세 아이콘 타일 색 (index.css .toggle.on.* / .icon-tile.*)
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

// search_benefits가 원문 확인으로 분리한 조건 이름
export const REVIEW_LABELS = { life_cycle_names: '생애주기', target_group_names: '대상특성', region: '지역' }

// 혜택의 분야로 아이콘·색을 고른다. 분야가 여러 개면 THEMES 순서(신체건강 → 정신건강 → 임신·출산)로 앞의 것.
// DB상 분야 없는 혜택은 없지만, 혹시 없으면 회색 하트
const themeOf = (b) => THEMES.find((t) => b.theme_codes?.includes(t.code))
export const iconFor = (b) => themeOf(b)?.icon ?? HeartPulse
export const toneFor = (b) => themeOf(b)?.tone ?? 'gray'

// 둘 다 원문 미확인이면 '대상 원문 확인 · 대상 원문 확인'처럼 반복되지 않게 한 번만
export const audienceOf = (b) => [...new Set([b.display.life_cycle, b.display.target_group])].join(' · ')

// 제공 지역을 알 수 없는 혜택(search_benefits의 region_scope가 unknown)은 위치를 보여주지 않는다
export const hasRegion = (b) => b.region_scope !== 'unknown' && Boolean(b.display?.region)

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
