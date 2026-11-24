"""DB primary 장애 → db02 승격 측정 (RTO/RPO). 결과는 evidence/failover-db.txt.

1) 1초마다 A 매장 주문을 넣고 성공한 order_id를 기록한다.
2) 10초 뒤 db01의 PostgreSQL을 강제 중지(장애 주입).
3) 주문이 3번 연속 실패하면(=감지) db02에서 pg_promote() 실행(런북 1단계). keepalived가 VIP를 옮긴다.
4) 주문이 다시 성공할 때까지 시간 = RTO. 장애 직전 성공한 주문이 db02에 있는지 = RPO.
"""
import json, subprocess, sys, time
sys.path.insert(0, "scripts")
import smoke  # noqa: E402  (url, tok, req 재사용)
from infra import A, on  # noqa: E402  (주소는 terraform output에서)


sku = smoke.req("/products", smoke.tok["a"])[1]["items"][0]["sku"]
log, t0, fail_at, promote_at, back_at, last_ok, fails = [], time.time(), None, None, None, None, 0
while time.time() - t0 < 300:
    t = time.time() - t0
    s, body = smoke.req("/orders", smoke.tok["a"], {"sku": sku, "qty": 1})
    ok = s == 201
    log.append(f"{t:6.1f}s {s} {body.get('order_id') if ok else ''}")
    if ok:
        last_ok = body["order_id"] if fail_at is None else last_ok
        fails = 0
        if promote_at and back_at is None:
            back_at = t
            break
    else:
        fails += 1
    if fail_at is None and t >= 10:
        on(A["db"][0], "sudo systemctl kill -s KILL postgresql@16-main")
        fail_at = time.time() - t0
    if fail_at and promote_at is None and fails >= 3:
        on(A["db"][1], "sudo -u postgres psql -Atc 'select pg_promote()'")
        promote_at = time.time() - t0
    time.sleep(1)

on_db02 = on(A["db"][1], f"sudo -u postgres psql -d gage -Atc 'select count(*) from orders where id={last_ok}'")
out = [
    f"장애 주입: {fail_at:.1f}s (db01 postgres SIGKILL)",
    f"승격 실행: {promote_at:.1f}s (3회 연속 실패 감지 후)" if promote_at else "승격 안 함",
    f"서비스 복구: {back_at:.1f}s" if back_at else "복구 안 됨 (300s)",
    f"RTO(장애→주문 성공): {back_at - fail_at:.1f}s" if back_at else "RTO: 측정 실패",
    f"RPO: 장애 직전 마지막 성공 주문 id={last_ok}, db02에 존재={on_db02 == '1'}",
    "--- 요청 로그 ---", *log,
]
print("\n".join(out))
open("evidence/failover-db.txt", "w", encoding="utf-8").write("\n".join(out) + "\n")
