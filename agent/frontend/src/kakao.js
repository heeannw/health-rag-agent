export const KAKAO_KEY = import.meta.env.VITE_KAKAO_MAP_KEY

let sdkPromise
/** 카카오맵 SDK(services, clusterer)를 한 번만 불러온다 */
export function loadKakaoSdk() {
  if (!KAKAO_KEY) return Promise.reject(new Error('VITE_KAKAO_MAP_KEY가 설정되지 않았습니다 (.env 참고)'))
  if (!sdkPromise) {
    sdkPromise = new Promise((resolve, reject) => {
      const script = document.createElement('script')
      script.src = `https://dapi.kakao.com/v2/maps/sdk.js?appkey=${KAKAO_KEY}&libraries=services,clusterer&autoload=false`
      script.onload = () => window.kakao.maps.load(() => resolve(window.kakao))
      script.onerror = () => {
        sdkPromise = null
        reject(new Error('카카오맵 SDK 로드 실패 (키/도메인 등록 확인)'))
      }
      document.head.appendChild(script)
    })
  }
  return sdkPromise
}

/** 좌표 → { province, municipality } */
export async function regionFromCoords(lat, lng) {
  const kakao = await loadKakaoSdk()
  return new Promise((resolve, reject) => {
    new kakao.maps.services.Geocoder().coord2RegionCode(lng, lat, (result, status) => {
      const area = status === kakao.maps.services.Status.OK && (result.find((r) => r.region_type === 'H') ?? result[0])
      if (!area) return reject(new Error('현재 위치의 행정구역을 찾지 못했어요'))
      // '수원시 팔달구' → '수원시' (시 단위)
      resolve({ province: area.region_1depth_name, municipality: area.region_2depth_name.split(' ')[0] || null })
    })
  })
}

function currentPosition() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) return reject(new Error('이 브라우저는 위치 정보를 지원하지 않아요'))
    navigator.geolocation.getCurrentPosition(
      (p) => resolve({ lat: p.coords.latitude, lng: p.coords.longitude }),
      () => reject(new Error('위치 권한이 없어 현재 위치를 쓸 수 없어요')),
      { timeout: 10000, maximumAge: 10 * 60 * 1000 },
    )
  })
}

/** 현재 위치(GPS)와 행정구역 → { province, municipality, lat, lng, fromGps } */
export async function findMyLocation() {
  const pos = await currentPosition()
  return { ...(await regionFromCoords(pos.lat, pos.lng)), ...pos, fromGps: true }
}

// 기관 유형별 카카오 검색 (병원·약국은 카테고리, 나머지는 키워드). keep으로 엉뚱한 장소를 거른다
const PLACE_QUERIES = {
  hospital: { category: 'HP8', radius: 3000 },
  public_health_center: {
    keyword: '보건소', radius: 10000,
    keep: (p) => /보건(소|지소|진료소)$/.test(p.category_name.split(' > ').at(-1)),
  },
  pharmacy: { category: 'PM9', radius: 3000 },
  ltc_institution: { keyword: '요양원', radius: 5000, keep: (p) => /요양|노인/.test(p.category_name) },
}

// 과마다 따로 등록된 병원('OO병원 정형외과' 등)을 500m 안이면 'OO병원' 하나로 합친다
const MERGE_RADIUS_M = 500
function mergeDepartments(places) {
  const baseOf = (p) => {
    const [first, ...rest] = p.place_name.trim().split(/\s+/)
    return rest.length && /병원$/.test(first) ? first : p.place_name.trim()
  }
  const near = (a, b) => {
    const dLat = (Number(a.y) - Number(b.y)) * 111000
    const dLng = (Number(a.x) - Number(b.x)) * 88000 // 위도 37° 근처 경도 1°≈88km
    return Math.hypot(dLat, dLng) <= MERGE_RADIUS_M
  }
  const groups = [] // { base, items }
  for (const p of places) {
    const base = baseOf(p)
    const g = groups.find((g) => g.base === base && near(g.items[0], p))
    if (g) g.items.push(p)
    else groups.push({ base, items: [p] })
  }
  return groups.map(({ base, items }) => {
    if (items.length === 1) return items[0]
    const main = items.find((p) => p.place_name.trim() === base)
    // 결과는 거리순이라 items[0]이 가장 가깝다
    return main ?? { ...items[0], place_name: base, category_name: '의료,건강 > 병원' }
  })
}

/** 기준점 주변 카카오 장소를 /api/facilities 형식으로 */
export async function searchNearbyPlaces(type, { lat, lng }) {
  const kakao = await loadKakaoSdk()
  const { category, keyword, radius, keep = () => true } = PLACE_QUERIES[type]
  const places = new kakao.maps.services.Places()
  const options = { location: new kakao.maps.LatLng(lat, lng), radius, sort: kakao.maps.services.SortBy.DISTANCE }
  const data = await new Promise((resolve) => {
    const done = (result, status) => resolve(status === kakao.maps.services.Status.OK ? result : [])
    if (category) places.categorySearch(category, done, options)
    else places.keywordSearch(keyword, done, options)
  })
  return mergeDepartments(data.filter(keep)).map((p) => ({
    id: `kakao-${p.id}`,
    type,
    name: p.place_name,
    address: p.road_address_name || p.address_name,
    phone: p.phone || null,
    lat: Number(p.y),
    lng: Number(p.x),
    summary: p.category_name.split(' > ').at(-1),
    grades: [],
    distance_km: p.distance ? Math.round(Number(p.distance) / 100) / 10 : null,
    place_url: p.place_url,
    data_source: '카카오 장소 검색',
  }))
}
