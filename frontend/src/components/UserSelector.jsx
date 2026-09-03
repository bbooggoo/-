import { useUser } from "../context/UserContext";

export default function UserSelector() {
  const { owners, currentUserId, setCurrentUserId } = useUser();

  return (
    <select
      value={currentUserId}
      onChange={(e) => setCurrentUserId(e.target.value)}
      style={{ width: 220 }}
      title="로그인 없이 데모용으로 현재 작업자를 선택합니다. 대공정별 담당자만 해당 건에 답변/해결할 수 있습니다."
    >
      <option value="">(사용자 미선택 - 열람만)</option>
      {owners.map((o) => (
        <option key={o.id} value={o.id}>
          {o.name} {o.major_processes.length ? `(${o.major_processes.map((m) => m.code).join(", ")})` : ""}
        </option>
      ))}
    </select>
  );
}
