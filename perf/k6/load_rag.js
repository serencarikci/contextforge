import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  stages: [
    { duration: "30s", target: 5 },
    { duration: "1m", target: 15 },
    { duration: "30s", target: 0 },
  ],
  thresholds: {
    http_req_failed: ["rate<0.1"],
    http_req_duration: ["p(95)<5000"],
  },
};

const BASE = __ENV.BASE_URL || "http://localhost:8000";
const USER = __ENV.USER_ID || "00000000-0000-0000-0000-000000000001";
const ORG = __ENV.ORG_ID || "00000000-0000-0000-0000-000000000002";

export default function () {
  const headers = {
    "X-ContextForge-User-ID": USER,
    "X-ContextForge-Organization-ID": ORG,
    "Content-Type": "application/json",
  };
  const payload = JSON.stringify({
    query: "What is ContextForge?",
    top_k: 5,
  });
  const res = http.post(`${BASE}/api/v1/rag/query`, payload, { headers });
  check(res, {
    "rag responded": (r) => [200, 401, 403, 422].includes(r.status),
  });
  sleep(1);
}
