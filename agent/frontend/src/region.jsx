import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { MapPin } from 'lucide-react'
import { getRegions } from './api.js'

const STORAGE_KEY = 'health-agent:region'
const RegionContext = createContext(null)

const keyOf = (r) => `${r.province} ${r.municipality}`

function readSaved() {
  try {
    return localStorage.getItem(STORAGE_KEY)
  } catch {
    return null
  }
}

/** 사용자가 고른 지역. 모든 화면(챗봇 질문, 혜택 필터, 지도 거리 기준)이 함께 쓴다. */
export function RegionProvider({ children }) {
  const [regions, setRegions] = useState([])
  const [selectedKey, setSelectedKey] = useState(readSaved)

  useEffect(() => {
    getRegions().then(setRegions).catch(() => setRegions([]))
  }, [])

  const value = useMemo(() => {
    const region = regions.find((r) => keyOf(r) === selectedKey) ?? regions[0] ?? null
    return {
      regions,
      region,
      label: region ? keyOf(region) : '',
      shortLabel: region ? region.municipality : '',
      setRegionKey: (key) => {
        setSelectedKey(key)
        try {
          localStorage.setItem(STORAGE_KEY, key)
        } catch {
          // 저장이 막힌 환경이면 이번 방문 동안만 유지
        }
      },
    }
  }, [regions, selectedKey])

  return <RegionContext.Provider value={value}>{children}</RegionContext.Provider>
}

export function useRegion() {
  return useContext(RegionContext)
}

export function RegionSelect({ className = '' }) {
  const { regions, label, setRegionKey } = useRegion()
  if (!regions.length) return null
  return (
    <label className={`region-select ${className}`}>
      <MapPin size={16} strokeWidth={1.8} />
      <select value={label} onChange={(e) => setRegionKey(e.target.value)} aria-label="내 지역">
        {regions.map((r) => <option key={keyOf(r)} value={keyOf(r)}>{keyOf(r)}</option>)}
      </select>
    </label>
  )
}
