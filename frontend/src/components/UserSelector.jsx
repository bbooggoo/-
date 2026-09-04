import { useUser } from "../context/UserContext";

const ROLE_LABEL = { ADMIN: "관리자", DESIGNER: "설계사", TECH_LEAD: "기술팀 담당자" };

function ownerLabel(o) {
  const role = ROLE_LABEL[o.role] || o.role;
  if (o.role === "TECH_LEAD" && o.major_processes.length) {
    return `${o.name} · ${role} (${o.major_processes.map((m) => m.code).join(", ")})`;
  }
  if (o.role === "DESIGNER" && o.disciplines.length) {
    return `${o.name} · ${role} (${o.disciplines.map((d) => d.name).join(", ")})`;
  }
  return `${o.name} · ${role}`;
}

export default function UserSelector() {
  const { owners, currentUserId, setCurrentUserId } = useUser();

  return (
    <select
      value={currentUserId}
      onChange={(e) => setCurrentUserId(e.target.value)}
      style={{ width: 260 }}
      title="로그인 없이 데모용으로 현재 사용자를 선택합니다. 관리자는 전체 열람+업로드, 기술팀은 담당 대공정만 답변/승인, 설계사는 담당 공종 질의만 승인할 수 있습니다."
    >
      <option value="">(사용자 미선택 - 열람만)</option>
      {owners.map((o) => (
        <option key={o.id} value={o.id}>
          {ownerLabel(o)}
        </option>
      ))}
    </select>
  );
}
