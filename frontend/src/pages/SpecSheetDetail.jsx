import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api from "../api";
import { useUser } from "../context/UserContext";

const STATUS_LABEL = {
  UPLOADED: "업로드됨",
  VALIDATED: "검증완료",
  IN_QA: "질의응답중",
  RESOLVED: "해결됨",
};

const QA_STATUS_LABEL = {
  OPEN: "미답변",
  TECH_ANSWERED: "답변완료(설계사 검토 대기)",
  ANSWER_APPROVED: "답변승인(값 수정 대기)",
  VALUE_PROPOSED: "값 제안됨(최종승인 대기)",
  RESOLVED: "해결됨",
  REJECTED: "반려됨",
};

function buildGrid(fields) {
  let maxRow = 0;
  let maxCol = 0;
  const map = {};
  fields.forEach((f) => {
    maxRow = Math.max(maxRow, f.row_index);
    maxCol = Math.max(maxCol, f.col_index);
    map[`${f.row_index}_${f.col_index}`] = f;
  });
  return { maxRow, maxCol, map };
}

export default function SpecSheetDetail() {
  const { id } = useParams();
  const [sheet, setSheet] = useState(null);
  const [threads, setThreads] = useState([]);
  const [aggregation, setAggregation] = useState([]);
  const [modal, setModal] = useState(null); // { specFieldId, validationResultId, title }
  const [busy, setBusy] = useState(false);

  const load = () => {
    api.get(`/spec-sheets/${id}`).then((res) => setSheet(res.data));
    api.get(`/spec-sheets/${id}/qa-threads`).then((res) => setThreads(res.data));
    api.get(`/spec-sheets/${id}/aggregation`).then((res) => setAggregation(res.data));
  };

  useEffect(load, [id]);

  if (!sheet) return <p className="muted">불러오는 중...</p>;

  const { maxRow, maxCol, map } = buildGrid(sheet.fields);
  const openResults = sheet.validation_results.filter(
    (r) => r.status !== "RESOLVED" && r.status !== "DISMISSED"
  );
  const flagByFieldId = {};
  openResults.forEach((r) => {
    if (!r.spec_field_id) return;
    const cur = flagByFieldId[r.spec_field_id];
    if (!cur || r.severity === "ERROR") flagByFieldId[r.spec_field_id] = r.severity;
  });

  const runValidation = async () => {
    setBusy(true);
    try {
      await api.post(`/spec-sheets/${id}/validate`);
      load();
    } finally {
      setBusy(false);
    }
  };

  const openThreadModalForResult = (result) => {
    const field = sheet.fields.find((f) => f.id === result.spec_field_id);
    setModal({
      specFieldId: result.spec_field_id,
      validationResultId: result.id,
      title: `[검증 이슈] ${field?.field_name || ""}: ${result.message}`,
      question: `이 항목의 값 "${field?.value ?? ""}" 이(가) 맞는지 확인 부탁드립니다.\n(자동 검증 메시지: ${result.message})`,
    });
  };

  const openThreadModalForField = (field) => {
    setModal({
      specFieldId: field.id,
      validationResultId: null,
      title: `[문의] ${field.field_name || `R${field.row_index}C${field.col_index}`}`,
      question: `"${field.field_name || ""}" 값 "${field.value}" 확인 부탁드립니다.`,
    });
  };

  return (
    <div>
      <h1>
        {sheet.title}{" "}
        <span className={`badge status-${sheet.status}`}>{STATUS_LABEL[sheet.status]}</span>
      </h1>
      <p className="muted">
        {sheet.major_process.name} · {sheet.construction_code}
        {sheet.equipment_module ? ` · ${sheet.equipment_module}` : ""} · v{sheet.version} · 업로더{" "}
        {sheet.uploaded_by || "-"}
      </p>

      <div className="panel" style={{ display: "flex", gap: 8 }}>
        <button className="btn primary" onClick={runValidation} disabled={busy}>
          {busy ? "검증 실행 중..." : "규칙 검증 실행"}
        </button>
        <a className="btn" href={`/api/spec-sheets/${id}/export`}>
          엑셀로 내보내기 (이슈 색상 표시)
        </a>
        <button
          className="btn"
          onClick={() =>
            setModal({ specFieldId: null, validationResultId: null, title: "", question: "" })
          }
        >
          + 새 질의 등록
        </button>
      </div>

      <div className="grid-2">
        <div className="panel">
          <h2>제원표 (CAD 레이아웃 보존)</h2>
          <p className="muted">빨강/노랑 배경 셀을 클릭하면 해당 항목에 대해 질의를 등록할 수 있습니다.</p>
          <div className="table-wrap">
            <table>
              <tbody>
                {Array.from({ length: maxRow }, (_, ri) => ri + 1).map((row) => (
                  <tr key={row}>
                    {Array.from({ length: maxCol }, (_, ci) => ci + 1).map((col) => {
                      const f = map[`${row}_${col}`];
                      const severity = f ? flagByFieldId[f.id] : null;
                      return (
                        <td
                          key={col}
                          className={severity ? `cell-flag-${severity}` : ""}
                          onClick={() => f && severity && openThreadModalForField(f)}
                          title={f?.field_name ? `${f.field_name}${f.unit ? ` (${f.unit})` : ""}` : ""}
                        >
                          {f?.value ?? ""}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div>
          <div className="panel">
            <h2>제원 총량 집계</h2>
            {aggregation.length === 0 ? (
              <p className="muted">집계할 데이터가 없습니다 (대분류별 성상/전원종류/자재명이 채워진 항목이 필요).</p>
            ) : (
              aggregation.map((a) => (
                <div key={a.category} style={{ marginBottom: 12 }}>
                  <div style={{ fontWeight: 600, fontSize: 13 }}>
                    {a.category} <span className="muted">({a.group_by}별, {a.unit}, {a.distinct_count}종)</span>
                  </div>
                  <table>
                    <tbody>
                      {Object.entries(a.totals).map(([group, total]) => (
                        <tr key={group}>
                          <td>{group}</td>
                          <td style={{ textAlign: "right", fontWeight: 600 }}>
                            {total.toLocaleString(undefined, { maximumFractionDigits: 2 })} {a.unit}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ))
            )}
          </div>

          <div className="panel">
            <h2>검증 결과 ({openResults.length}건 미해결)</h2>
            {sheet.validation_results.length === 0 ? (
              <p className="muted">아직 검증을 실행하지 않았습니다.</p>
            ) : (
              sheet.validation_results.map((r) => (
                <div key={r.id} style={{ borderBottom: "1px solid var(--border)", padding: "8px 0" }}>
                  <span className={`badge sev-${r.severity}`}>{r.severity}</span>{" "}
                  <span className="badge" style={{ background: "#eef2f6" }}>
                    {r.status}
                  </span>
                  <div style={{ fontSize: 13, margin: "4px 0" }}>{r.message}</div>
                  {r.suggested_value != null && (
                    <div className="muted" style={{ fontSize: 12 }}>제안값: {r.suggested_value} (자동 질의 대상)</div>
                  )}
                  {r.status !== "RESOLVED" && r.status !== "DISMISSED" && (
                    <button className="btn" onClick={() => openThreadModalForResult(r)}>
                      질문하기
                    </button>
                  )}
                </div>
              ))
            )}
          </div>

          <div className="panel">
            <h2>질의응답 스레드 ({threads.length}건)</h2>
            <p className="muted" style={{ marginTop: 0 }}>
              답변/승인 등 실제 처리는 <Link to="/queries">질의응답 관리</Link> 화면에서 진행합니다.
            </p>
            {threads.length === 0 ? (
              <p className="muted">등록된 질의가 없습니다.</p>
            ) : (
              threads.map((t) => (
                <Link key={t.id} to={`/queries?thread=${t.id}`} className="thread-card" style={{ display: "block", textDecoration: "none", color: "inherit" }}>
                  <span className={`badge qa-${t.status === "RESOLVED" || t.status === "REJECTED" ? "RESOLVED" : t.status === "OPEN" ? "OPEN" : "ANSWERED"}`}>
                    {QA_STATUS_LABEL[t.status]}
                  </span>{" "}
                  <span className="badge" style={{ background: t.query_type === "AUTO" ? "#ddeeff" : "#f0f2f5" }}>
                    {t.query_type === "AUTO" ? "자동" : "수동"}
                  </span>
                  <div style={{ fontWeight: 600, fontSize: 13, margin: "4px 0" }}>{t.title}</div>
                  <div className="muted">담당자: {t.assigned_owner?.name || "미배정"}</div>
                </Link>
              ))
            )}
          </div>
        </div>
      </div>

      {modal && (
        <ThreadCreateModal
          sheetId={id}
          majorProcessId={sheet.major_process.id}
          initial={modal}
          onClose={() => setModal(null)}
          onCreated={() => {
            setModal(null);
            load();
          }}
        />
      )}
    </div>
  );
}

function ThreadCreateModal({ sheetId, majorProcessId, initial, onClose, onCreated }) {
  const { owners, disciplines, currentUser } = useUser();
  const [title, setTitle] = useState(initial.title || "");
  const [question, setQuestion] = useState(initial.question || "");
  const [disciplineId, setDisciplineId] = useState(
    currentUser?.role === "DESIGNER" && currentUser.disciplines.length === 1
      ? String(currentUser.disciplines[0].id)
      : ""
  );
  const [assignedOwnerId, setAssignedOwnerId] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const candidates = owners.filter(
    (o) => o.role === "TECH_LEAD" && o.major_processes.some((mp) => mp.id === majorProcessId)
  );

  const submit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      await api.post(`/spec-sheets/${sheetId}/qa-threads`, {
        title,
        discipline_id: Number(disciplineId),
        spec_field_id: initial.specFieldId,
        validation_result_id: initial.validationResultId,
        assigned_owner_id: assignedOwnerId || null,
        question,
        author_name: currentUser?.name || "익명",
      });
      onCreated();
    } catch (err) {
      setError(err.response?.data?.detail || "등록 실패");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>수동 질의 등록</h2>
        <p className="muted">설계사가 직접 서술형으로 질의합니다. 기술팀 답변 → 설계사 승인 → 값 수정 → 최종 승인 순서로 처리됩니다.</p>
        <form onSubmit={submit}>
          <div className="field">
            <label>제목</label>
            <input value={title} onChange={(e) => setTitle(e.target.value)} required />
          </div>
          <div className="field">
            <label>공종</label>
            <select value={disciplineId} onChange={(e) => setDisciplineId(e.target.value)} required>
              <option value="" disabled>선택하세요</option>
              {disciplines.map((d) => (
                <option key={d.id} value={d.id}>{d.name}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>질문 내용</label>
            <textarea rows={4} value={question} onChange={(e) => setQuestion(e.target.value)} required />
          </div>
          <div className="field">
            <label>담당 기술팀 지정 (선택 - 비우면 대공정 담당자 중 자동/미배정)</label>
            <select value={assignedOwnerId} onChange={(e) => setAssignedOwnerId(e.target.value)}>
              <option value="">자동</option>
              {candidates.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.name}
                </option>
              ))}
            </select>
          </div>
          {error && <p className="error-text">{error}</p>}
          <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
            <button className="btn primary" type="submit" disabled={submitting}>
              등록
            </button>
            <button className="btn" type="button" onClick={onClose}>
              취소
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
