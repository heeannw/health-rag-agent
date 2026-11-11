import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { KAKAO_KEY as KEY, loadKakaoSdk } from '../kakao.js'
import MapPin from './MapPin.jsx'

// 클러스터 모양 (인라인 스타일만 받음). 개수 30·50 경계로 초록 → 노랑 → 주황
const CLUSTER_STEPS = [30, 50]
const CLUSTER_TIERS = [
  { size: 40, bg: 'rgba(90, 164, 140, 0.92)', color: '#fff', shadow: 'rgba(30, 90, 70, 0.3)' },
  { size: 48, bg: 'rgba(242, 182, 48, 0.95)', color: '#4A3400', shadow: 'rgba(140, 100, 10, 0.3)' }, // 노랑은 진한 글씨
  { size: 58, bg: 'rgba(240, 132, 56, 0.94)', color: '#fff', shadow: 'rgba(160, 75, 15, 0.32)' },
]
const clusterStyle = ({ size, bg, color, shadow }) => ({
  width: `${size}px`, height: `${size}px`, lineHeight: `${size - 6}px`, textAlign: 'center',
  borderRadius: '50%', background: bg, border: '3px solid rgba(255, 255, 255, 0.9)',
  color, fontSize: '14px', fontWeight: '800', boxShadow: `0 4px 14px ${shadow}`,
})

/**
 * markers 클릭 시 onSelect, center·level이 바뀌면 이동. myLocation은 내 위치 점,
 * recenterKey가 바뀌면 center로 다시 이동, onCenterChange는 지도가 멈출 때 중심을 알린다.
 */
export default function KakaoMap({
  markers, onSelect, center = { lat: 37.5665, lng: 126.978 }, level = 6, myLocation, recenterKey, onCenterChange,
}) {
  const ref = useRef(null)
  const mapRef = useRef(null)
  const onCenterChangeRef = useRef(onCenterChange)
  onCenterChangeRef.current = onCenterChange
  const [error, setError] = useState(KEY ? null : 'VITE_KAKAO_MAP_KEY가 설정되지 않았습니다 (.env 참고)')

  const withMap = (fn) =>
    loadKakaoSdk()
      .then((kakao) => {
        if (!ref.current) return
        if (!mapRef.current) {
          const map = new kakao.maps.Map(ref.current, {
            center: new kakao.maps.LatLng(center.lat, center.lng),
            level,
          })
          kakao.maps.event.addListener(map, 'idle', () => {
            const c = map.getCenter()
            onCenterChangeRef.current?.({ lat: c.getLat(), lng: c.getLng() })
          })
          mapRef.current = map
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
  }, [center.lat, center.lng, level, recenterKey])

  useEffect(() => {
    if (!KEY || !myLocation?.lat || !myLocation?.lng) return
    let overlay
    let cancelled = false
    withMap((kakao, map) => {
      if (cancelled) return
      const el = document.createElement('div')
      el.className = 'my-location'
      el.title = '내 위치'
      el.innerHTML = '<span class="my-location-pulse"></span><span class="my-location-dot"></span>'
      overlay = new kakao.maps.CustomOverlay({
        position: new kakao.maps.LatLng(myLocation.lat, myLocation.lng), content: el, xAnchor: 0.5, yAnchor: 0.5, zIndex: 5,
      })
      overlay.setMap(map)
    })
    return () => {
      cancelled = true
      overlay?.setMap(null)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [myLocation?.lat, myLocation?.lng])

  // 마커가 많아서 줌아웃 상태에선 클러스터로 묶는다 (레벨 4 이하에서 풀림)
  const clustererRef = useRef(null)
  // 핀은 커스텀 오버레이 + React 포털로 그린다
  const [pins, setPins] = useState([])
  useEffect(() => {
    if (!KEY) return
    let overlays = []
    let cancelled = false
    withMap((kakao, map) => {
      if (cancelled) return
      if (!clustererRef.current && kakao.maps.MarkerClusterer) {
        clustererRef.current = new kakao.maps.MarkerClusterer({
          map,
          averageCenter: true,
          minLevel: 5,
          gridSize: 70,
          minClusterSize: 3,
          disableClickZoom: false,
          calculator: CLUSTER_STEPS,
          styles: CLUSTER_TIERS.map(clusterStyle),
          clickable: true,
        })
      }
      const next = markers
        .filter((m) => m.lat && m.lng)
        .map((m) => {
          const el = document.createElement('div')
          const overlay = new kakao.maps.CustomOverlay({
            position: new kakao.maps.LatLng(m.lat, m.lng), content: el, yAnchor: 1, clickable: true, zIndex: 1,
          })
          el.addEventListener('click', () => onSelect?.(m))
          // 올린 핀의 카드가 가려지지 않게 맨 위로
          el.addEventListener('mouseenter', () => overlay.setZIndex(10))
          el.addEventListener('mouseleave', () => overlay.setZIndex(1))
          return { m, el, overlay }
        })
      overlays = next.map((p) => p.overlay)
      setPins(next)
      if (clustererRef.current) clustererRef.current.addMarkers(overlays)
      else overlays.forEach((o) => o.setMap(map))
    })
    return () => {
      cancelled = true
      if (clustererRef.current) clustererRef.current.removeMarkers(overlays)
      else overlays.forEach((o) => o.setMap(null))
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [markers, onSelect])

  if (error) return <div className="map map-placeholder">{error}</div>
  return (
    <>
      <div ref={ref} className="map" />
      {pins.map(({ m, el }) => createPortal(<MapPin facility={m} />, el, m.id))}
    </>
  )
}
