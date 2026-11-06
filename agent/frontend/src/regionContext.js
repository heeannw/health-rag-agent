import { createContext, useContext } from 'react'

/** 전역 지역 선택 컨텍스트. Provider·선택 UI는 region.jsx */
export const RegionContext = createContext(null)

export function useRegion() {
  return useContext(RegionContext)
}
