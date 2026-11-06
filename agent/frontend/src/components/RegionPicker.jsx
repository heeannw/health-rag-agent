import { useEffect, useMemo, useRef, useState } from 'react'
import { ChevronDown, ChevronLeft, LoaderCircle, LocateFixed, MapPin, Search, X } from 'lucide-react'

// 시도 버튼에 쓸 짧은 이름과 보여줄 순서. 목록에 없는 시도는 원래 이름으로 맨 뒤에 붙는다
const PROVINCE_SHORT = {
  서울특별시: '서울', 경기도: '경기', 인천광역시: '인천', 부산광역시: '부산', 대구광역시: '대구',
  전남광주통합특별시: '전남·광주', 대전광역시: '대전', 울산광역시: '울산', 세종특별자치시: '세종',
  강원특별자치도: '강원', 충청북도: '충북', 충청남도: '충남', 전북특별자치도: '전북',
  경상북도: '경북', 경상남도: '경남', 제주특별자치도: '제주',
}
const ORDER = Object.keys(PROVINCE_SHORT)
const shortOf = (p) => PROVINCE_SHORT[p] ?? p
const MAX_SEARCH = 30

/**
 * 내 지역 선택. 시군구가 200개가 넘어서 한 목록에 다 펼치지 않고
 * 시도 → 시군구 두 단계로 고르거나, 이름으로 바로 검색한다.
 */
export default function RegionPicker({ regions, region, keyOf, onChoose, locate, locating, locateError }) {
  const [open, setOpen] = useState(false)
  const [province, setProvince] = useState(region.province)
  const [query, setQuery] = useState('')
  const rootRef = useRef(null)
  const searchRef = useRef(null)

  const byProvince = useMemo(() => {
    const map = new Map()
    regions.forEach((r) => map.set(r.province, [...(map.get(r.province) ?? []), r]))
    const rank = (p) => (ORDER.includes(p) ? ORDER.indexOf(p) : ORDER.length)
    return new Map([...map].sort(([a], [b]) => rank(a) - rank(b)))
  }, [regions])

  const results = useMemo(() => {
    const q = query.replace(/\s/g, '')
    if (!q) return null
    return regions
      .filter((r) => `${r.province}${r.municipality ?? ''}${shortOf(r.province)}`.includes(q))
      .slice(0, MAX_SEARCH)
  }, [regions, query])

  // 열 때마다 지금 고른 지역의 시도 화면에서 시작
  const toggle = () => {
    if (!open) {
      setProvince(region.province)
      setQuery('')
    }
    setOpen((o) => !o)
  }

  useEffect(() => {
    if (!open) return
    searchRef.current?.focus()
    const onDown = (e) => rootRef.current?.contains(e.target) || setOpen(false)
    const onKey = (e) => e.key === 'Escape' && setOpen(false)
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  const choose = (r) => {
    onChoose(r)
    setOpen(false)
  }
  const isCurrent = (r) => keyOf(r) === keyOf(region)
  const label = region.municipality ?? `${region.province} 전체`
  const list = province ? byProvince.get(province) ?? [] : []

  return (
    <div className="region-picker" ref={rootRef}>
      <div className="region-select">
        <MapPin size={16} strokeWidth={1.8} />
        <button
          type="button"
          className="region-trigger"
          onClick={toggle}
          aria-haspopup="dialog"
          aria-expanded={open}
          aria-label={`내 지역: ${keyOf(region)}. 바꾸기`}
          title={keyOf(region)}
        >
          <span>{label}</span>
          <ChevronDown size={16} className={open ? 'flip' : ''} />
        </button>
        <button
          type="button"
          className="locate-btn"
          onClick={locate}
          disabled={locating}
          title="현재 위치로 설정"
          aria-label="현재 위치로 설정"
        >
          {locating ? <LoaderCircle size={16} className="spin" /> : <LocateFixed size={16} strokeWidth={1.8} />}
        </button>
      </div>
      {locateError && <small className="region-hint">{locateError}</small>}

      {open && (
        <div className="region-pop" role="dialog" aria-label="지역 선택">
          <label className="region-search">
            <Search size={15} strokeWidth={1.8} />
            <input
              ref={searchRef}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="시군구 이름으로 찾기 (예: 마포)"
            />
            {query && (
              <button type="button" onClick={() => setQuery('')} aria-label="검색어 지우기"><X size={14} /></button>
            )}
          </label>

          {results ? (
            <ul className="region-results">
              {results.length === 0 && <li className="region-empty">‘{query}’에 맞는 지역이 없어요</li>}
              {results.map((r) => (
                <li key={keyOf(r)}>
                  <button type="button" className={isCurrent(r) ? 'on' : ''} onClick={() => choose(r)}>
                    <strong>{r.municipality ?? `${r.province} 전체`}</strong>
                    {r.municipality && <small>{r.province}</small>}
                  </button>
                </li>
              ))}
            </ul>
          ) : province ? (
            <>
              <div className="region-step">
                <button type="button" onClick={() => setProvince(null)}>
                  <ChevronLeft size={16} />시도
                </button>
                <strong>{province}</strong>
              </div>
              <div className="region-grid">
                {list.map((r) => (
                  <button
                    key={keyOf(r)}
                    type="button"
                    className={`${isCurrent(r) ? 'on' : ''} ${r.municipality ? '' : 'all'}`}
                    onClick={() => choose(r)}
                  >
                    {r.municipality ?? '전체'}
                  </button>
                ))}
              </div>
            </>
          ) : (
            <>
              <p className="region-caption">시도를 고르세요</p>
              <div className="region-grid">
                {[...byProvince.keys()].map((p) => (
                  <button
                    key={p}
                    type="button"
                    className={p === region.province ? 'on' : ''}
                    onClick={() => setProvince(p)}
                    title={p}
                  >
                    {shortOf(p)}
                  </button>
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}
