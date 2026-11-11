import { useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import {
  ArrowLeft, ArrowRight, ChevronDown, ChevronUp, Gift, Info, ListChecks, MapPin, MessageCircleHeart,
  Navigation, Phone,
} from 'lucide-react'
import KakaoMap from '../components/KakaoMap.jsx'
import { getBenefits, getFacility } from '../api.js'
import { FACILITY_META } from '../facilityTypes.js'
import { regionFromCoords } from '../kakao.js'
import { getPlace, isKakaoPlace } from '../placeCache.js'
import { useRegion } from '../regionContext.js'
import { benefitPath } from '../benefitMeta.js'

// 연계 혜택 '더보기' 단위
const PAGE = 5

/** 카카오 장소는 넘겨받거나 보관한 정보로 열고, 좌표로 시도·시군구를 채운다 */
async function loadKakaoPlace(id, passed) {
  const place = passed ?? getPlace(id)
  if (!place) throw new Error('카카오 장소 정보는 지도에서 기관을 다시 눌러 열어 주세요.')
  const area = await regionFromCoords(place.lat, place.lng).catch(() => ({}))
  return {
    stats: [], services: [], grades: [],
    ...place,
    province: place.province ?? area.province ?? null,
    municipality: place.municipality ?? area.municipality ?? null,
    details: place.summary ? { 업종: place.summary } : {},
  }
}

// 기관 지역 혜택 중 이 기관 유형과 관련된 것만 (related_facility_types는 키워드 추정). 약국은 제외
const NO_BENEFIT_TYPES = ['pharmacy']

async function linkedBenefits(f) {
  if (!f.province || NO_BENEFIT_TYPES.includes(f.type)) return []
  const { matched, needs_review } = await getBenefits({ province: f.province, municipality: f.municipality })
  return [...matched, ...needs_review]
    .filter((b) => b.related_facility_types?.includes(f.type))
}

export default function FacilityDetailPage() {
  const { id } = useParams()
  const passed = useLocation().state?.facility
  const { region } = useRegion()
  const navigate = useNavigate()
  const [facility, setFacility] = useState(null)
  const [benefits, setBenefits] = useState([])
  const [error, setError] = useState(null)
  const kakao = isKakaoPlace(id)
  const [shown, setShown] = useState(PAGE)

  useEffect(() => {
    let cancelled = false
    setFacility(null)
    setBenefits([])
    setShown(PAGE)
    setError(null)
    const load = kakao
      ? loadKakaoPlace(id, passed)
      : getFacility(id, region ? { lat: region.lat, lng: region.lng } : {})
    load
      .then((f) => {
        if (cancelled) return []
        setFacility(f)
        // 혜택 DB가 안 돼도 기관 정보는 보여준다
        return linkedBenefits(f).catch(() => [])
      })
      .then((list) => !cancelled && setBenefits(list))
      .catch((e) => !cancelled && setError(e.message))
    return () => {
      cancelled = true
    }
  }, [id, region, kakao, passed])

  const markers = useMemo(() => (facility ? [facility] : []), [facility])

  if (error) {
    return (
      <section className="page page-full">
        <Link to="/map" className="back"><ArrowLeft size={18} />지도로</Link>
        <p className="error">{error}</p>
      </section>
    )
  }
  if (!facility) return <section className="page page-full"><p className="empty">불러오는 중…</p></section>

  const meta = FACILITY_META[facility.type]
  const hasServices = facility.services.length > 0
  const showBenefits = !NO_BENEFIT_TYPES.includes(facility.type)
  const Icon = meta?.icon
  const directions = facility.lat
    ? `https://map.kakao.com/link/to/${encodeURIComponent(facility.name)},${facility.lat},${facility.lng}`
    : null

  return (
    <section className="page page-full">
      <Link to="/map" className="back"><ArrowLeft size={18} />지도로</Link>

      <div className="detail-card glass">
        <div className="detail-main">
          <div className="detail-hero">
            <span className={`icon-tile lg ${meta?.tone}`}>{Icon && <Icon size={28} strokeWidth={1.6} />}</span>
            <div className="detail-hero-text">
              <h1>{facility.name}</h1>
              {facility.distance_km != null && <p>내 지역에서 {facility.distance_km}km</p>}
            </div>
          </div>
        <div className="detail-actions">
          {directions && (
            <a className="btn kakao" href={directions} target="_blank" rel="noreferrer">
              <Navigation size={16} />카카오맵에서 길찾기
            </a>
          )}
          {facility.type !== 'pharmacy' && (
            <button
              type="button"
              className="btn ask"
              onClick={() => navigate(`/?q=${encodeURIComponent(`${facility.name}에서 받을 수 있는 서비스 알려줘`)}`)}
            >
              <MessageCircleHeart size={16} />챗봇에 물어보기
            </button>
          )}
        </div>
        <ul className="info-list">
          <li><MapPin size={18} strokeWidth={1.8} /><span>주소</span><strong>{facility.address ?? '-'}</strong></li>
          <li><Phone size={18} strokeWidth={1.8} /><span>전화</span><strong>{facility.phone ?? '-'}</strong></li>
          {/* '위치 출처'는 내부용이라 숨긴다 */}
          {Object.entries(facility.details).filter(([k]) => k !== '위치 출처').map(([k, v]) => (
            <li key={k}><Info size={18} strokeWidth={1.8} /><span>{k}</span><strong>{String(v)}</strong></li>
          ))}
          {facility.grades.length > 0 && (
            <li>
              <Info size={18} strokeWidth={1.8} /><span>평가등급</span>
              <strong className="grades">
                {facility.grades.map((g) => <span key={g} className="tag blue">{g}</span>)}
                <small className="grade-hint">건강보험심사평가원 적정성 평가 · 1등급이 가장 우수</small>
              </strong>
            </li>
          )}
        </ul>
        </div>
        <div className="detail-map">
          <KakaoMap markers={markers} center={facility} />
        </div>
      </div>

      {kakao && (
        <div className="callout place-note">
          <Info size={16} strokeWidth={1.8} />
          <span>
            카카오 장소 검색으로 찾은 기관이라 공공데이터의 인력·이용현황·제공 서비스 정보는 없어요.
            운영시간과 진료과목은 카카오맵에서 확인해 주세요.
          </span>
        </div>
      )}

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

      {(hasServices || showBenefits) && (
      <div className={`detail-columns ${hasServices && showBenefits ? '' : 'single'}`}>
        {hasServices && (
          <div>
            <h2 className="section-title"><ListChecks size={20} strokeWidth={1.8} />제공 서비스</h2>
            <ul className="service-list glass">
              {facility.services.map((s) => (
                <li key={s.name}><span>{s.name}</span><strong>{s.cost}</strong></li>
              ))}
            </ul>
          </div>
        )}
        {showBenefits && (
        <div>
          <h2 className="section-title">
            <Gift size={20} strokeWidth={1.8} />이 기관과 연계된 혜택
            {benefits.length > 0 && <span className="section-count">{benefits.length}</span>}
          </h2>
          {benefits.length === 0 ? (
            <p className="empty small">이 기관 유형과 연결된 혜택을 찾지 못했어요.</p>
          ) : (
            <>
              <ul className="linked-list">
                {benefits.slice(0, shown).map((b) => (
                  <li key={b.id}>
                    <Link
                      className="linked glass"
                      to={benefitPath(b, { province: facility.province, municipality: facility.municipality })}
                      state={{ benefit: b }}
                    >
                      <span><strong>{b.name}</strong><small className="clamp-2">{b.summary_text || b.criteria_text}</small></span>
                      <ArrowRight size={18} />
                    </Link>
                  </li>
                ))}
              </ul>
              {benefits.length > PAGE && (
                <button
                  type="button"
                  className="show-more"
                  onClick={() => setShown((n) => (n >= benefits.length ? PAGE : n + PAGE))}
                >
                  {shown >= benefits.length
                    ? <>접기<ChevronUp size={16} /></>
                    : <>더보기 <small>{benefits.length - shown}개 남음</small><ChevronDown size={16} /></>}
                </button>
              )}
            </>
          )}
        </div>
        )}
      </div>
      )}

      {facility.data_source && <p className="data-source">출처: {facility.data_source}</p>}
    </section>
  )
}
