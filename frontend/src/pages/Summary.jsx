import { useEffect, useState } from "react";
import api from "../api";
import { useUser } from "../context/UserContext";

const GCS_CATEGORIES = ["SPECIALITY GAS", "폐액"];

export default function Summary() {
  const { currentUser, majorProcesses } = useUser();
  const [filterMp, setFilterMp] = useState("");
  const [autoApplied, setAutoApplied] = useState(false);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);

  // item 5: 담당자(기술팀)가 바뀌면 SUMMARY도 그 담당자의 대공정으로 자동 전환.
  useEffect(() => {
    if (currentUser?.role === "TECH_LEAD" && currentUser.major_processes.length === 1) {
      setFilterMp(String(currentUser.major_processes[0].id));
      setAutoApplied(true);
    } else if (autoApplied) {
      setFilterMp("");
      setAutoApplied(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentUser?.id]);

  useEffect(() => {
    setLoading(true);
    const params = {};
    if (filterMp) params.major_process_id = filterMp;
    api
      .get("/summary", { params })
      .then((res) => setSummary(res.data))
      .finally(() => setLoading(false));
  }, [filterMp]);

  return (
    <div>
      <h1>제원 SUMMARY</h1>
      <p className="muted">
        담당자(대공정)별로 제원 총량 집계, 미해결 이슈/질의 건수를 한 장으로 봅니다. GCS(SPECIALITY GAS +
        폐액(CCSS))는 종수(자재명 개수)가 중요한 지표라 따로 집계합니다.
      </p>

      <div className="panel">
        {autoApplied && (
          <p className="muted" style={{ marginTop: 0 }}>
            {currentUser.name} 님의 담당 대공정으로 자동 필터링됨 — 아래에서 직접 바꿀 수 있습니다.
          </p>
        )}
        <div className="field" style={{ maxWidth: 280 }}>
          <label>대공정</label>
          <select
            value={filterMp}
            onChange={(e) => { setFilterMp(e.target.value); setAutoApplied(false); }}
          >
            <option value="">전체</option>
            {majorProcesses.map((mp) => (
              <option key={mp.id} value={mp.id}>{mp.name}</option>
            ))}
          </select>
        </div>
      </div>

      {loading || !summary ? (
        <p className="muted">불러오는 중...</p>
      ) : (
        <>
          <div className="panel" style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
            <Stat label="제원표" value={`${summary.sheet_count}건`} />
            <Stat
              label="미해결 검증 이슈"
              value={`${summary.open_issue_count}건`}
              tone={summary.open_issue_count > 0 ? "error" : "ok"}
            />
            <Stat
              label="미해결 자동 질의"
              value={`${summary.open_auto_query_count}건`}
              tone={summary.open_auto_query_count > 0 ? "warn" : "ok"}
            />
            <Stat
              label="미해결 수동 질의"
              value={`${summary.open_manual_query_count}건`}
              tone={summary.open_manual_query_count > 0 ? "warn" : "ok"}
            />
            <Stat label="GCS 종수 (SPECIALITY GAS + 폐액)" value={`${summary.gcs_material_count}종`} tone="primary" />
          </div>

          {summary.gcs_materials.length > 0 && (
            <div className="panel">
              <h2>GCS 자재 목록</h2>
              <p className="muted" style={{ marginTop: 0 }}>
                {summary.gcs_materials.join(", ")}
              </p>
            </div>
          )}

          <div className="panel">
            <h2>대분류별 총량 집계</h2>
            {summary.categories.length === 0 ? (
              <p className="muted">집계할 데이터가 없습니다.</p>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>대분류</th>
                    <th>그룹 기준</th>
                    <th>종수</th>
                    <th>값</th>
                    <th>단위</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.categories.map((c) => (
                    <tr key={c.category}>
                      <td>
                        {c.category}
                        {GCS_CATEGORIES.includes(c.category) && (
                          <span className="badge" style={{ background: "#ddeeff", marginLeft: 6 }}>GCS</span>
                        )}
                      </td>
                      <td className="muted">{c.group_by}</td>
                      <td>{c.distinct_count}</td>
                      <td>
                        {Object.entries(c.totals)
                          .sort()
                          .map(([k, v]) => `${k}: ${v.toLocaleString()}`)
                          .join(", ")}
                      </td>
                      <td className="muted">{c.unit}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}
    </div>
  );
}

function Stat({ label, value, tone }) {
  const color =
    tone === "error" ? "var(--error)" : tone === "warn" ? "var(--warn)" : tone === "primary" ? "var(--primary)" : "var(--ok)";
  return (
    <div>
      <div className="muted" style={{ fontSize: 12 }}>{label}</div>
      <div style={{ fontSize: 22, fontWeight: 700, color }}>{value}</div>
    </div>
  );
}
