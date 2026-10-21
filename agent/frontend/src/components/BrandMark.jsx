import { MeshGradient } from '@paper-design/shaders-react'
import { HeartPulse } from 'lucide-react'
import { useShouldAnimate } from '../hooks/motion.js'

/** 사이드바 로고: 팔레트 3색이 천천히 섞이는 메시 그러데이션 (paper-design shaders) 위에 아이콘. */
export default function BrandMark({ size = 40 }) {
  const animate = useShouldAnimate()
  return (
    <span className="brand-mark" style={{ width: size, height: size }} aria-hidden="true">
      <MeshGradient
        width={size}
        height={size}
        colors={['#D7F6F7', '#71BAF6', '#FFC9CA', '#71BAF6']}
        distortion={0.8}
        swirl={0.4}
        speed={animate ? 0.4 : 0}
      />
      <HeartPulse className="brand-icon" size={size * 0.5} strokeWidth={2.2} />
    </span>
  )
}
