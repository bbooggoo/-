import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";

const EQUIPMENT_MODULE_SUGGESTIONS = ["GAS", "SCRUBBER", "MAIN", "CHAMBER", "EFEM", "PUMP"];

export default function Upload() {
  const navigate = useNavigate();
  const [majorProcesses, setMajorProcesses] = useState([]);
  const [form, setForm] = useState({
    major_process_id: "",
    construction_code: "",
    equipment_module: "",
    title: "",
    uploaded_by: "",
    header_row: 1,
    label_col: 1,
    value_col: 2,
    unit_col: 3,
  });
  const [file, setFile] = useState(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    api.get("/major-processes").then((res) => {
      setMajorProcesses(res.data);
      if (res.data.length) setForm((f) => ({ ...f, major_process_id: res.data[0].id }));
    });
  }, []);

  const update = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    if (!file) {
      setError("엑셀 파일을 선택해 주세요.");
      return;
    }
    setSubmitting(true);
    const data = new FormData();
    Object.entries(form).forEach(([k, v]) => data.append(k, v));
    data.append("file", file);
    try {
      const res = await api.post("/spec-sheets/upload", data, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      navigate(`/spec-sheets/${res.data.id}`);
    } catch (err) {
      setError(err.response?.data?.detail || "업로드에 실패했습니다.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <h1>제원표 업로드</h1>
      <form onSubmit={submit}>
        <div className="panel">
          <h2>분류 정보</h2>
          <div className="form-row">
            <div className="field">
              <label>대공정</label>
              <select value={form.major_process_id} onChange={update("major_process_id")} required>
                {majorProcesses.map((mp) => (
                  <option key={mp.id} value={mp.id}>
                    {mp.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>건설코드 (P + 영숫자 7자리)</label>
              <input
                value={form.construction_code}
                onChange={update("construction_code")}
                placeholder="예: PD000001"
                required
              />
            </div>
            <div className="field">
              <label>설비모듈</label>
              <input
                value={form.equipment_module}
                onChange={update("equipment_module")}
                placeholder="예: GAS"
                list="equipment-module-suggestions"
                required
              />
              <datalist id="equipment-module-suggestions">
                {EQUIPMENT_MODULE_SUGGESTIONS.map((m) => (
                  <option key={m} value={m} />
                ))}
              </datalist>
            </div>
          </div>
          <div className="form-row">
            <div className="field">
              <label>제목 (선택)</label>
              <input value={form.title} onChange={update("title")} placeholder="비워두면 자동 생성" />
            </div>
            <div className="field">
              <label>업로더</label>
              <input value={form.uploaded_by} onChange={update("uploaded_by")} placeholder="이름" />
            </div>
          </div>
        </div>

        <div className="panel">
          <h2>엑셀 파일</h2>
          <div className="field">
            <label>파일 선택 (.xlsx)</label>
            <input type="file" accept=".xlsx,.xlsm" onChange={(e) => setFile(e.target.files[0])} required />
          </div>
          <p className="muted">
            CAD형 레이아웃의 셀 좌표를 그대로 보존해서 저장합니다. 아래는 "라벨 열 - 값 열 - 단위 열" 형태로
            반복되는 표 기준 파싱 설정입니다. 실제 제원표 헤더 예시를 받으면 이 파싱 로직을 정교화할 예정입니다.
          </p>
          <div className="form-row">
            <div className="field">
              <label>시작 행</label>
              <input type="number" min="1" value={form.header_row} onChange={update("header_row")} />
            </div>
            <div className="field">
              <label>라벨 열 (A=1)</label>
              <input type="number" min="1" value={form.label_col} onChange={update("label_col")} />
            </div>
            <div className="field">
              <label>값 열</label>
              <input type="number" min="1" value={form.value_col} onChange={update("value_col")} />
            </div>
            <div className="field">
              <label>단위 열 (선택)</label>
              <input type="number" min="1" value={form.unit_col} onChange={update("unit_col")} />
            </div>
          </div>
        </div>

        {error && <p className="error-text">{error}</p>}

        <button className="btn primary" type="submit" disabled={submitting}>
          {submitting ? "업로드 중..." : "업로드"}
        </button>
      </form>
    </div>
  );
}
