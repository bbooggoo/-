import { useEffect, useState } from "react";
import api from "../api";
import { useUser } from "../context/UserContext";

export default function Owners() {
  const { owners, refreshOwners } = useUser();
  const [majorProcesses, setMajorProcesses] = useState([]);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [selectedMps, setSelectedMps] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/major-processes").then((res) => setMajorProcesses(res.data));
  }, []);

  const toggleMp = (id) => {
    setSelectedMps((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  };

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      await api.post("/owners", { name, email: email || null, major_process_ids: selectedMps });
      setName("");
      setEmail("");
      setSelectedMps([]);
      refreshOwners();
    } catch (err) {
      setError(err.response?.data?.detail || "등록 실패");
    }
  };

  return (
    <div>
      <h1>담당자 관리</h1>
      <p className="muted">대공정마다 담당자가 다르므로, 담당자별로 담당할 대공정(복수 가능)을 지정합니다.</p>

      <div className="grid-2">
        <div className="panel">
          <h2>담당자 목록</h2>
          <table>
            <thead>
              <tr>
                <th>이름</th>
                <th>이메일</th>
                <th>담당 대공정</th>
              </tr>
            </thead>
            <tbody>
              {owners.map((o) => (
                <tr key={o.id}>
                  <td>{o.name}</td>
                  <td className="muted">{o.email || "-"}</td>
                  <td>
                    {o.major_processes.map((mp) => (
                      <span key={mp.id} className="badge" style={{ background: "#eef2f6", marginRight: 4 }}>
                        {mp.code}
                      </span>
                    ))}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="panel">
          <h2>담당자 추가</h2>
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
              <label>담당 대공정</label>
              {majorProcesses.map((mp) => (
                <div className="checkbox-row" key={mp.id}>
                  <input
                    type="checkbox"
                    checked={selectedMps.includes(mp.id)}
                    onChange={() => toggleMp(mp.id)}
                    id={`mp-${mp.id}`}
                  />
                  <label htmlFor={`mp-${mp.id}`} style={{ margin: 0 }}>
                    {mp.name}
                  </label>
                </div>
              ))}
            </div>
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
