import { NavLink, Outlet } from "react-router-dom";
import { useUser } from "../context/UserContext";
import UserSelector from "./UserSelector";

export default function Layout() {
  const { currentUser } = useUser();
  // 관리자만 업로드 가능 (item 6). 사용자 미선택(데모 게스트)일 때도 눌러보고 나서
  // 서버가 401로 막아주므로, 메뉴 자체는 숨기지 않고 살짝 표시만 다르게 한다.
  const isAdmin = currentUser?.role === "ADMIN";

  return (
    <div className="app-shell">
      <div className="topbar">
        <div className="brand">🏭 반도체 제원 Q&A 플랫폼</div>
        <nav>
          <NavLink to="/" end>
            대시보드
          </NavLink>
          <NavLink to="/summary">SUMMARY</NavLink>
          <NavLink to="/queries">질의응답</NavLink>
          <NavLink to="/upload" style={isAdmin ? undefined : { opacity: 0.6 }}>
            제원표 업로드{!isAdmin && " (관리자 전용)"}
          </NavLink>
          <NavLink to="/rules">검증 규칙</NavLink>
          <NavLink to="/owners">사용자 관리</NavLink>
          <NavLink to="/corrections">수정 이력</NavLink>
        </nav>
        <UserSelector />
      </div>
      <div className="main">
        <Outlet />
      </div>
    </div>
  );
}
