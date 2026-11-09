import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { ChevronRight, LoaderCircle, LocateFixed, MapPin, RotateCw, Search } from 'lucide-react'
import KakaoMap from '../components/KakaoMap.jsx'
import { getFacilities } from '../api.js'
import { FACILITY_META } from '../facilityTypes.js'
import { searchNearbyPlaces } from '../kakao.js'
import { isKakaoPlace, savePlace } from '../placeCache.js'
import { useRegion } from '../regionContext.js'

const squash = (name) => name.replace(/\s/g, '')

/** 병원 평가등급이 많게는 10개 넘게 와서, 목록에는 가장 좋은 등급 하나와 나머지 개수만 보여준다 */
const gradeNo = (g) => Number(g.match(/(\d+)\s*등급/)?.[1] ?? 99)
const bestGrade = (grades) => [...grades].sort((a, b) => gradeNo(a) - gradeNo(b))[0]

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
const NEARBY_KM = 5
// 서울 전체만 해도 기관이 1만 곳이 넘어서, 지도·목록에는 가까운 순으로 이만큼만 올린다
const MAX_FACILITIES = 200
const scopeParams = (region) => (region.municipality ? { radius_km: NEARBY_KM } : { province: region.province })
// 지도를 이만큼(km) 넘게 옮기면 "이 지역 검색" 버튼을 띄운다
const MOVED_KM = 0.3
// 목록은 처음에 이만큼만 그리고, 끝까지 스크롤하면 이만큼씩 더 붙인다 (지도 핀은 전부 그대로)
const LIST_PAGE = 15
const kmBetween = (a, b) => Math.hypot((a.lat - b.lat) * 111, (a.lng - b.lng) * 88)

export default function MapPage() {
  const { region, shortLabel, locate, locating, locateError, resetToDefault } = useRegion()
  // 들어올 때마다 현재 위치를 다시 잡고, 실패하면 서울특별시 전체로 시작한다
  const [ready, setReady] = useState(false)
  useEffect(() => {
    locate()
      .then((ok) => ok || resetToDefault())
      .finally(() => setReady(true))
  }, [locate, resetToDefault])
  const [params] = useSearchParams()
  // 혜택 카드의 "가까운 ○○ 보기"로 들어오면 그 유형만 켜진 상태로 시작
  // (지도에 없는 유형, 예: 예전 링크의 dementia_center는 버린다)
  const [types, setTypes] = useState(() => (params.get('types') ?? '').split(',').filter((t) => t in FACILITY_META))
  const [query, setQuery] = useState('')
  const [items, setItems] = useState([])
  const [error, setError] = useState(null)
  const navigate = useNavigate()

  // 지도를 옮긴 뒤 다시 검색하면 그 지도 중심(area) 반경에서 찾는다. 지역을 바꾸면 다시 지역 기준으로
  const [area, setArea] = useState(null)
  const [mapCenter, setMapCenter] = useState(null)
  useEffect(() => setArea(null), [region])
  const searchBase = area ?? (region ? { lat: region.lat, lng: region.lng } : null)
  const moved = !!(mapCenter && searchBase && kmBetween(mapCenter, searchBase) > MOVED_KM)
  const searchHere = () => mapCenter && setArea(mapCenter)
  // 검색어·유형을 바꿀 때도 지도를 옮겨 둔 상태면 지금 보고 있는 곳에서 찾는다
  const followMap = () => moved && searchHere()

  useEffect(() => {
    if (!region || !ready) return
    let cancelled = false
    const timer = setTimeout(async () => {
      const q = query.trim()
      const center = area ?? { lat: region.lat, lng: region.lng }
      const scope = area ? { radius_km: NEARBY_KM } : scopeParams(region)
      const placeTypes = types.length ? types : Object.keys(FACILITY_META)
      try {
        const [api, ...placeLists] = await Promise.all([
          // 전체 보기일 때도 유형을 명시해서, 백엔드 데이터에 있는 치매안심센터가 지도에 섞이지 않게
          getFacilities({ types: placeTypes, q, ...center, ...scope, limit: MAX_FACILITIES }),
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
  }, [region, ready, types, query, area])

  // 목록 더 보기: 검색 결과가 바뀌면 다시 15개부터, 바닥 가까이 스크롤하면 15개 더
  const [listCount, setListCount] = useState(LIST_PAGE)
  const listRef = useRef(null)
  useEffect(() => {
    setListCount(LIST_PAGE)
    listRef.current?.scrollTo({ top: 0 })
  }, [items])
  const hasMore = listCount < items.length
  // 바닥에서 120px 안쪽이면 미리 붙인다. 목록이 패널보다 짧아 스크롤이 안 생기는 큰 화면도 같은 조건으로 채운다
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
  // 카카오 장소도 같은 기관 상세 화면으로 연다. 백엔드에 없는 장소라 데이터를 같이 넘겨 둔다
  const open = useCallback((f) => {
    if (isKakaoPlace(f.id)) savePlace(f)
    navigate(`/facilities/${f.id}`, { state: isKakaoPlace(f.id) ? { facility: f } : undefined })
  }, [navigate])
  const center = useMemo(() => (region ? { lat: region.lat, lng: region.lng } : undefined), [region])
  // 지역을 직접 고른 경우엔 그 좌표가 내 위치가 아니라서, GPS로 잡은 때만 점을 찍는다
  const myLocation = region?.fromGps ? center : undefined
  // "내 위치로": 위치를 다시 잡고, 좌표가 그대로여도 지도를 그 자리로 되돌린다
  const [recenterKey, setRecenterKey] = useState(0)
  const goToMyLocation = async () => {
    if (await locate()) setRecenterKey((k) => k + 1)
  }

  return (
    <section className="map-page">
      <div className="map-stage">
        <KakaoMap markers={items} onSelect={open} center={center} level={region?.municipality ? 6 : 8} myLocation={myLocation} recenterKey={recenterKey} onCenterChange={setMapCenter} />
        {moved && ready && (
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
          {/* 4개 유형을 2×2로 같은 폭에 맞춰서 줄이 들쭉날쭉하지 않게 */}
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
          {/* 개수 표시는 뺐다. 위치를 잡는 동안만 안내 */}
          {!ready && <p className="result-count">현재 위치를 찾는 중…</p>}
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
                      {/* 이름은 한 줄, 거리는 이름 오른쪽 끝에 붙여서 눈이 한 줄로 읽게 */}
                      <span className="facility-name">
                        <strong title={f.name}>{f.name}</strong>
                        {f.distance_km != null && <span className="distance">{f.distance_km}km</span>}
                      </span>
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
