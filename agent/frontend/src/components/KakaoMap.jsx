import { useEffect, useRef, useState } from 'react'
import { KAKAO_KEY as KEY, loadKakaoSdk } from '../kakao.js'

/**
 * markers: [{ id, name, lat, lng }] — 마커 클릭 시 onSelect(marker) 호출
 * center·level이 바뀌면 그 위치로 지도를 옮긴다. 멀리 있는 마커까지 다 보이게 줌아웃하지 않는다.
 */
export default function KakaoMap({ markers, onSelect, center = { lat: 37.5665, lng: 126.978 }, level = 6 }) {
  const ref = useRef(null)
  const mapRef = useRef(null)
  const [error, setError] = useState(KEY ? null : 'VITE_KAKAO_MAP_KEY가 설정되지 않았습니다 (.env 참고)')

  const withMap = (fn) =>
    loadKakaoSdk()
      .then((kakao) => {
        if (!ref.current) return
        if (!mapRef.current) {
          mapRef.current = new kakao.maps.Map(ref.current, {
            center: new kakao.maps.LatLng(center.lat, center.lng),
            level,
          })
        }
        fn(kakao, mapRef.current)
      })
      .catch((e) => setError(e.message))

  useEffect(() => {
    if (!KEY) return
    withMap((kakao, map) => {
      map.setLevel(level)
      map.setCenter(new kakao.maps.LatLng(center.lat, center.lng))
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [center.lat, center.lng, level])

  useEffect(() => {
    if (!KEY) return
    let overlays = []
    let cancelled = false
    withMap((kakao, map) => {
      if (cancelled) return
      overlays = markers
        .filter((m) => m.lat && m.lng)
        .map((m) => {
          const marker = new kakao.maps.Marker({ map, position: new kakao.maps.LatLng(m.lat, m.lng), title: m.name })
          kakao.maps.event.addListener(marker, 'click', () => onSelect?.(m))
          return marker
        })
    })
    return () => {
      cancelled = true
      overlays.forEach((o) => o.setMap(null))
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [markers, onSelect])

  if (error) return <div className="map map-placeholder">{error}</div>
  return <div ref={ref} className="map" />
}
