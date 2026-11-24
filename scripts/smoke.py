"""스모크 테스트: 헬스, 주문, 테넌트 격리(RLS). 토큰은 terraform output에서 읽고 출력하지 않는다."""
import json, ssl, subprocess, urllib.request, urllib.error

TF = dict(cwd="terraform", capture_output=True, text=True, encoding="utf-8", shell=True)
url = json.loads(subprocess.run("terraform output -json service_url", **TF).stdout)
tok = json.loads(subprocess.run("terraform output -json tenant_tokens", **TF).stdout)
ctx = ssl._create_unverified_context()  # 자체 서명 인증서


def req(path, token=None, body=None):
    r = urllib.request.Request(url + path, method="POST" if body else "GET",
                               data=json.dumps(body).encode() if body else None,
                               headers={"Content-Type": "application/json",
                                        **({"Authorization": f"Bearer {token}"} if token else {})})
    try:
        with urllib.request.urlopen(r, context=ctx, timeout=10) as f:
            return f.status, json.loads(f.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:200]
    except OSError as e:  # 타임아웃·연결 실패 = 장애로 기록
        return 0, str(e)


if __name__ == "__main__":
    checks = []
    s, _ = req("/healthz"); checks.append(("healthz 200", s == 200))
    s, _ = req("/products"); checks.append(("토큰 없으면 401", s == 401))
    s, va = req("/products/all-tenants", tok["a"])
    checks.append(("A 토큰: 필터 없는 쿼리도 A 매장 행만 (RLS)", s == 200 and len(va["visible_tenants"]) == 1))
    s, vb = req("/products/all-tenants", tok["b"])
    checks.append(("B 토큰: B 매장 행만, A와 다른 매장", s == 200 and len(vb["visible_tenants"]) == 1 and vb["visible_tenants"].keys() != va["visible_tenants"].keys()))
    sku = req("/products", tok["a"])[1]["items"][0]["sku"]
    stock_b = lambda: {p["sku"]: p["stock"] for p in req("/products", tok["b"])[1]["items"]}.get(sku)
    b0 = stock_b()
    s, o = req("/orders", tok["a"], {"sku": sku, "qty": 1}); checks.append(("A 주문 생성 201", s == 201))
    import time; time.sleep(11)  # 상품 캐시 TTL 10초
    checks.append(("A 주문이 B 재고를 바꾸지 않음", stock_b() == b0))
    s, _ = req("/orders", "wrong-token"); checks.append(("잘못된 토큰 401", s == 401))
    for name, ok in checks:
        print(("PASS " if ok else "FAIL ") + name)
    raise SystemExit(0 if all(ok for _, ok in checks) else 1)
