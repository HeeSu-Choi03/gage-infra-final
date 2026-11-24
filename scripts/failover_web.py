"""웹 1대 장애: web01 앱 컨테이너를 중지하고 60초 동안 /healthz 성공률·응답 서버를 기록한다."""
import collections, subprocess, sys, time
sys.path.insert(0, "scripts")
import smoke  # noqa: E402
from infra import A, on  # noqa: E402

on(A["web"][0], "sudo docker stop gage >/dev/null 2>&1 || sudo docker stop $(sudo docker ps -q)")
t0, res = time.time(), []
while time.time() - t0 < 60:
    s, b = smoke.req("/healthz")
    res.append((round(time.time() - t0, 1), s, b.get("host") if isinstance(b, dict) else "-"))
    time.sleep(0.5)
on(A["web"][0], "sudo docker start gage >/dev/null 2>&1 || sudo docker start $(sudo docker ps -aq)")
ok = sum(1 for _, s, _ in res if s == 200)
out = [f"요청 {len(res)}건, 성공 {ok}건 ({ok / len(res):.1%})",
       f"응답 서버 분포: {dict(collections.Counter(h for _, s, h in res if s == 200))}",
       f"상태 코드 분포: {dict(collections.Counter(s for _, s, _ in res))}",
       "--- 로그 ---", *[f"{t}s {s} {h}" for t, s, h in res]]
print("\n".join(out[:3]))
open("evidence/failover-web.txt", "w", encoding="utf-8").write("\n".join(out) + "\n")
