import { useEffect, useState } from "react";
import api from "../api";

export default function Corrections() {
  const [corrections, setCorrections] = useState([]);

  useEffect(() => {
    api.get("/corrections").then((res) => setCorrections(res.data));
  }, []);

  return (
    <div>
      <h1>제원 수정 이력</h1>
      <p className="muted">
        질의응답을 통해 실제로 반영된 제원 수정 이력입니다. 이 데이터가 쌓이면 2단계(질의응답 이력 기반 자동
        제원 수정 제안)의 학습/추천 데이터로 활용될 예정입니다.
      </p>
      <div className="panel">
        {corrections.length === 0 ? (
          <p className="muted">아직 수정 이력이 없습니다.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>필드명</th>
                <th>이전 값</th>
                <th>수정 값</th>
                <th>출처</th>
                <th>처리자</th>
                <th>일시</th>
              </tr>
            </thead>
            <tbody>
              {corrections.map((c) => (
                <tr key={c.id}>
                  <td>{c.field_name || "-"}</td>
                  <td>{c.old_value}</td>
                  <td style={{ fontWeight: 600 }}>{c.new_value}</td>
                  <td className="muted">{c.source}</td>
                  <td>{c.applied_by || "-"}</td>
                  <td className="muted">{new Date(c.applied_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
