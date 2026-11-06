/**
 * 카카오 장소 검색으로 찾은 기관은 백엔드에 없어서, 지도에서 누른 장소를 여기 잠깐 보관했다가
 * 기관 상세 화면(/facilities/kakao-…)이 꺼내 쓴다. 새로고침해도 열리도록 sessionStorage에도 둔다.
 */
const STORAGE_KEY = 'health-agent:kakao-places:v1'
const MAX = 50

export const isKakaoPlace = (id) => String(id).startsWith('kakao-')

function readAll() {
  try {
    return JSON.parse(sessionStorage.getItem(STORAGE_KEY)) ?? {}
  } catch {
    return {}
  }
}

export function savePlace(place) {
  const all = readAll()
  delete all[place.id]
  all[place.id] = place
  // 오래된 것부터 지워 개수 제한
  const ids = Object.keys(all)
  ids.slice(0, Math.max(0, ids.length - MAX)).forEach((k) => delete all[k])
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(all))
  } catch {
    // 저장이 막힌 환경이면 화면 이동 때 넘긴 state로만 연다
  }
}

export const getPlace = (id) => readAll()[id] ?? null
