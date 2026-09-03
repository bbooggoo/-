import { NavLink, Outlet } from "react-router-dom";
import UserSelector from "./UserSelector";

export default function Layout() {
  return (
    <div className="app-shell">
      <div className="topbar">
        <div className="brand">🏭 반도체 제원 Q&A 플랫폼</div>
        <nav>
          <NavLink to="/" end>
            대시보드
          </NavLink>
          <NavLink to="/upload">제원표 업로드</NavLink>
          <NavLink to="/rules">검증 규칙</NavLink>
          <NavLink to="/owners">담당자 관리</NavLink>
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
