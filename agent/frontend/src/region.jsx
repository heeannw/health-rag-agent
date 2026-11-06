import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { getRegions } from './api.js'
import RegionPicker from './components/RegionPicker.jsx'
import { regionFromCoords } from './kakao.js'
import { RegionContext, useRegion } from './regionContext.js'

const STORAGE_KEY = 'health-agent:region:v2'

/** 위치를 못 받거나 거부했을 때 쓰는 기본 지역. 좌표는 서울시청. */
const SEOUL_ALL = { province: '서울특별시', municipality: null, lat: 37.5665, lng: 126.978 }

const keyOf = (r) => (r.municipality ? `${r.province} ${r.municipality}` : r.province)
const optionLabel = (r) => (r.municipality ? keyOf(r) : `${r.province} 전체`)

function readSaved() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY))
  } catch {
    return null
  }
}

function save(region) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(region))
  } catch {
    // 저장이 막힌 환경이면 이번 방문 동안만 유지
  }
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

/**
 * 사용자가 고른 지역. 모든 화면(챗봇 질문, 혜택 필터, 지도 거리 기준)이 함께 쓴다.
 * 처음 방문하면 현재 위치로 시군구를 찾고, 실패하면 서울특별시 전체를 쓴다.
 */
export function RegionProvider({ children }) {
  const [regions, setRegions] = useState([])
  const [selected, setSelected] = useState(readSaved)
  const [locating, setLocating] = useState(false)
  const [locateError, setLocateError] = useState(null)
  const triedAuto = useRef(false)
  const pending = useRef(null)

  useEffect(() => {
    getRegions().then(setRegions).catch(() => setRegions([]))
  }, [])

  const choose = useCallback((region) => {
    setSelected(region)
    save(region)
  }, [])

  /** 현재 위치로 지역을 바꾼다. 성공하면 true. 동시에 여러 번 불려도 위치 요청은 한 번만 한다. */
  const locate = useCallback(() => {
    if (pending.current) return pending.current
    setLocating(true)
    setLocateError(null)
    pending.current = (async () => {
      try {
        const pos = await currentPosition()
        choose({ ...(await regionFromCoords(pos.lat, pos.lng)), ...pos, fromGps: true })
        return true
      } catch (e) {
        setLocateError(e.message)
        return false
      } finally {
        setLocating(false)
        pending.current = null
      }
    })()
    return pending.current
  }, [choose])

  const resetToDefault = useCallback(() => choose(SEOUL_ALL), [choose])

  useEffect(() => {
    if (selected || triedAuto.current) return
    triedAuto.current = true
    locate()
  }, [selected, locate])

  const value = useMemo(() => {
    const region = selected ?? SEOUL_ALL
    // 목록을 아직 못 받았으면 기본 지역만, 현재 위치로 찾은 지역이 목록에 없으면 더해서 보여준다
    const options = regions.length ? [...regions] : [SEOUL_ALL]
    if (!options.some((r) => keyOf(r) === keyOf(region))) options.push(region)
    return {
      regions: options,
      region,
      label: keyOf(region),
      shortLabel: region.municipality ?? optionLabel(region),
      locating,
      locateError,
      locate,
      resetToDefault,
      setRegionKey: (key) => {
        const next = options.find((r) => keyOf(r) === key)
        if (next) choose(next)
      },
    }
  }, [regions, selected, locating, locateError, locate, resetToDefault, choose])

  return <RegionContext.Provider value={value}>{children}</RegionContext.Provider>
}

export function RegionSelect() {
  const { regions, region, setRegionKey, locate, locating, locateError } = useRegion()
  return (
    <RegionPicker
      regions={regions}
      region={region}
      keyOf={keyOf}
      onChoose={(r) => setRegionKey(keyOf(r))}
      locate={locate}
      locating={locating}
      locateError={locateError}
    />
  )
}
