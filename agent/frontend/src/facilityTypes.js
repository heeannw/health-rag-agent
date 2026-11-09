import { Building2, HeartHandshake, Hospital, Pill } from 'lucide-react'

// tone은 목록 아이콘·필터 버튼·지도 핀이 같이 쓰는 색 이름 (index.css의 .blue/.mint/.pink/.violet)
export const FACILITY_META = {
  hospital: { label: '병원', icon: Hospital, tone: 'blue' },
  public_health_center: { label: '보건소', icon: Building2, tone: 'mint' },
  // 약국은 공공데이터가 없어서 카카오 장소 검색으로만 나온다
  pharmacy: { label: '약국', icon: Pill, tone: 'pink' },
  ltc_institution: { label: '장기요양기관', icon: HeartHandshake, tone: 'violet' },
}
