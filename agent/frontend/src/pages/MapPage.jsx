import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ChevronRight, Clock, LoaderCircle, LocateFixed, MapPin, Phone, RotateCw, Search } from 'lucide-react'
import KakaoMap from '../components/KakaoMap.jsx'
import { getFacilities } from '../api.js'
import { FACILITY_META } from '../facilityTypes.js'
import { searchNearbyPlaces } from '../kakao.js'
import { isKakaoPlace, savePlace } from '../placeCache.js'
import { useRegion } from '../regionContext.js'

const squash = (name) => name.replace(/\s/g, '')

// 목록 주소는 시도·시군구를 뺀다 ('서울특별시 중구 무교로 12' → '무교로 12')
const shortAddress = (addr) => addr.replace(/^\S+\s+(?:\S+[시군구]\s+){0,2}/, '') || addr

/** 목록엔 가장 좋은 평가등급 하나만 */
const gradeNo = (g) => Number(g.match(/(\d+)\s*등급/)?.[1] ?? 99)
const bestGrade = (grades) => [...grades].sort((a, b) => gradeNo(a) - gradeNo(b))[0]

/** 공공데이터와 카카오 결과를 합친다 (같은 기관이면 공공데이터를 남김) */
function mergeFacilities(api, places) {
  const dup = (p) => api.some((f) => squash(f.name) === squash(p.name)
    && f.lat && Math.hypot(f.lat - p.lat, (f.lng - p.lng) * 0.8) < 0.003)
  return [...api, ...places.filter((p) => !dup(p))]
    .sort((a, b) => (a.distance_km ?? Infinity) - (b.distance_km ?? Infinity))
}

// 시군구는 반경 안, 시도 전체는 그 시도 기관
const NEARBY_KM = 5
// 가까운 순으로 이만큼만
const MAX_FACILITIES = 200
const scopeParams = (region) => (region.municipality ? { radius_km: NEARBY_KM } : { province: region.province })
// 이만큼(km) 옮기면 "이 지역 검색" 버튼
const MOVED_KM = 0.3
// 목록 무한 스크롤 단위
const LIST_PAGE = 15
const kmBetween = (a, b) => Math.hypot((a.lat - b.lat) * 111, (a.lng - b.lng) * 88)

export default function MapPage() {
  // 지도는 '내 지역' 기준. '내 위치로'는 내 지역 자체를 바꾼다
  const { region, shortLabel, locate, locating, locateError } = useRegion()

  const [types, setTypes] = useState([])
  const [query, setQuery] = useState('')
  const [items, setItems] = useState([])
  const [error, setError] = useState(null)
  const navigate = useNavigate()

  // "이 지역 검색"을 누르면 지도 중심(area) 기준, 지역을 바꾸면 초기화
  const [area, setArea] = useState(null)
  const [mapCenter, setMapCenter] = useState(null)
  // 지도 중심도 비워서, 새 지역으로 옮겨 가는 동안 버튼이 깜빡이지 않게
  useEffect(() => {
    setArea(null)
    setMapCenter(null)
  }, [region])
  const searchBase = area ?? { lat: region.lat, lng: region.lng }
  const moved = !!(mapCenter && searchBase && kmBetween(mapCenter, searchBase) > MOVED_KM)
  const searchHere = () => mapCenter && setArea(mapCenter)
  // 지도를 옮겨 둔 상태면 검색어·유형 변경도 지금 보는 곳에서
  const followMap = () => moved && searchHere()

  useEffect(() => {
    let cancelled = false
    const timer = setTimeout(async () => {
      const q = query.trim()
      const center = area ?? { lat: region.lat, lng: region.lng }
      const scope = area ? { radius_km: NEARBY_KM } : scopeParams(region)
      const placeTypes = types.length ? types : Object.keys(FACILITY_META)
      try {
        const [api, ...placeLists] = await Promise.all([
          // 유형을 명시해 치매안심센터를 뺀다
          getFacilities({ types: placeTypes, q, ...center, ...scope, limit: MAX_FACILITIES }),
          // 카카오가 실패해도 공공데이터는 보여준다
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
  }, [region, types, query, area])

  // 결과가 바뀌면 처음부터
  const [listCount, setListCount] = useState(LIST_PAGE)
  const listRef = useRef(null)
  useEffect(() => {
    setListCount(LIST_PAGE)
    listRef.current?.scrollTo({ top: 0 })
  }, [items])
  const hasMore = listCount < items.length
  // 바닥 120px 안이면 더 붙인다 (스크롤이 없는 큰 화면도)
  const loadMoreIfNearEnd = useCallback(() => {
    const ul = listRef.current
    if (ul && hasMore && ul.scrollTop + ul.clientHeight >= ul.scrollHeight - 120) {
      setListCount((n) => n + LIST_PAGE)
    }
  }, [hasMore])
  useEffect(loadMoreIfNearEnd, [loadMoreIfNearEnd, listCount])

  const toggleType = (key) => {
    followMap()
    setTypes((t) => (t.includes(key) ? t.filter((k) => k !== key) : [...t, key]))
  }
  // 카카오 장소는 데이터를 같이 넘긴다
  const open = useCallback((f) => {
    if (isKakaoPlace(f.id)) savePlace(f)
    navigate(`/facilities/${encodeURIComponent(f.id)}`, { state: isKakaoPlace(f.id) ? { facility: f } : undefined })
  }, [navigate])
  const center = useMemo(() => ({ lat: region.lat, lng: region.lng }), [region])
  // GPS로 잡은 지역일 때만 내 위치 점
  const myLocation = region.fromGps ? center : undefined
  // 내 위치가 있으면 거기서 잰 거리
  const distanceOf = (f) => (myLocation && f.lat ? Math.round(kmBetween(myLocation, f) * 10) / 10 : f.distance_km)
  // 좌표가 같아도 지도를 되돌린다
  const [recenterKey, setRecenterKey] = useState(0)
  const goToMyLocation = async () => {
    if (await locate()) setRecenterKey((k) => k + 1)
  }

  return (
    <section className="map-page">
      <div className="map-stage">
        <KakaoMap markers={items} onSelect={open} center={center} level={region.municipality ? 6 : 8} myLocation={myLocation} recenterKey={recenterKey} onCenterChange={setMapCenter} />
        {moved && (
          <button type="button" className="map-search-here glass" onClick={searchHere}>
            <RotateCw size={15} strokeWidth={2} />이 지역 검색
          </button>
        )}
        <div className="map-locate">
          <button
            type="button"
            className="map-locate-btn glass"
            onClick={goToMyLocation}
            disabled={locating}
            aria-label="내 위치로 이동"
            title="내 위치로"
          >
            {locating ? <LoaderCircle size={20} className="spin" /> : <LocateFixed size={20} strokeWidth={1.8} />}
          </button>
          {locateError && !locating && <p className="map-locate-error glass" role="status">{locateError}</p>}
        </div>

        <aside className="map-panel glass">
          <header>
            <h1>내 주변 의료기관</h1>
            <span className="map-panel-region"><MapPin size={13} strokeWidth={2} />{area ? '지도 중심 주변' : shortLabel}</span>
          </header>
          <label className="search">
            <Search size={16} strokeWidth={1.8} />
            <input value={query} onChange={(e) => { followMap(); setQuery(e.target.value) }} placeholder="기관명, 진료과목 검색" />
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
          {locating && <p className="result-count">현재 위치를 찾는 중…</p>}
          {error && <p className="error">{error}</p>}
          <ul ref={listRef} onScroll={loadMoreIfNearEnd}>
            {items.slice(0, listCount).map((f) => {
              const meta = FACILITY_META[f.type]
              const Icon = meta?.icon
              return (
                <li key={f.id}>
                  <button onClick={() => open(f)}>
                    <span className={`icon-tile ${meta?.tone}`}>{Icon && <Icon size={18} strokeWidth={1.8} />}</span>
                    <span className="facility-text">
                      <span className="facility-name">
                        <strong title={f.name}>{f.name}</strong>
                        {distanceOf(f) != null && <span className="distance">{distanceOf(f)}km</span>}
                      </span>
                      {f.address && (
                        <span className="facility-meta" title={f.address}><MapPin size={13} strokeWidth={1.8} /><span>{shortAddress(f.address)}</span></span>
                      )}
                      {f.details?.운영시간 && (
                        <span className="facility-meta"><Clock size={13} strokeWidth={1.8} /><span>{f.details.운영시간}</span></span>
                      )}
                      {f.phone && (
                        <span className="facility-meta"><Phone size={13} strokeWidth={1.8} /><span>{f.phone}</span></span>
                      )}
                      {f.grades.length > 0 && (
                        <span className="grades" title={f.grades.join(', ')}>
                          <span className="tag blue">{bestGrade(f.grades)}</span>
                          {f.grades.length > 1 && <span className="tag more">평가 +{f.grades.length - 1}</span>}
                        </span>
                      )}
                    </span>
                    <ChevronRight size={16} className="chev" />
                  </button>
                </li>
              )
            })}
            {hasMore && (
              <li className="list-more" aria-hidden="true">
                <LoaderCircle size={16} className="spin" />더 불러오는 중
              </li>
            )}
          </ul>
          <p className="data-source map-source">
            출처: 건강보험심사평가원 병원평가정보 · 국민건강보험공단 장기요양기관 · 카카오 장소 검색
          </p>
        </aside>
      </div>
    </section>
  )
}
