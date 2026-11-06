import { Brain, Building2, HeartHandshake, Hospital } from 'lucide-react'

// tone은 목록 아이콘·필터 버튼·지도 핀이 같이 쓰는 색 이름 (index.css의 .blue/.mint/.pink/.violet)
export const FACILITY_META = {
  hospital: { label: '병원', icon: Hospital, tone: 'blue' },
  public_health_center: { label: '보건소', icon: Building2, tone: 'mint' },
  dementia_center: { label: '치매안심센터', icon: Brain, tone: 'pink' },
  ltc_institution: { label: '장기요양기관', icon: HeartHandshake, tone: 'violet' },
}
