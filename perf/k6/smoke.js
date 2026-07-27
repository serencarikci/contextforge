import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  vus: 2,
  duration: "30s",
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<1000"],
  },
};

const BASE = __ENV.BASE_URL || "http://localhost:8000";

export default function () {
  const live = http.get(`${BASE}/api/v1/health/live`);
  check(live, { "live 200": (r) => r.status === 200 });
  const metrics = http.get(`${BASE}/metrics`);
  check(metrics, { "metrics 200": (r) => r.status === 200 });
  sleep(1);
}
