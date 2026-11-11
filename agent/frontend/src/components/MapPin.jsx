import { MapPin as PinIcon } from 'lucide-react'
import { FACILITY_META } from '../facilityTypes.js'

/** 지도 기관 핀 (마우스를 올리면 정보 카드) */
export default function MapPin({ facility }) {
  const meta = FACILITY_META[facility.type]
  const Icon = meta?.icon ?? PinIcon
  const tone = meta?.tone ?? 'blue'
  // 가장 좋은 평가등급 하나만
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
