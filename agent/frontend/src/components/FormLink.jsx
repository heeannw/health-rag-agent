import { FileDown } from 'lucide-react'

// 신청 서식 링크 (http(s)만 링크로)
export default function FormLink({ form }) {
  const safe = /^https?:\/\//.test(form.link ?? '')
  return safe
    ? <a href={form.link} target="_blank" rel="noreferrer"><FileDown size={13} />{form.name}</a>
    : <span>{form.name}</span>
}
