import { useState } from "react";
import api from "../api";
import { useUser } from "../context/UserContext";

const ROLE_LABEL = { ADMIN: "관리자", DESIGNER: "설계사", TECH_LEAD: "기술팀 담당자" };
const ROLES = ["TECH_LEAD", "DESIGNER", "ADMIN"];

export default function Owners() {
  const { owners, refreshOwners, majorProcesses, disciplines } = useUser();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("TECH_LEAD");
  const [selectedMps, setSelectedMps] = useState([]);
  const [selectedDisciplines, setSelectedDisciplines] = useState([]);
  const [error, setError] = useState("");

  const toggle = (setter) => (id) => {
    setter((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  };

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      await api.post("/owners", {
        name,
        email: email || null,
        role,
        major_process_ids: role === "TECH_LEAD" ? selectedMps : [],
        discipline_ids: role === "DESIGNER" ? selectedDisciplines : [],
      });
      setName("");
      setEmail("");
      setSelectedMps([]);
      setSelectedDisciplines([]);
      refreshOwners();
    } catch (err) {
      setError(err.response?.data?.detail || "등록 실패");
    }
  };

  return (
    <div>
      <h1>사용자 관리</h1>
      <p className="muted">
        <b>관리자</b>는 모든 데이터를 열람하고 제원표를 업로드할 수 있는 유일한 역할입니다. <b>기술팀
        담당자</b>는 대공정별로 질의에 답변/승인합니다. <b>설계사</b>는 공종별로 질의를 제기하고
        답변/최종값을 승인합니다.
      </p>

      <div className="grid-2">
        <div className="panel">
          <h2>사용자 목록</h2>
          <table>
            <thead>
              <tr>
                <th>이름</th>
                <th>역할</th>
                <th>담당 대공정 / 공종</th>
              </tr>
            </thead>
            <tbody>
              {owners.map((o) => (
                <tr key={o.id}>
                  <td>{o.name}</td>
                  <td>
                    <span className="badge" style={{ background: "#eef2f6" }}>
                      {ROLE_LABEL[o.role] || o.role}
                    </span>
                  </td>
                  <td>
                    {o.major_processes.map((mp) => (
                      <span key={mp.id} className="badge" style={{ background: "#eef2f6", marginRight: 4 }}>
                        {mp.code}
                      </span>
                    ))}
                    {o.disciplines.map((d) => (
                      <span key={d.id} className="badge" style={{ background: "#eef2f6", marginRight: 4 }}>
                        {d.name}
                      </span>
                    ))}
                    {!o.major_processes.length && !o.disciplines.length && (
                      <span className="muted">-</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="panel">
          <h2>사용자 추가</h2>
          <form onSubmit={submit}>
            <div className="field">
              <label>이름</label>
              <input value={name} onChange={(e) => setName(e.target.value)} required />
            </div>
            <div className="field">
              <label>이메일 (선택)</label>
              <input value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
            <div className="field">
              <label>역할</label>
              <select value={role} onChange={(e) => setRole(e.target.value)}>
                {ROLES.map((r) => (
                  <option key={r} value={r}>
                    {ROLE_LABEL[r]}
                  </option>
                ))}
              </select>
            </div>

            {role === "TECH_LEAD" && (
              <div className="field">
                <label>담당 대공정</label>
                {majorProcesses.map((mp) => (
                  <div className="checkbox-row" key={mp.id}>
                    <input
                      type="checkbox"
                      checked={selectedMps.includes(mp.id)}
                      onChange={() => toggle(setSelectedMps)(mp.id)}
                      id={`mp-${mp.id}`}
                    />
                    <label htmlFor={`mp-${mp.id}`} style={{ margin: 0 }}>
                      {mp.name}
                    </label>
                  </div>
                ))}
              </div>
            )}

            {role === "DESIGNER" && (
              <div className="field">
                <label>담당 공종</label>
                {disciplines.map((d) => (
                  <div className="checkbox-row" key={d.id}>
                    <input
                      type="checkbox"
                      checked={selectedDisciplines.includes(d.id)}
                      onChange={() => toggle(setSelectedDisciplines)(d.id)}
                      id={`disc-${d.id}`}
                    />
                    <label htmlFor={`disc-${d.id}`} style={{ margin: 0 }}>
                      {d.name}
                    </label>
                  </div>
                ))}
              </div>
            )}

            {role === "ADMIN" && (
              <p className="muted">관리자는 대공정/공종 제한 없이 모든 데이터를 봅니다.</p>
            )}

            {error && <p className="error-text">{error}</p>}
            <button className="btn primary" type="submit">
              추가
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
