/** 카카오 장소는 백엔드에 없어서 기관 상세용으로 sessionStorage에 잠깐 보관한다 */
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
    // 저장이 막히면 화면 이동 state로만 연다
  }
}

export const getPlace = (id) => readAll()[id] ?? null
