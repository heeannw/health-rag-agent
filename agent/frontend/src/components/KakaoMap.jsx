import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { KAKAO_KEY as KEY, loadKakaoSdk } from '../kakao.js'
import MapPin from './MapPin.jsx'

/**
 * markers: [{ id, name, lat, lng }] — 마커 클릭 시 onSelect(marker) 호출
 * center·level이 바뀌면 그 위치로 지도를 옮긴다. 멀리 있는 마커까지 다 보이게 줌아웃하지 않는다.
 */
// 클러스터 묶음 모양 (카카오 클러스터러는 인라인 스타일만 받는다).
// 개수가 많을수록 크게, 색은 초록(50개 미만) → 노랑(50~99) → 주황(100개 이상). 경계는 CLUSTER_STEPS
// (빨강은 '위험'처럼 보여서 주황으로)
const CLUSTER_STEPS = [50, 100]
const CLUSTER_TIERS = [
  { size: 40, bg: 'rgba(90, 164, 140, 0.92)', color: '#fff', shadow: 'rgba(30, 90, 70, 0.3)' }, // 초록 (보듬 초록)
  { size: 48, bg: 'rgba(242, 182, 48, 0.95)', color: '#4A3400', shadow: 'rgba(140, 100, 10, 0.3)' }, // 노랑: 흰 글씨가 안 보여서 진한 글씨
  { size: 58, bg: 'rgba(240, 132, 56, 0.94)', color: '#fff', shadow: 'rgba(160, 75, 15, 0.32)' }, // 주황
]
const clusterStyle = ({ size, bg, color, shadow }) => ({
  width: `${size}px`, height: `${size}px`, lineHeight: `${size - 6}px`, textAlign: 'center',
  borderRadius: '50%', background: bg, border: '3px solid rgba(255, 255, 255, 0.9)',
  color, fontSize: '14px', fontWeight: '800', boxShadow: `0 4px 14px ${shadow}`,
})

/**
 * myLocation: { lat, lng } — 있으면 그 자리에 "내 위치" 점을 찍는다 (클러스터에 섞이지 않게 따로)
 * recenterKey: 값이 바뀌면 center가 그대로여도 다시 center로 옮긴다 (지도를 끌어 놓은 뒤 "내 위치로")
 * onCenterChange({ lat, lng }): 지도를 옮기거나 확대·축소해서 멈출 때마다 지금 지도 중심을 알려 준다
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
