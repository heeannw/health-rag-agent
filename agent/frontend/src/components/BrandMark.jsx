/** 서비스 '보듬' 로고 (하트 + 십자가 + 글자) */
export default function BrandLogo({ height = 40 }) {
  return <img className="brand-logo" src="/brand/bodeum-logo.png" alt="보듬" height={height} width={Math.round(height * 2.425)} />
}

/** 챗봇 답변 옆 프로필: 로고의 하트·십자가 부분만 */
export function BodeumAvatar() {
  return (
    <span className="avatar" aria-hidden="true">
      <img src="/brand/bodeum-mark.png" alt="" width="26" height="26" />
    </span>
  )
}
