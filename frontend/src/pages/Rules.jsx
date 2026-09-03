import { useEffect, useState } from "react";
import api from "../api";

const SEVERITIES = ["ERROR", "WARN"];

export default function Rules() {
  const [rules, setRules] = useState([]);
  const [ruleTypes, setRuleTypes] = useState([]);
  const [majorProcesses, setMajorProcesses] = useState([]);
  const [form, setForm] = useState({
    name: "",
    rule_type: "",
    major_process_id: "",
    equipment_module: "",
    field_name_pattern: "",
    params: "{}",
    severity: "ERROR",
    active: true,
  });
  const [error, setError] = useState("");

  const load = () => api.get("/validation-rules").then((res) => setRules(res.data));

  useEffect(() => {
    load();
    api.get("/validation-rules/rule-types").then((res) => {
      setRuleTypes(res.data);
      setForm((f) => ({ ...f, rule_type: res.data[0] || "" }));
    });
    api.get("/major-processes").then((res) => setMajorProcesses(res.data));
  }, []);

  const update = (key) => (e) =>
    setForm((f) => ({ ...f, [key]: e.target.type === "checkbox" ? e.target.checked : e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    let params;
    try {
      params = JSON.parse(form.params || "{}");
    } catch {
      setError("파라미터는 올바른 JSON 형식이어야 합니다.");
      return;
    }
    try {
      await api.post("/validation-rules", {
        ...form,
        major_process_id: form.major_process_id || null,
        equipment_module: form.equipment_module || null,
        params,
      });
      setForm((f) => ({ ...f, name: "", field_name_pattern: "", params: "{}" }));
      load();
    } catch (err) {
      setError(err.response?.data?.detail || "등록 실패");
    }
  };

  const remove = async (id) => {
    await api.delete(`/validation-rules/${id}`);
    load();
  };

  return (
    <div>
      <h1>검증 규칙 (플러그인)</h1>
      <p className="muted">
        지금은 예시로 <code>max_value</code>(수치 상한/하한, 예: 유량 OVER), <code>standardized_enum</code>
        (표준화된 값 목록 검증, 예: 성상값)만 등록되어 있습니다. 실제 제원 검증 로직을 받으면
        <code>backend/app/services/rules/</code>에 같은 방식으로 새 규칙 함수를 추가하면 이 화면에서 바로 사용할 수 있습니다.
      </p>

      <div className="grid-2">
        <div className="panel">
          <h2>등록된 규칙</h2>
          <table>
            <thead>
              <tr>
                <th>이름</th>
                <th>타입</th>
                <th>범위</th>
                <th>필드 패턴</th>
                <th>파라미터</th>
                <th>심각도</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {rules.map((r) => (
                <tr key={r.id}>
                  <td>{r.name}</td>
                  <td>
                    <code>{r.rule_type}</code>
                  </td>
                  <td className="muted">
                    {(majorProcesses.find((mp) => mp.id === r.major_process_id)?.name) || "전체"}
                    {r.equipment_module ? ` / ${r.equipment_module}` : ""}
                  </td>
                  <td>
                    <code>{r.field_name_pattern}</code>
                  </td>
                  <td className="muted">{JSON.stringify(r.params)}</td>
                  <td>
                    <span className={`badge sev-${r.severity}`}>{r.severity}</span>
                  </td>
                  <td>
                    <button className="btn" onClick={() => remove(r.id)}>
                      삭제
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="panel">
          <h2>규칙 추가</h2>
          <form onSubmit={submit}>
            <div className="field">
              <label>이름</label>
              <input value={form.name} onChange={update("name")} required />
            </div>
            <div className="field">
              <label>규칙 타입</label>
              <select value={form.rule_type} onChange={update("rule_type")}>
                {ruleTypes.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>적용 대공정 (비우면 전체)</label>
              <select value={form.major_process_id} onChange={update("major_process_id")}>
                <option value="">전체</option>
                {majorProcesses.map((mp) => (
                  <option key={mp.id} value={mp.id}>
                    {mp.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>적용 설비모듈 (비우면 전체, 부분일치)</label>
              <input value={form.equipment_module} onChange={update("equipment_module")} placeholder="예: GAS" />
            </div>
            <div className="field">
              <label>필드명 패턴 (정규식)</label>
              <input
                value={form.field_name_pattern}
                onChange={update("field_name_pattern")}
                placeholder="예: 유량|FLOW"
                required
              />
            </div>
            <div className="field">
              <label>파라미터 (JSON)</label>
              <textarea
                rows={3}
                value={form.params}
                onChange={update("params")}
                placeholder='{"max": 100, "unit": "LPM"}'
              />
            </div>
            <div className="field">
              <label>심각도</label>
              <select value={form.severity} onChange={update("severity")}>
                {SEVERITIES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
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
