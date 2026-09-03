import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import api from "../api";
import { useUser } from "../context/UserContext";

const STATUS_LABEL = {
  UPLOADED: "업로드됨",
  VALIDATED: "검증완료",
  IN_QA: "질의응답중",
  RESOLVED: "해결됨",
};

const QA_STATUS_LABEL = { OPEN: "미답변", ANSWERED: "답변완료(미해결)", RESOLVED: "해결됨" };

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
  const { currentUser } = useUser();
  const [sheet, setSheet] = useState(null);
  const [threads, setThreads] = useState([]);
  const [activeThreadId, setActiveThreadId] = useState(null);
  const [modal, setModal] = useState(null); // { specFieldId, validationResultId, title }
  const [busy, setBusy] = useState(false);

  const load = () => {
    api.get(`/spec-sheets/${id}`).then((res) => setSheet(res.data));
    api.get(`/spec-sheets/${id}/qa-threads`).then((res) => setThreads(res.data));
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
  const resultsByFieldId = {};
  sheet.validation_results.forEach((r) => {
    if (!r.spec_field_id) return;
    (resultsByFieldId[r.spec_field_id] ||= []).push(r);
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
            {threads.length === 0 ? (
              <p className="muted">등록된 질의가 없습니다.</p>
            ) : (
              threads.map((t) => (
                <div key={t.id} className="thread-card" onClick={() => setActiveThreadId(t.id)}>
                  <span className={`badge qa-${t.status}`}>{QA_STATUS_LABEL[t.status]}</span>
                  <div style={{ fontWeight: 600, fontSize: 13, margin: "4px 0" }}>{t.title}</div>
                  <div className="muted">담당자: {t.assigned_owner?.name || "미배정"}</div>
                </div>
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

      {activeThreadId && (
        <ThreadDetailModal
          threadId={activeThreadId}
          currentUser={currentUser}
          onClose={() => setActiveThreadId(null)}
          onChanged={load}
        />
      )}
    </div>
  );
}

function ThreadCreateModal({ sheetId, majorProcessId, initial, onClose, onCreated }) {
  const { owners, currentUser } = useUser();
  const [title, setTitle] = useState(initial.title || "");
  const [question, setQuestion] = useState(initial.question || "");
  const [assignedOwnerId, setAssignedOwnerId] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const candidates = owners.filter((o) => o.major_processes.some((mp) => mp.id === majorProcessId));

  const submit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      await api.post(`/spec-sheets/${sheetId}/qa-threads`, {
        title,
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
        <h2>질의 등록</h2>
        <form onSubmit={submit}>
          <div className="field">
            <label>제목</label>
            <input value={title} onChange={(e) => setTitle(e.target.value)} required />
          </div>
          <div className="field">
            <label>질문 내용</label>
            <textarea rows={4} value={question} onChange={(e) => setQuestion(e.target.value)} required />
          </div>
          <div className="field">
            <label>담당자 지정 (선택 - 비우면 대공정 담당자 중 자동/미배정)</label>
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

function ThreadDetailModal({ threadId, currentUser, onClose, onChanged }) {
  const [thread, setThread] = useState(null);
  const [content, setContent] = useState("");
  const [newValue, setNewValue] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = () => api.get(`/qa-threads/${threadId}`).then((res) => setThread(res.data));
  useEffect(load, [threadId]);

  if (!thread) return null;

  const isAssignedOwner = currentUser && thread.assigned_owner && currentUser.id === thread.assigned_owner.id;

  const sendMessage = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api.post(`/qa-threads/${threadId}/messages`, {
        author_name: currentUser?.name || "익명",
        role: isAssignedOwner ? "ANSWER" : "QUESTION",
        content,
      });
      setContent("");
      load();
      onChanged();
    } catch (err) {
      setError(err.response?.data?.detail || "전송 실패");
    } finally {
      setBusy(false);
    }
  };

  const resolve = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api.post(`/qa-threads/${threadId}/resolve`, {
        resolver_name: currentUser?.name || "익명",
        new_value: newValue || null,
        note: note || null,
      });
      load();
      onChanged();
    } catch (err) {
      setError(err.response?.data?.detail || "해결 처리 실패");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" style={{ width: 520 }} onClick={(e) => e.stopPropagation()}>
        <h2>{thread.title}</h2>
        <p className="muted">
          담당자: {thread.assigned_owner?.name || "미배정"} · 상태: {QA_STATUS_LABEL[thread.status]}
        </p>

        <div style={{ maxHeight: 260, overflow: "auto", margin: "12px 0" }}>
          {thread.messages.map((m) => (
            <div key={m.id} className={`message role-${m.role}`}>
              <div className="meta">
                {m.author_name} · {m.role} · {new Date(m.created_at).toLocaleString()}
              </div>
              <div style={{ whiteSpace: "pre-wrap" }}>{m.content}</div>
            </div>
          ))}
        </div>

        {thread.status !== "RESOLVED" && (
          <form onSubmit={sendMessage} className="field">
            <label>{isAssignedOwner ? "답변 작성 (담당자)" : "추가 문의"}</label>
            <textarea rows={3} value={content} onChange={(e) => setContent(e.target.value)} required />
            <button className="btn primary" type="submit" disabled={busy} style={{ marginTop: 8 }}>
              전송
            </button>
          </form>
        )}

        {thread.status !== "RESOLVED" && isAssignedOwner && (
          <form onSubmit={resolve} className="panel" style={{ marginTop: 12 }}>
            <h2>해결 처리</h2>
            <div className="field">
              <label>수정 값 (제원 반영, 선택)</label>
              <input value={newValue} onChange={(e) => setNewValue(e.target.value)} placeholder="비우면 값 변경 없이 해결" />
            </div>
            <div className="field">
              <label>메모 (선택)</label>
              <input value={note} onChange={(e) => setNote(e.target.value)} />
            </div>
            <button className="btn primary" type="submit" disabled={busy}>
              해결로 표시
            </button>
          </form>
        )}

        {thread.status !== "RESOLVED" && !isAssignedOwner && (
          <p className="muted">
            이 대공정 담당자만 답변/해결 처리를 할 수 있습니다. 상단에서 담당자를 선택해 주세요.
          </p>
        )}

        {error && <p className="error-text">{error}</p>}

        <button className="btn" onClick={onClose} style={{ marginTop: 12 }}>
          닫기
        </button>
      </div>
    </div>
  );
}
