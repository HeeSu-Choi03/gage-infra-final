"""가용성 프로브: 0.5초마다 <url>/readyz. 사용: python scripts/probe.py <url> <최대초> <출력파일>
apply 중에도 돌아야 하므로 terraform을 호출하지 않는다."""
import ssl, sys, time, urllib.request

url, limit, path = sys.argv[1], int(sys.argv[2]), sys.argv[3]
ctx = ssl._create_unverified_context()
t0, ok, n = time.time(), 0, 0
with open(path, "w", encoding="utf-8") as f:
    while time.time() - t0 < limit:
        try:
            with urllib.request.urlopen(url + "/readyz", context=ctx, timeout=5) as r:
                s = r.status
        except Exception as e:  # noqa: BLE001  실패 종류 무관하게 기록
            s = getattr(e, "code", 0)
        n += 1; ok += s == 200
        f.write(f"{time.strftime('%H:%M:%S')} {s} 누적 {ok}/{n} ({ok / n:.2%})\n"); f.flush()
        time.sleep(0.5)
