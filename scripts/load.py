"""부하 시험: 목표 RPS로 60초 동안 조회 80% / 주문 20%. 사용: python scripts/load.py [rps] [초] [라벨]
결과(p50/p95/p99, 오류율, 실제 RPS)는 evidence/load-<라벨>.txt.
"""
import random, statistics, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, "scripts")
import smoke  # noqa: E402

rps = int(sys.argv[1]) if len(sys.argv) > 1 else 50
dur = int(sys.argv[2]) if len(sys.argv) > 2 else 60
label = sys.argv[3] if len(sys.argv) > 3 else f"{rps}rps"
toks = [smoke.tok["a"], smoke.tok["b"]]
skus = {t: [p["sku"] for p in smoke.req("/products", t)[1]["items"]] for t in toks}
lat, codes, lock = [], {}, threading.Lock()


def one():
    t = random.choice(toks)
    s0 = time.perf_counter()
    if random.random() < 0.8:
        s, _ = smoke.req("/products", t)
    else:
        s, _ = smoke.req("/orders", t, {"sku": random.choice(skus[t]), "qty": 1})
    ms = (time.perf_counter() - s0) * 1000
    with lock:
        lat.append(ms)
        codes[s] = codes.get(s, 0) + 1


t0 = time.time()
with ThreadPoolExecutor(max_workers=200) as ex:
    for i in range(rps * dur):
        time.sleep(max(0, t0 + i / rps - time.time()))  # 일정 간격으로 요청 시작(open model)
        ex.submit(one)
el = time.time() - t0
lat.sort()
q = lambda p: lat[min(len(lat) - 1, int(len(lat) * p))]
err = sum(v for k, v in codes.items() if k not in (200, 201)) / len(lat)
out = [f"[{label}] 목표 {rps} RPS × {dur}s, 완료 {len(lat)}건, 실제 {len(lat) / el:.1f} RPS",
       f"p50 {q(.5):.0f}ms  p95 {q(.95):.0f}ms  p99 {q(.99):.0f}ms  평균 {statistics.mean(lat):.0f}ms",
       f"오류율 {err:.2%}  코드 {codes}"]
print("\n".join(out))
open(f"evidence/load-{label}.txt", "w", encoding="utf-8").write("\n".join(out) + "\n")
