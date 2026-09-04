import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import api from "../api";
import { useUser } from "../context/UserContext";

const STATUS_LABEL = {
  OPEN: "미답변",
  TECH_ANSWERED: "답변완료(설계사 검토 대기)",
  ANSWER_APPROVED: "답변승인(값 수정 대기)",
  VALUE_PROPOSED: "값 제안됨(최종승인 대기)",
  RESOLVED: "해결됨",
  REJECTED: "반려됨",
};
const STATUS_BADGE = {
  OPEN: "qa-OPEN",
  TECH_ANSWERED: "qa-ANSWERED",
  ANSWER_APPROVED: "qa-ANSWERED",
  VALUE_PROPOSED: "qa-ANSWERED",
  RESOLVED: "qa-RESOLVED",
  REJECTED: "qa-RESOLVED",
};

export default function Queries() {
  const { currentUser, majorProcesses, disciplines } = useUser();

  const [filterMp, setFilterMp] = useState("");
  const [filterDiscipline, setFilterDiscipline] = useState("");
  const [filterType, setFilterType] = useState("");
  const [openOnly, setOpenOnly] = useState(false);
  const [autoApplied, setAutoApplied] = useState(false);

  const [threads, setThreads] = useState([]);
  const [searchParams, setSearchParams] = useSearchParams();
  const threadParam = searchParams.get("thread");
  const [selectedId, setSelectedId] = useState(threadParam ? Number(threadParam) : null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [genMessage, setGenMessage] = useState("");

  // SpecSheetDetail 등 다른 화면에서 ?thread=<id>로 딥링크해 들어온 경우 반영.
  useEffect(() => {
    if (threadParam) setSelectedId(Number(threadParam));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [threadParam]);

  const selectThread = (id) => {
    setSelectedId(id);
    setSearchParams(id ? { thread: String(id) } : {});
  };

  // item 7: 기술팀 담당자로 들어오면 자기 대공정 + 미해결만 자동으로 필터링.
  // 설계사는 자기 공종으로 자동 필터링. 관리자/미선택은 건드리지 않는다.
  useEffect(() => {
    if (currentUser?.role === "TECH_LEAD" && currentUser.major_processes.length === 1) {
      setFilterMp(String(currentUser.major_processes[0].id));
      setOpenOnly(true);
      setAutoApplied(true);
    } else if (currentUser?.role === "DESIGNER" && currentUser.disciplines.length === 1) {
      setFilterDiscipline(String(currentUser.disciplines[0].id));
      setOpenOnly(true);
      setAutoApplied(true);
    } else if (autoApplied) {
      setFilterMp("");
      setFilterDiscipline("");
      setOpenOnly(false);
      setAutoApplied(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentUser?.id]);

  const load = () => {
    setLoading(true);
    const params = {};
    if (filterMp) params.major_process_id = filterMp;
    if (filterDiscipline) params.discipline_id = filterDiscipline;
    if (filterType) params.query_type = filterType;
    if (openOnly) params.open_only = true;
    api
      .get("/qa-threads", { params })
      .then((res) => setThreads(res.data))
      .finally(() => setLoading(false));
  };

  useEffect(load, [filterMp, filterDiscipline, filterType, openOnly]);

  const generateAuto = async () => {
    setGenerating(true);
    setGenMessage("");
    try {
      const res = await api.post("/qa-threads/generate-auto");
      setGenMessage(
        res.data.length ? `자동 질의 ${res.data.length}건이 새로 생성되었습니다.` : "새로 생성할 자동 질의가 없습니다."
      );
      load();
    } catch (err) {
      setGenMessage(err.response?.data?.detail || "생성 실패");
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div>
      <h1>질의응답 관리</h1>
      <p className="muted">
        <b>자동 제원 질의</b>는 로직이 명확한 규칙이 AS-IS→TO-BE를 스스로 계산해 일괄 생성하고, 기술팀
        승인/미승인 한 번으로 끝납니다. <b>수동 제원 질의</b>는 설계사가 직접 서술형으로 질의하고, 기술팀
        답변 → 설계사 승인 → 기술팀 값 수정(검증 통과 필수) → 설계사 최종 승인 순서로 진행됩니다.
      </p>

      <div className="panel" style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
        <button className="btn primary" onClick={generateAuto} disabled={generating}>
          {generating ? "생성 중..." : "자동 질의 일괄 생성"}
        </button>
        {genMessage && <span className="muted">{genMessage}</span>}
      </div>

      <div className="panel">
        {autoApplied && (
          <p className="muted" style={{ marginTop: 0 }}>
            {currentUser.name} 님 기준으로 자동 필터링됨 — 아래에서 직접 바꿀 수 있습니다.
          </p>
        )}
        <div className="form-row">
          <div className="field" style={{ marginBottom: 0 }}>
            <label>대공정</label>
            <select value={filterMp} onChange={(e) => { setFilterMp(e.target.value); setAutoApplied(false); }}>
              <option value="">전체</option>
              {majorProcesses.map((mp) => (
                <option key={mp.id} value={mp.id}>{mp.name}</option>
              ))}
            </select>
          </div>
          <div className="field" style={{ marginBottom: 0 }}>
            <label>공종</label>
            <select value={filterDiscipline} onChange={(e) => { setFilterDiscipline(e.target.value); setAutoApplied(false); }}>
              <option value="">전체</option>
              {disciplines.map((d) => (
                <option key={d.id} value={d.id}>{d.name}</option>
              ))}
            </select>
          </div>
          <div className="field" style={{ marginBottom: 0 }}>
            <label>질의 유형</label>
            <select value={filterType} onChange={(e) => setFilterType(e.target.value)}>
              <option value="">전체</option>
              <option value="AUTO">자동</option>
              <option value="MANUAL">수동</option>
            </select>
          </div>
          <div className="field" style={{ marginBottom: 0 }}>
            <label>상태</label>
            <div className="checkbox-row" style={{ marginTop: 8 }}>
              <input
                type="checkbox"
                id="open-only"
                checked={openOnly}
                onChange={(e) => { setOpenOnly(e.target.checked); setAutoApplied(false); }}
              />
              <label htmlFor="open-only" style={{ margin: 0 }}>미해결만 보기</label>
            </div>
          </div>
        </div>
      </div>

      <div className="grid-2">
        <div className="panel">
          <h2>질의 목록 ({threads.length}건)</h2>
          {loading ? (
            <p className="muted">불러오는 중...</p>
          ) : threads.length === 0 ? (
            <p className="muted">조건에 맞는 질의가 없습니다.</p>
          ) : (
            threads.map((t) => (
              <div
                key={t.id}
                className="thread-card"
                style={selectedId === t.id ? { borderColor: "var(--primary)" } : undefined}
                onClick={() => selectThread(t.id)}
              >
                <span className={`badge ${STATUS_BADGE[t.status]}`}>{STATUS_LABEL[t.status]}</span>{" "}
                <span className="badge" style={{ background: t.query_type === "AUTO" ? "#ddeeff" : "#f0f2f5" }}>
                  {t.query_type === "AUTO" ? "자동" : "수동"}
                </span>
                <div style={{ fontWeight: 600, fontSize: 13, margin: "4px 0" }}>{t.title}</div>
                <div className="muted">
                  {t.major_process.name}
                  {t.discipline ? ` · ${t.discipline.name}` : ""} · 대상 {t.targets.length}건
                  {t.to_be_value != null ? ` · TO-BE: ${t.to_be_value}` : ""}
                </div>
              </div>
            ))
          )}
        </div>

        <div className="panel">
          {selectedId ? (
            <QueryDetail threadId={selectedId} currentUser={currentUser} onChanged={load} />
          ) : (
            <p className="muted">왼쪽에서 질의를 선택하세요.</p>
          )}
        </div>
      </div>
    </div>
  );
}

function QueryDetail({ threadId, currentUser, onChanged }) {
  const [thread, setThread] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [warnings, setWarnings] = useState([]);
  const [answerText, setAnswerText] = useState("");
  const [proposedValue, setProposedValue] = useState("");

  const load = () => api.get(`/qa-threads/${threadId}`).then((res) => setThread(res.data));
  useEffect(() => {
    setError("");
    setWarnings([]);
    setAnswerText("");
    setProposedValue("");
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [threadId]);

  if (!thread) return <p className="muted">불러오는 중...</p>;

  const isTechForThread =
    currentUser?.role === "TECH_LEAD" && currentUser.major_processes.some((mp) => mp.id === thread.major_process.id);
  const isDesignerForThread =
    currentUser?.role === "DESIGNER" &&
    thread.discipline &&
    currentUser.disciplines.some((d) => d.id === thread.discipline.id);
  const isAdmin = currentUser?.role === "ADMIN";

  const act = async (fn) => {
    setBusy(true);
    setError("");
    setWarnings([]);
    try {
      await fn();
      await load();
      onChanged();
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (detail && typeof detail === "object") {
        setError(detail.message || "처리 실패");
        setWarnings(detail.errors || []);
      } else {
        setError(detail || "처리 실패");
      }
    } finally {
      setBusy(false);
    }
  };

  const decidedBy = currentUser?.name || "익명";

  return (
    <div>
      <h2 style={{ marginBottom: 4 }}>{thread.title}</h2>
      <p className="muted">
        {thread.query_type === "AUTO" ? "자동 질의" : "수동 질의"} · {thread.major_process.name}
        {thread.discipline ? ` · ${thread.discipline.name}` : ""} ·{" "}
        <span className={`badge ${STATUS_BADGE[thread.status]}`}>{STATUS_LABEL[thread.status]}</span>
      </p>

      <table style={{ marginBottom: 12 }}>
        <thead>
          <tr>
            <th>건설코드</th>
            <th>필드</th>
            <th>AS-IS(현재값)</th>
            <th>TO-BE(제안/확정값)</th>
          </tr>
        </thead>
        <tbody>
          {thread.targets.map((t) => (
            <tr key={t.id}>
              <td>{t.construction_code}</td>
              <td>{t.spec_field.field_name}</td>
              <td>{t.spec_field.value}</td>
              <td style={{ fontWeight: 600 }}>{thread.to_be_value ?? "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div style={{ maxHeight: 200, overflow: "auto", marginBottom: 12 }}>
        {thread.messages.map((m) => (
          <div key={m.id} className={`message role-${m.role}`}>
            <div className="meta">
              {m.author_name} · {m.role} · {new Date(m.created_at).toLocaleString()}
            </div>
            <div style={{ whiteSpace: "pre-wrap" }}>{m.content}</div>
          </div>
        ))}
      </div>

      {error && <p className="error-text">{error}</p>}
      {warnings.length > 0 && (
        <ul>
          {warnings.map((w, i) => (
            <li key={i} className="error-text">{w}</li>
          ))}
        </ul>
      )}

      {/* AUTO: OPEN -> 승인/미승인 */}
      {thread.query_type === "AUTO" && thread.status === "OPEN" && (
        isTechForThread || isAdmin ? (
          <div style={{ display: "flex", gap: 8 }}>
            <button
              className="btn primary"
              disabled={busy}
              onClick={() => act(() => api.post(`/qa-threads/${threadId}/auto-decision`, { approve: true, decided_by: decidedBy }))}
            >
              승인 (TO-BE 반영)
            </button>
            <button
              className="btn"
              disabled={busy}
              onClick={() => act(() => api.post(`/qa-threads/${threadId}/auto-decision`, { approve: false, decided_by: decidedBy }))}
            >
              미승인
            </button>
          </div>
        ) : (
          <p className="gate-note">이 대공정 담당 기술팀만 승인/미승인할 수 있습니다.</p>
        )
      )}

      {/* MANUAL: OPEN -> 서술형 답변 */}
      {thread.query_type === "MANUAL" && thread.status === "OPEN" && (
        isTechForThread || isAdmin ? (
          <div className="thread-form">
            <label className="field-label">서술형 답변</label>
            <textarea rows={3} value={answerText} onChange={(e) => setAnswerText(e.target.value)} />
            <button
              className="btn primary"
              style={{ marginTop: 8 }}
              disabled={busy || !answerText.trim()}
              onClick={() =>
                act(() =>
                  api.post(`/qa-threads/${threadId}/messages`, {
                    author_name: decidedBy, role: "ANSWER", content: answerText,
                  })
                ).then(() => setAnswerText(""))
              }
            >
              답변 등록
            </button>
          </div>
        ) : (
          <p className="gate-note">이 대공정 담당 기술팀만 답변할 수 있습니다.</p>
        )
      )}

      {/* MANUAL: TECH_ANSWERED -> 설계사 승인/반려 */}
      {thread.query_type === "MANUAL" && thread.status === "TECH_ANSWERED" && (
        isDesignerForThread || isAdmin ? (
          <div style={{ display: "flex", gap: 8 }}>
            <button
              className="btn primary"
              disabled={busy}
              onClick={() => act(() => api.post(`/qa-threads/${threadId}/answer-decision`, { approve: true, decided_by: decidedBy }))}
            >
              답변 승인 (값 수정 허용)
            </button>
            <button
              className="btn"
              disabled={busy}
              onClick={() => act(() => api.post(`/qa-threads/${threadId}/answer-decision`, { approve: false, decided_by: decidedBy }))}
            >
              반려 (재답변 요청)
            </button>
          </div>
        ) : (
          <p className="gate-note">이 공종 담당 설계사만 답변을 승인/반려할 수 있습니다.</p>
        )
      )}

      {/* MANUAL: ANSWER_APPROVED -> 기술팀 값 제안 (검증 룰셋 통과 필수) */}
      {thread.query_type === "MANUAL" && thread.status === "ANSWER_APPROVED" && (
        isTechForThread || isAdmin ? (
          <div className="thread-form">
            <label className="field-label">새 값 제안 (성상명/자재명/유량 등 검증 규칙을 통과해야 등록됩니다)</label>
            <input className="text" value={proposedValue} onChange={(e) => setProposedValue(e.target.value)} />
            <button
              className="btn primary"
              style={{ marginTop: 8 }}
              disabled={busy || !proposedValue.trim()}
              onClick={() =>
                act(() =>
                  api.post(`/qa-threads/${threadId}/propose-value`, {
                    proposed_by: decidedBy, new_value: proposedValue,
                  })
                )
              }
            >
              값 제안
            </button>
          </div>
        ) : (
          <p className="gate-note">이 대공정 담당 기술팀만 값을 제안할 수 있습니다.</p>
        )
      )}

      {/* MANUAL: VALUE_PROPOSED -> 설계사 최종 승인/반려 */}
      {thread.query_type === "MANUAL" && thread.status === "VALUE_PROPOSED" && (
        isDesignerForThread || isAdmin ? (
          <div style={{ display: "flex", gap: 8 }}>
            <button
              className="btn primary"
              disabled={busy}
              onClick={() => act(() => api.post(`/qa-threads/${threadId}/final-decision`, { approve: true, decided_by: decidedBy }))}
            >
              최종 승인 (DB 반영)
            </button>
            <button
              className="btn"
              disabled={busy}
              onClick={() => act(() => api.post(`/qa-threads/${threadId}/final-decision`, { approve: false, decided_by: decidedBy }))}
            >
              반려 (재제안 요청)
            </button>
          </div>
        ) : (
          <p className="gate-note">이 공종 담당 설계사만 최종 승인/반려할 수 있습니다.</p>
        )
      )}

      {(thread.status === "RESOLVED" || thread.status === "REJECTED") && (
        <p className="muted">이 질의는 종결되었습니다 ({STATUS_LABEL[thread.status]}).</p>
      )}
    </div>
  );
}
