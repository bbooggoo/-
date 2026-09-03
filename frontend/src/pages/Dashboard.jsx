import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api";
import { useUser } from "../context/UserContext";

const STATUS_LABEL = {
  UPLOADED: "업로드됨",
  VALIDATED: "검증완료",
  IN_QA: "질의응답중",
  RESOLVED: "해결됨",
};

export default function Dashboard() {
  const { currentUser, majorProcesses } = useUser();
  const [sheets, setSheets] = useState([]);
  const [filterMp, setFilterMp] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [autoFiltered, setAutoFiltered] = useState(false);
  const [loading, setLoading] = useState(true);

  // item 5 수정: 담당자(기술팀)가 바뀌면 대시보드도 그 담당자의 대공정으로 자동 필터링된다.
  // 관리자/설계사/미선택이면 필터를 건드리지 않는다(관리자는 전체를 봐야 하니까).
  useEffect(() => {
    if (currentUser?.role === "TECH_LEAD" && currentUser.major_processes.length === 1) {
      setFilterMp(String(currentUser.major_processes[0].id));
      setAutoFiltered(true);
    } else if (autoFiltered) {
      // 이전에 자동 필터링됐던 상태에서 다른(비-TECH_LEAD) 사용자로 바뀌면 필터를 풀어준다.
      setFilterMp("");
      setAutoFiltered(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentUser?.id]);

  const load = () => {
    setLoading(true);
    const params = {};
    if (filterMp) params.major_process_id = filterMp;
    if (filterStatus) params.status = filterStatus;
    api
      .get("/spec-sheets", { params })
      .then((res) => setSheets(res.data))
      .finally(() => setLoading(false));
  };

  useEffect(load, [filterMp, filterStatus]);

  return (
    <div>
      <h1>제원표 대시보드</h1>
      {currentUser?.role === "TECH_LEAD" && autoFiltered && (
        <p className="muted">
          {currentUser.name} 님의 담당 대공정({currentUser.major_processes[0]?.name})으로 자동 필터링됨 —
          아래에서 직접 바꿀 수 있습니다.
        </p>
      )}

      <div className="panel">
        <div className="form-row">
          <div className="field" style={{ marginBottom: 0 }}>
            <label>대공정 필터</label>
            <select
              value={filterMp}
              onChange={(e) => {
                setFilterMp(e.target.value);
                setAutoFiltered(false);
              }}
            >
              <option value="">전체</option>
              {majorProcesses.map((mp) => (
                <option key={mp.id} value={mp.id}>
                  {mp.name}
                </option>
              ))}
            </select>
          </div>
          <div className="field" style={{ marginBottom: 0 }}>
            <label>상태 필터</label>
            <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}>
              <option value="">전체</option>
              {Object.entries(STATUS_LABEL).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      <div className="panel">
        {loading ? (
          <p className="muted">불러오는 중...</p>
        ) : sheets.length === 0 ? (
          <p className="muted">등록된 제원표가 없습니다. 상단 메뉴에서 업로드해 보세요.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>대공정</th>
                <th>건설코드</th>
                <th>설비모듈</th>
                <th>제목</th>
                <th>버전</th>
                <th>상태</th>
                <th>미해결 이슈</th>
                <th>업로드</th>
              </tr>
            </thead>
            <tbody>
              {sheets.map((s) => (
                <tr key={s.id}>
                  <td>{s.major_process.name}</td>
                  <td>{s.construction_code}</td>
                  <td className={s.equipment_module ? "" : "muted"}>{s.equipment_module || "-"}</td>
                  <td>
                    <Link to={`/spec-sheets/${s.id}`}>{s.title}</Link>
                  </td>
                  <td>v{s.version}</td>
                  <td>
                    <span className={`badge status-${s.status}`}>{STATUS_LABEL[s.status]}</span>
                  </td>
                  <td>
                    {s.open_issue_count > 0 ? (
                      <span className="badge sev-ERROR">{s.open_issue_count}건</span>
                    ) : (
                      <span className="muted">-</span>
                    )}
                  </td>
                  <td className="muted">{s.uploaded_by || "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
