async function request(path, options) {
  const res = await fetch(path, options)
  if (!res.ok) {
    // FastAPI 오류는 {detail: ...} 로 온다
    const body = await res.json().catch(() => null)
    throw new Error(typeof body?.detail === 'string' ? body.detail : `요청 실패 (${res.status})`)
  }
  return res.json()
}

const qs = (params) => {
  const entries = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== null && v !== '' && !(Array.isArray(v) && !v.length))
    .map(([k, v]) => [k, Array.isArray(v) ? v.join(',') : String(v)])
  return entries.length ? `?${new URLSearchParams(entries)}` : ''
}

/** history: 같은 대화의 이전 메시지 [{ role: 'user'|'assistant', content }] (오래된 것부터) */
export const askChat = (query, region, history = []) =>
  request('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, region: region || null, history }),
  })

export const getRegions = () => request('/api/regions')

/** params: { province, municipality, life_cycle, themes: string[] } */
export const getBenefits = (params = {}) => request(`/api/benefits${qs(params)}`)

/** 챗봇 인용 출처의 복지서비스 코드로 혜택 한 건 (source: welfare_central | welfare_local) */
export const getBenefitByService = (source, serviceId) =>
  request(`/api/benefits/by-service/${encodeURIComponent(source)}/${encodeURIComponent(serviceId)}`)

/** params: { types: string[], q, province, municipality, lat, lng } */
export const getFacilities = (params = {}) => request(`/api/facilities${qs(params)}`)

export const getFacility = (id, { lat, lng } = {}) =>
  request(`/api/facilities/${encodeURIComponent(id)}${qs({ lat, lng })}`)

/** data-rag 출처 구분자 → 화면 표시 이름 */
export const SOURCE_LABELS = {
  welfare_central: '중앙부처 복지서비스',
  welfare_local: '지자체 복지서비스',
  welfare_payment: '복지사업 급여지급 현황',
  law: '국가법령정보',
  hospital: '병원평가정보',
  dementia_center: '전국치매센터 표준데이터',
  ltc_institution: '장기요양기관',
  ltc_institution_search: '장기요양기관',
}
