import { useEffect, useRef, useState } from 'react'

const KEY = import.meta.env.VITE_KAKAO_MAP_KEY

let sdkPromise
function loadKakaoSdk() {
  if (!sdkPromise) {
    sdkPromise = new Promise((resolve, reject) => {
      const script = document.createElement('script')
      script.src = `https://dapi.kakao.com/v2/maps/sdk.js?appkey=${KEY}&autoload=false`
      script.onload = () => window.kakao.maps.load(() => resolve(window.kakao))
      script.onerror = () => reject(new Error('카카오맵 SDK 로드 실패 (키/도메인 등록 확인)'))
      document.head.appendChild(script)
    })
  }
  return sdkPromise
}

/** markers: [{ id, name, lat, lng }] — 마커 클릭 시 onSelect(marker) 호출 */
export default function KakaoMap({ markers, onSelect, center = { lat: 37.5665, lng: 126.978 } }) {
  const ref = useRef(null)
  const mapRef = useRef(null)
  const [error, setError] = useState(KEY ? null : 'VITE_KAKAO_MAP_KEY가 설정되지 않았습니다 (.env 참고)')

  useEffect(() => {
    if (!KEY) return
    let overlays = []
    loadKakaoSdk()
      .then((kakao) => {
        if (!mapRef.current) {
          mapRef.current = new kakao.maps.Map(ref.current, {
            center: new kakao.maps.LatLng(center.lat, center.lng),
            level: 6,
          })
        }
        const bounds = new kakao.maps.LatLngBounds()
        overlays = markers
          .filter((m) => m.lat && m.lng)
          .map((m) => {
            const pos = new kakao.maps.LatLng(m.lat, m.lng)
            bounds.extend(pos)
            const marker = new kakao.maps.Marker({ map: mapRef.current, position: pos, title: m.name })
            kakao.maps.event.addListener(marker, 'click', () => onSelect?.(m))
            return marker
          })
        if (overlays.length) mapRef.current.setBounds(bounds)
      })
      .catch((e) => setError(e.message))
    return () => overlays.forEach((o) => o.setMap(null))
  }, [markers, onSelect, center.lat, center.lng])

  if (error) return <div className="map map-placeholder">{error}</div>
  return <div ref={ref} className="map" />
}
