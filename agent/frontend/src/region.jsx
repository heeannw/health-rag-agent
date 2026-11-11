import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { getRegions } from './api.js'
import RegionPicker from './components/RegionPicker.jsx'
import { findMyLocation } from './kakao.js'
import { RegionContext, useRegion } from './regionContext.js'

const STORAGE_KEY = 'health-agent:region:v2'

/** 위치를 못 받을 때 기본 지역 (서울시청 좌표) */
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
    // fromGps는 저장하지 않는다 (다음 방문에 예전 좌표가 '내 위치'로 보이지 않게)
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...region, fromGps: undefined }))
  } catch {
    // 저장이 막히면 이번 방문 동안만 유지
  }
}

/** 모든 화면이 쓰는 '내 지역'. 첫 방문은 현재 위치, 실패하면 서울특별시 전체 */
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

  /** 현재 위치로 지역 변경, 성공하면 true (동시 호출은 한 번만) */
  const locate = useCallback(() => {
    if (pending.current) return pending.current
    setLocating(true)
    setLocateError(null)
    pending.current = (async () => {
      try {
        choose(await findMyLocation())
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

  useEffect(() => {
    if (selected || triedAuto.current) return
    triedAuto.current = true
    locate()
  }, [selected, locate])

  const value = useMemo(() => {
    const region = selected ?? SEOUL_ALL
    // 목록에 없는 현재 지역은 덧붙인다
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
      setRegionKey: (key) => {
        const next = options.find((r) => keyOf(r) === key)
        if (next) choose(next)
      },
    }
  }, [regions, selected, locating, locateError, locate, choose])

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
