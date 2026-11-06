import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { KAKAO_KEY as KEY, loadKakaoSdk } from '../kakao.js'
import MapPin from './MapPin.jsx'

/**
 * markers: [{ id, name, lat, lng }] — 마커 클릭 시 onSelect(marker) 호출
 * center·level이 바뀌면 그 위치로 지도를 옮긴다. 멀리 있는 마커까지 다 보이게 줌아웃하지 않는다.
 */
// 클러스터 묶음 모양 (카카오 클러스터러는 인라인 스타일만 받는다). 개수가 많을수록 크게
const clusterStyle = (size) => ({
  width: `${size}px`, height: `${size}px`, lineHeight: `${size - 6}px`, textAlign: 'center',
  // 여러 유형이 섞인 묶음이라 특정 기관 색(파랑=병원 등) 대신 보듬 초록으로
  borderRadius: '50%', background: 'rgba(90, 164, 140, 0.92)', border: '3px solid rgba(255, 255, 255, 0.9)',
  color: '#fff', fontSize: '14px', fontWeight: '800', boxShadow: '0 4px 14px rgba(30, 90, 70, 0.3)',
})

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

  // 마커가 수백 개라 그대로 찍으면 지도가 핀으로 덮인다. 줌아웃 상태에선 숫자 묶음(클러스터)으로 보여주고,
  // 묶음을 누르거나 가까이 확대하면(레벨 4 이하) 개별 마커로 풀린다
  const clustererRef = useRef(null)
  // 핀은 카카오 기본 마커 대신 커스텀 오버레이(DOM)로 그리고, 그 안을 React 포털로 채운다
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
          calculator: [10, 30, 100],
          styles: [40, 46, 54, 62].map(clusterStyle),
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
          // 마우스를 올린 핀의 정보 카드가 옆 핀들에 가려지지 않게 맨 위로
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
