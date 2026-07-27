import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  stages: [
    { duration: "30s", target: 5 },
    { duration: "1m", target: 10 },
    { duration: "30s", target: 0 },
  ],
  thresholds: {
    http_req_failed: ["rate<0.05"],
    http_req_duration: ["p(95)<3000"],
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
  const res = http.get(`${BASE}/api/v1/conversations`, { headers });
  check(res, { "conversations status ok-ish": (r) => r.status === 200 || r.status === 401 || r.status === 403 });
  sleep(1);
}
