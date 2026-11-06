import { MapPin as PinIcon } from 'lucide-react'
import { FACILITY_META } from '../facilityTypes.js'

/** 지도 위 기관 핀. 유형 색으로 칠하고, 마우스를 올리면 위에 간단한 정보 카드가 뜬다 */
export default function MapPin({ facility }) {
  const meta = FACILITY_META[facility.type]
  const Icon = meta?.icon ?? PinIcon
  const tone = meta?.tone ?? 'blue'
  // 병원 평가등급은 여러 개라 가장 좋은 등급 하나만
  const gradeNo = (g) => Number(g.match(/(\d+)\s*등급/)?.[1] ?? 99)
  const grade = [...(facility.grades ?? [])].sort((a, b) => gradeNo(a) - gradeNo(b))[0]
  const extra = [facility.distance_km != null && `${facility.distance_km}km`, grade].filter(Boolean)

  return (
    <div className={`map-pin ${tone}`}>
      <div className="map-pin-card" role="tooltip">
        <span className={`tag ${tone}`}>{meta?.label ?? '기관'}</span>
        <strong>{facility.name}</strong>
        {facility.summary && <small>{facility.summary}</small>}
        {extra.length > 0 && <span className="map-pin-extra">{extra.join(' · ')}</span>}
      </div>
      <span className="map-pin-head" aria-label={facility.name}>
        <Icon size={16} strokeWidth={2} />
      </span>
    </div>
  )
}
