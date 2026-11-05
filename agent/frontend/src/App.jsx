import { Suspense, lazy } from 'react'
import { BrowserRouter, NavLink, Route, Routes } from 'react-router-dom'
import { Gift, MapPinned, MessageCircleHeart, ShieldCheck } from 'lucide-react'
import ChatPage from './pages/ChatPage.jsx'
import BenefitsPage from './pages/BenefitsPage.jsx'
import MapPage from './pages/MapPage.jsx'
import FacilityDetailPage from './pages/FacilityDetailPage.jsx'
import BrandMark from './components/BrandMark.jsx'
import { RegionProvider, RegionSelect } from './region.jsx'
import { ChatHistoryProvider, useChatHistory } from './chatHistory.jsx'
import ConversationList from './components/ConversationList.jsx'

// three.js가 커서 첫 화면 이후에 따로 불러온다
const AppBackground = lazy(() => import('./components/AppBackground.jsx'))

const NAV = [
  { to: '/', label: '챗봇', icon: MessageCircleHeart, end: true },
  { to: '/benefits', label: '혜택 추천', icon: Gift },
  { to: '/map', label: '내 주변', icon: MapPinned },
]

/** 메뉴 링크. 챗봇 화면에서 '챗봇'을 다시 누르면 새 대화를 시작한다. */
function NavLinks({ iconSize }) {
  const { startNew } = useChatHistory()
  return NAV.map(({ to, label, icon: Icon, end }) => (
    <NavLink key={to} to={to} end={end} onClick={to === '/' ? startNew : undefined}>
      <Icon size={iconSize} strokeWidth={1.8} />
      <span>{label}</span>
    </NavLink>
  ))
}

export default function App() {
  return (
    <BrowserRouter>
      <RegionProvider>
      <ChatHistoryProvider>
        <div className="app-bg" aria-hidden="true">
          <Suspense fallback={null}>
            <AppBackground />
          </Suspense>
          <div className="app-bg-wash" />
        </div>

        <div className="shell">
          <aside className="sidebar glass">
            <div className="brand">
              <BrandMark />
              <div>
                <strong>의료·복지 안내</strong>
                <span>AI 에이전트</span>
              </div>
            </div>
            <div className="side-region">
              <span>내 지역</span>
              <RegionSelect />
            </div>
            <nav className="side-nav">
              <NavLinks iconSize={20} />
            </nav>
            <ConversationList />
            <p className="side-note">
              <ShieldCheck size={16} strokeWidth={1.8} />
              공공데이터 기반 정보 안내 서비스로, 진단이나 처방을 하지 않아요.
            </p>
          </aside>

          <main className="content">
            <Routes>
              <Route path="/" element={<ChatPage />} />
              <Route path="/benefits" element={<BenefitsPage />} />
              <Route path="/map" element={<MapPage />} />
              <Route path="/facilities/:id" element={<FacilityDetailPage />} />
            </Routes>
          </main>
        </div>

        <nav className="tabbar glass">
          <NavLinks iconSize={22} />
        </nav>
      </ChatHistoryProvider>
      </RegionProvider>
    </BrowserRouter>
  )
}
