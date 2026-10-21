import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { ChevronRight, Search } from 'lucide-react'
import KakaoMap from '../components/KakaoMap.jsx'
import { getFacilities } from '../api.js'
import { FACILITY_META } from '../facilityTypes.js'
import { useRegion } from '../region.jsx'

export default function MapPage() {
  const { region } = useRegion()
  const [params] = useSearchParams()
  // 혜택 카드의 "가까운 ○○ 보기"로 들어오면 그 유형만 켜진 상태로 시작
  const [types, setTypes] = useState(() => (params.get('types') ? params.get('types').split(',') : []))
  const [query, setQuery] = useState('')
  const [items, setItems] = useState([])
  const [error, setError] = useState(null)
  const navigate = useNavigate()

  useEffect(() => {
    if (!region) return
    const timer = setTimeout(() => {
      getFacilities({ types, q: query.trim(), lat: region.lat, lng: region.lng })
        .then(setItems)
        .catch((e) => setError(e.message))
    }, 200)
    return () => clearTimeout(timer)
  }, [region, types, query])

  const toggleType = (key) => setTypes((t) => (t.includes(key) ? t.filter((k) => k !== key) : [...t, key]))
  const open = useCallback((f) => navigate(`/facilities/${f.id}`), [navigate])
  const center = useMemo(() => (region ? { lat: region.lat, lng: region.lng } : undefined), [region])

  return (
    <section className="map-page">
      <div className="map-stage">
        <KakaoMap markers={items} onSelect={open} center={center} />

        <aside className="map-panel glass">
          <header>
            <h1>내 주변 의료기관</h1>
            <span>{region?.municipality}</span>
          </header>
          <label className="search">
            <Search size={16} strokeWidth={1.8} />
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="기관명, 진료과목 검색" />
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
          <p className="result-count">결과 {items.length}곳 · 가까운 순</p>
          {error && <p className="error">{error}</p>}
          <ul>
            {items.map((f) => {
              const meta = FACILITY_META[f.type]
              const Icon = meta?.icon
              return (
                <li key={f.id}>
                  <button onClick={() => open(f)}>
                    <span className={`icon-tile ${meta?.tone}`}>{Icon && <Icon size={18} strokeWidth={1.8} />}</span>
                    <span className="facility-text">
                      <strong>{f.name}</strong>
                      <small>{meta?.label}{f.summary ? ` · ${f.summary}` : ''}</small>
                      {f.grades.length > 0 && (
                        <span className="grades">{f.grades.map((g) => <span key={g} className="tag blue">{g}</span>)}</span>
                      )}
                    </span>
                    {f.distance_km != null && <span className="distance">{f.distance_km}km</span>}
                    <ChevronRight size={18} className="chev" />
                  </button>
                </li>
              )
            })}
          </ul>
        </aside>
      </div>
    </section>
  )
}
