import { FileDown } from 'lucide-react'

// 신청 서식은 복지로 첨부파일 링크. http(s) 링크만 걸고 나머지는 이름만 보여준다
export default function FormLink({ form }) {
  const safe = /^https?:\/\//.test(form.link ?? '')
  return safe
    ? <a href={form.link} target="_blank" rel="noreferrer"><FileDown size={13} />{form.name}</a>
    : <span>{form.name}</span>
}
