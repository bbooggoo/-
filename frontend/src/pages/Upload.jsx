import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api";

export default function Upload() {
  const [majorProcesses, setMajorProcesses] = useState([]);
  const [layout, setLayout] = useState("grouped");

  const [grouped, setGrouped] = useState({
    major_process_id: "",
    uploaded_by: "",
    category_row: 1,
    label_row: 2,
    data_start_row: 3,
    construction_code_override: "",
  });

  const [simple, setSimple] = useState({
    major_process_id: "",
    uploaded_by: "",
    title: "",
    construction_code: "",
    equipment_module: "",
    header_row: 1,
    label_col: 1,
    value_col: 2,
    unit_col: 3,
  });

  const [file, setFile] = useState(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null); // { created: [...], warnings: [...] }

  useEffect(() => {
    api.get("/major-processes").then((res) => {
      setMajorProcesses(res.data);
      if (res.data.length) {
        setGrouped((f) => ({ ...f, major_process_id: res.data[0].id }));
        setSimple((f) => ({ ...f, major_process_id: res.data[0].id }));
      }
    });
  }, []);

  const form = layout === "grouped" ? grouped : simple;
  const setForm = layout === "grouped" ? setGrouped : setSimple;
  const update = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setResult(null);
    if (!file) {
      setError("엑셀 파일을 선택해 주세요.");
      return;
    }
    setSubmitting(true);
    const data = new FormData();
    data.append("layout", layout);
    Object.entries(form).forEach(([k, v]) => data.append(k, v));
    data.append("file", file);
    try {
      const res = await api.post("/spec-sheets/upload", data, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setResult(res.data);
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
          <h2>헤더 형식</h2>
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
              <label>업로더</label>
              <input value={form.uploaded_by} onChange={update("uploaded_by")} placeholder="이름" />
            </div>
            <div className="field">
              <label>레이아웃 형식</label>
              <select value={layout} onChange={(e) => setLayout(e.target.value)}>
                <option value="grouped">대분류+세부항목 2단 헤더 (기본, 건설코드 자동 분리)</option>
                <option value="simple">라벨/값/단위 열 (단순 표)</option>
              </select>
            </div>
          </div>
        </div>

        {layout === "grouped" ? (
          <div className="panel">
            <h2>2단 헤더 파싱 설정</h2>
            <p className="muted">
              1행 = 대분류(UTILITY/GAS·AIR/POWER...), 2행 = 세부 항목(위치/라인/건설코드/유량/성상명...) 구조를
              가정합니다. 시트 안의 <b>건설코드</b> 열 값을 그대로 읽어서, 같은 건설코드를 쓰는 행들을 묶어
              건설코드 1개당 제원표 1건으로 자동 생성합니다. 건설코드가 비어 있는 행은 바로 위 행의 값을
              이어받습니다(카드다운).
            </p>
            <div className="form-row">
              <div className="field">
                <label>대분류 행</label>
                <input type="number" min="1" value={grouped.category_row} onChange={update("category_row")} />
              </div>
              <div className="field">
                <label>세부항목 행</label>
                <input type="number" min="1" value={grouped.label_row} onChange={update("label_row")} />
              </div>
              <div className="field">
                <label>데이터 시작 행</label>
                <input type="number" min="1" value={grouped.data_start_row} onChange={update("data_start_row")} />
              </div>
              <div className="field">
                <label>건설코드 대체값 (선택)</label>
                <input
                  value={grouped.construction_code_override}
                  onChange={update("construction_code_override")}
                  placeholder="시트에 건설코드가 비어있을 때만 사용"
                />
              </div>
            </div>
          </div>
        ) : (
          <div className="panel">
            <h2>단순 라벨/값 파싱 설정</h2>
            <div className="form-row">
              <div className="field">
                <label>건설코드 (P + 영숫자 7자리)</label>
                <input
                  value={simple.construction_code}
                  onChange={update("construction_code")}
                  placeholder="예: PD000001"
                  required
                />
              </div>
              <div className="field">
                <label>설비모듈</label>
                <input value={simple.equipment_module} onChange={update("equipment_module")} placeholder="예: GAS" />
              </div>
              <div className="field">
                <label>제목 (선택)</label>
                <input value={simple.title} onChange={update("title")} />
              </div>
            </div>
            <div className="form-row">
              <div className="field">
                <label>시작 행</label>
                <input type="number" min="1" value={simple.header_row} onChange={update("header_row")} />
              </div>
              <div className="field">
                <label>라벨 열 (A=1)</label>
                <input type="number" min="1" value={simple.label_col} onChange={update("label_col")} />
              </div>
              <div className="field">
                <label>값 열</label>
                <input type="number" min="1" value={simple.value_col} onChange={update("value_col")} />
              </div>
              <div className="field">
                <label>단위 열 (선택)</label>
                <input type="number" min="1" value={simple.unit_col} onChange={update("unit_col")} />
              </div>
            </div>
          </div>
        )}

        <div className="panel">
          <h2>엑셀 파일</h2>
          <div className="field">
            <label>파일 선택 (.xlsx)</label>
            <input type="file" accept=".xlsx,.xlsm" onChange={(e) => setFile(e.target.files[0])} required />
          </div>
        </div>

        {error && <p className="error-text">{error}</p>}

        <button className="btn primary" type="submit" disabled={submitting}>
          {submitting ? "업로드 중..." : "업로드"}
        </button>
      </form>

      {result && (
        <div className="panel" style={{ marginTop: 16 }}>
          <h2>업로드 결과</h2>
          {result.warnings.length > 0 && (
            <ul>
              {result.warnings.map((w, i) => (
                <li key={i} className="error-text">
                  {w}
                </li>
              ))}
            </ul>
          )}
          {result.created.length === 0 ? (
            <p className="muted">생성된 제원표가 없습니다.</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>건설코드</th>
                  <th>설비모듈 요약</th>
                  <th>버전</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {result.created.map((s) => (
                  <tr key={s.id}>
                    <td>{s.construction_code}</td>
                    <td className="muted">{s.equipment_module || "-"}</td>
                    <td>v{s.version}</td>
                    <td>
                      <Link to={`/spec-sheets/${s.id}`}>상세 보기</Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
