import { Building2, HeartHandshake, Hospital, Pill } from 'lucide-react'

// tone: 아이콘·필터·지도 핀 공용 색 이름
export const FACILITY_META = {
  hospital: { label: '병원', icon: Hospital, tone: 'blue' },
  public_health_center: { label: '보건소', icon: Building2, tone: 'mint' },
  // 약국은 카카오 장소 검색으로만
  pharmacy: { label: '약국', icon: Pill, tone: 'pink' },
  ltc_institution: { label: '장기요양기관', icon: HeartHandshake, tone: 'violet' },
}
