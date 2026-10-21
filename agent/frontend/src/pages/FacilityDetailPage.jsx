import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  ArrowLeft, ArrowRight, Gift, Info, ListChecks, MapPin, MessageCircleHeart, Navigation, Phone,
} from 'lucide-react'
import KakaoMap from '../components/KakaoMap.jsx'
import { getBenefits, getFacility } from '../api.js'
import { FACILITY_META } from '../facilityTypes.js'
import { useRegion } from '../region.jsx'

export default function FacilityDetailPage() {
  const { id } = useParams()
  const { region } = useRegion()
  const navigate = useNavigate()
  const [facility, setFacility] = useState(null)
  const [benefits, setBenefits] = useState([])
  const [error, setError] = useState(null)

  useEffect(() => {
    getFacility(id, region ? { lat: region.lat, lng: region.lng } : {})
      .then((f) => {
        setFacility(f)
        // 기관 지역에서 받을 수 있는 혜택 중 이 기관 유형과 연결된 것 우선
        // (기관-혜택 직접 매핑은 가은 데이터 확정 후 교체)
        return getBenefits({ province: f.province, municipality: f.municipality }).then((list) => {
          const linked = list.filter((b) => b.related_facility_type === f.type)
          return linked.length ? linked : list
        })
      })
      .then(setBenefits)
      .catch((e) => setError(e.message))
  }, [id, region])

  const markers = useMemo(() => (facility ? [facility] : []), [facility])

  if (error) return <section className="page"><p className="error">{error}</p></section>
  if (!facility) return <section className="page"><p className="empty">불러오는 중…</p></section>

  const meta = FACILITY_META[facility.type]
  const Icon = meta?.icon
  const directions = facility.lat
    ? `https://map.kakao.com/link/to/${encodeURIComponent(facility.name)},${facility.lat},${facility.lng}`
    : null

  return (
    <section className="page">
      <Link to="/map" className="back"><ArrowLeft size={18} />지도로</Link>

      <div className="detail-hero glass">
        <span className={`icon-tile lg ${meta?.tone}`}>{Icon && <Icon size={28} strokeWidth={1.6} />}</span>
        <div className="detail-hero-text">
          <span className="eyebrow">{meta?.label}</span>
          <h1>{facility.name}</h1>
          <p>
            {facility.address}
            {facility.distance_km != null && <> · 내 지역에서 {facility.distance_km}km</>}
          </p>
        </div>
        <div className="detail-actions">
          {directions && (
            <a className="btn primary" href={directions} target="_blank" rel="noreferrer">
              <Navigation size={16} />길찾기
            </a>
          )}
          {facility.phone
            ? <a className="btn" href={`tel:${facility.phone}`}><Phone size={16} />{facility.phone}</a>
            : <span className="btn disabled"><Phone size={16} />전화번호 없음</span>}
        </div>
      </div>

      {facility.stats.length > 0 && (
        <div className="stat-row">
          {facility.stats.map((s) => (
            <div key={s.label} className="stat glass">
              <span>{s.label}</span>
              <strong>{s.value}</strong>
            </div>
          ))}
          {facility.details.운영시간 && (
            <div className="stat glass mint">
              <span>운영시간</span>
              <strong>{facility.details.운영시간}</strong>
            </div>
          )}
        </div>
      )}

      <div className="detail-grid">
        <ul className="info-list glass">
          <li><MapPin size={18} strokeWidth={1.8} /><span>주소</span><strong>{facility.address ?? '-'}</strong></li>
          <li><Phone size={18} strokeWidth={1.8} /><span>전화</span><strong>{facility.phone ?? '-'}</strong></li>
          {Object.entries(facility.details).map(([k, v]) => (
            <li key={k}><Info size={18} strokeWidth={1.8} /><span>{k}</span><strong>{String(v)}</strong></li>
          ))}
          {facility.grades.length > 0 && (
            <li>
              <Info size={18} strokeWidth={1.8} /><span>평가등급</span>
              <strong className="grades">{facility.grades.map((g) => <span key={g} className="tag blue">{g}</span>)}</strong>
            </li>
          )}
        </ul>
        <div className="detail-map glass">
          <KakaoMap markers={markers} center={facility} />
        </div>
      </div>

      <div className="detail-columns">
        <div>
          <h2 className="section-title"><ListChecks size={20} strokeWidth={1.8} />제공 서비스</h2>
          {facility.services.length > 0 ? (
            <ul className="service-list glass">
              {facility.services.map((s) => (
                <li key={s.name}><span>{s.name}</span><strong>{s.cost}</strong></li>
              ))}
            </ul>
          ) : (
            <p className="empty small">등록된 서비스 정보가 아직 없어요.</p>
          )}
        </div>
        <div>
          <h2 className="section-title"><Gift size={20} strokeWidth={1.8} />이 기관과 연계된 혜택</h2>
          <ul className="linked-list">
            {benefits.map((b) => (
              <li key={b.id}>
                <Link className="linked glass" to="/benefits">
                  <span><strong>{b.name}</strong><small>{b.criteria_text}</small></span>
                  <ArrowRight size={18} />
                </Link>
              </li>
            ))}
            <li>
              <button
                className="linked ask"
                onClick={() => navigate(`/?q=${encodeURIComponent(`${facility.name}에서 받을 수 있는 서비스 알려줘`)}`)}
              >
                <span><strong><MessageCircleHeart size={16} />챗봇에 이 기관 물어보기</strong><small>근거 출처와 함께 답변해요</small></span>
                <ArrowRight size={18} />
              </button>
            </li>
          </ul>
        </div>
      </div>

      {facility.data_source && <p className="data-source">출처: {facility.data_source}</p>}
    </section>
  )
}
