async function request(path, options) {
  const res = await fetch(path, options)
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`)
  return res.json()
}

const qs = (params) => {
  const entries = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== null && v !== '' && !(Array.isArray(v) && !v.length))
    .map(([k, v]) => [k, Array.isArray(v) ? v.join(',') : String(v)])
  return entries.length ? `?${new URLSearchParams(entries)}` : ''
}

export const askChat = (query, region) =>
  request('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, region: region || null }),
  })

export const getRegions = () => request('/api/regions')

/** params: { province, municipality, life_cycle, themes: string[] } */
export const getBenefits = (params = {}) => request(`/api/benefits${qs(params)}`)

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
  mock: '샘플',
}
