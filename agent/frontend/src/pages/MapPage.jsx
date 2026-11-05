import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { ChevronRight, Search } from 'lucide-react'
import KakaoMap from '../components/KakaoMap.jsx'
import { getFacilities } from '../api.js'
import { FACILITY_META } from '../facilityTypes.js'
import { searchNearbyPlaces } from '../kakao.js'
import { useRegion } from '../region.jsx'

const squash = (name) => name.replace(/\s/g, '')

/**
 * 공공데이터 기관(/api/facilities)과 카카오 장소 검색 결과를 합친다.
 * 같은 기관(이름 같고 300m 이내)은 상세정보가 있는 공공데이터를 남긴다.
 */
function mergeFacilities(api, places) {
  const dup = (p) => api.some((f) => squash(f.name) === squash(p.name)
    && f.lat && Math.hypot(f.lat - p.lat, (f.lng - p.lng) * 0.8) < 0.003)
  return [...api, ...places.filter((p) => !dup(p))]
    .sort((a, b) => (a.distance_km ?? Infinity) - (b.distance_km ?? Infinity))
}

// 시군구(현재 위치 포함)는 기준점 반경 안만, 시도 전체는 그 시도 기관만 보여준다
const NEARBY_KM = 10
// 서울 전체만 해도 기관이 1만 곳이 넘어서, 지도·목록에는 가까운 순으로 이만큼만 올린다
const MAX_FACILITIES = 300
const scopeParams = (region) => (region.municipality ? { radius_km: NEARBY_KM } : { province: region.province })

export default function MapPage() {
  const { region, shortLabel, locate, resetToDefault } = useRegion()
  // 들어올 때마다 현재 위치를 다시 잡고, 실패하면 서울특별시 전체로 시작한다
  const [ready, setReady] = useState(false)
  useEffect(() => {
    locate()
      .then((ok) => ok || resetToDefault())
      .finally(() => setReady(true))
  }, [locate, resetToDefault])
  const [params] = useSearchParams()
  // 혜택 카드의 "가까운 ○○ 보기"로 들어오면 그 유형만 켜진 상태로 시작
  const [types, setTypes] = useState(() => (params.get('types') ? params.get('types').split(',') : []))
  const [query, setQuery] = useState('')
  const [items, setItems] = useState([])
  const [error, setError] = useState(null)
  const navigate = useNavigate()

  useEffect(() => {
    if (!region || !ready) return
    let cancelled = false
    const timer = setTimeout(async () => {
      const q = query.trim()
      const center = { lat: region.lat, lng: region.lng }
      const placeTypes = types.length ? types : Object.keys(FACILITY_META)
      try {
        const [api, ...placeLists] = await Promise.all([
          getFacilities({ types, q, ...center, ...scopeParams(region), limit: MAX_FACILITIES }),
          // 카카오 키가 없거나 검색이 막혀도 공공데이터 목록은 보여준다
          ...placeTypes.map((t) => searchNearbyPlaces(t, center).catch(() => [])),
        ])
        const places = placeLists.flat().filter((p) => !q || p.name.includes(q) || p.summary.includes(q))
        if (!cancelled) {
          setError(null)
          setItems(mergeFacilities(api, places))
        }
      } catch (e) {
        if (!cancelled) setError(e.message)
      }
    }, 200)
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [region, ready, types, query])

  const toggleType = (key) => setTypes((t) => (t.includes(key) ? t.filter((k) => k !== key) : [...t, key]))
  // 카카오 장소는 우리 상세 데이터가 없어서 카카오맵 장소 페이지로 연다
  const open = useCallback(
    (f) => (f.place_url ? window.open(f.place_url, '_blank', 'noopener') : navigate(`/facilities/${f.id}`)),
    [navigate],
  )
  const center = useMemo(() => (region ? { lat: region.lat, lng: region.lng } : undefined), [region])

  return (
    <section className="map-page">
      <div className="map-stage">
        <KakaoMap markers={items} onSelect={open} center={center} level={region?.municipality ? 6 : 8} />

        <aside className="map-panel glass">
          <header>
            <h1>내 주변 의료기관</h1>
            <span>{shortLabel}</span>
          </header>
          <label className="search">
            <Search size={16} strokeWidth={1.8} />
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="기관명, 진료과목 검색" />
          </label>
          <div className="type-toggles">
            {Object.entries(FACILITY_META).map(([key, { label, icon: Icon, tone }]) => (
              <button
                key={key}
                aria-pressed={types.includes(key)}
                className={`toggle ${tone} ${types.includes(key) ? 'on' : ''}`}
                onClick={() => toggleType(key)}
              >
                <Icon size={15} strokeWidth={1.8} />{label}
              </button>
            ))}
          </div>
          <p className="result-count">{ready ? `가까운 순 ${items.length}곳` : '현재 위치를 찾는 중…'}</p>
          {error && <p className="error">{error}</p>}
          <ul>
            {items.map((f) => {
              const meta = FACILITY_META[f.type]
              const Icon = meta?.icon
              return (
                <li key={f.id}>
                  <button onClick={() => open(f)}>
                    <span className={`icon-tile ${meta?.tone}`}>{Icon && <Icon size={18} strokeWidth={1.8} />}</span>
                    <span className="facility-text">
                      <strong>{f.name}</strong>
                      <small>
                        {meta?.label}{f.summary ? ` · ${f.summary}` : ''}
                      </small>
                      {f.grades.length > 0 && (
                        <span className="grades">{f.grades.map((g) => <span key={g} className="tag blue">{g}</span>)}</span>
                      )}
                    </span>
                    {f.distance_km != null && <span className="distance">{f.distance_km}km</span>}
                    <ChevronRight size={18} className="chev" />
                  </button>
                </li>
              )
            })}
          </ul>
          <p className="data-source map-source">
            출처: 전국치매센터표준데이터 · 건강보험심사평가원 병원평가정보 · 국민건강보험공단 장기요양기관 · 카카오 장소 검색
          </p>
        </aside>
      </div>
    </section>
  )
}
