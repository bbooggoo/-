import axios from "axios";

const api = axios.create({ baseURL: "/api" });

// 데모용 사용자 식별: 선택된 담당자 id를 모든 요청에 X-User-Id 헤더로 실어보낸다.
api.interceptors.request.use((config) => {
  const userId = localStorage.getItem("currentUserId");
  if (userId) {
    config.headers["X-User-Id"] = userId;
  }
  return config;
});

export default api;
