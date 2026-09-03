import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api";

const STATUS_LABEL = {
  UPLOADED: "업로드됨",
  VALIDATED: "검증완료",
  IN_QA: "질의응답중",
  RESOLVED: "해결됨",
};

export default function Dashboard() {
  const [sheets, setSheets] = useState([]);
  const [majorProcesses, setMajorProcesses] = useState([]);
  const [filterMp, setFilterMp] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/major-processes").then((res) => setMajorProcesses(res.data));
  }, []);

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

      <div className="panel">
        <div className="form-row">
          <div className="field" style={{ marginBottom: 0 }}>
            <label>대공정 필터</label>
            <select value={filterMp} onChange={(e) => setFilterMp(e.target.value)}>
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
                  <td>{s.equipment_module}</td>
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
