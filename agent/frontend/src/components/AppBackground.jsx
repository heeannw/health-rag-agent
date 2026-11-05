import { ShaderGradient, ShaderGradientCanvas } from '@shadergradient/react'
import { useShouldAnimate } from '../hooks/motion.js'

/**
 * 사이트 전체 뒤에 깔리는 흐르는 그러데이션 (셰이더 그라디언트).
 * 글자는 항상 유리 패널 위에 올라가므로 배경은 옅고 느리게 둔다.
 * WebGL 캔버스는 이것 하나만 크게 쓰고, 나머지 효과는 CSS로 처리한다.
 */
export default function AppBackground() {
  const animate = useShouldAnimate()

  return (
    <ShaderGradientCanvas style={{ width: '100%', height: '100%' }} pointerEvents="none" pixelDensity={1} lazyLoad={false}>
      <ShaderGradient
        control="props"
        type="waterPlane"
        animate={animate ? 'on' : 'off'}
        uSpeed={0.05}
        uStrength={1.6}
        uDensity={1.2}
        uFrequency={3.5}
        uAmplitude={1}
        color1="#D7F6F7"
        color2="#A9D5FA"
        color3="#FFDCDD"
        brightness={1.5}
        cDistance={3.4}
        cPolarAngle={90}
        cAzimuthAngle={180}
        lightType="3d"
        envPreset="city"
        grain="off"
      />
    </ShaderGradientCanvas>
  )
}
