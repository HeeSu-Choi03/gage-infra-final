"""보안 모니터링 시험: 공격 3종을 흉내 내고 Prometheus 경보가 뜨기까지 걸린 시간을 잰다.
1) bastion SSH 무차별 대입  2) 잘못된 토큰 대량 요청  3) mon sshd_config 변조(끝나면 원복)
사용(저장소 루트에서): python scripts/sec_test.py > evidence/security-monitoring.txt"""
import json, subprocess, sys, time
from smoke import req  # 같은 폴더의 HTTP 헬퍼 재사용 (smoke는 main 가드가 있다)
from infra import A, mon  # 주소는 terraform output에서

def firing():
    out = mon("curl -s 'http://127.0.0.1:9090/api/v1/query?query=ALERTS%7Balertstate%3D%22firing%22%7D'")
    return {r["metric"]["alertname"] for r in json.loads(out)["data"]["result"]}


def wait_alert(name, t0, limit=300):
    while time.time() - t0 < limit:
        if name in firing():
            return round(time.time() - t0, 1)
        time.sleep(5)
    return None


def main():
    print("시작 전 경보:", sorted(firing()) or "없음")

    t0 = time.time()
    for _ in range(10):  # 없는 사용자로 접속 시도 (키도 없으니 실패)
        subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=NUL",
                        "-o", "LogLevel=QUIET", "-o", "ConnectTimeout=5", "-p", "2222", f"attacker@{A['bastion']}", "true"])
    print(f"[1] SSH 무차별 대입 10회 → SSHAuthFailures 경보 {wait_alert('SSHAuthFailures', t0)}초")

    t0 = time.time()
    codes = [req("/products", f"guess-{i}")[0] for i in range(300)]
    print(f"[2] 잘못된 토큰 300회 (401 {codes.count(401)}건) → HttpAuthDeniedSpike 경보 {wait_alert('HttpAuthDeniedSpike', t0)}초")

    t0 = time.time()
    mon("sudo cp /etc/ssh/sshd_config /tmp/sshd_config.bak && echo '# tamper-test' | sudo tee -a /etc/ssh/sshd_config >/dev/null")
    print(f"[3] sshd_config 변조 → IntegrityViolation 경보 {wait_alert('IntegrityViolation', t0)}초")
    mon("sudo cp /tmp/sshd_config.bak /etc/ssh/sshd_config && sudo /usr/local/bin/gage-secmon")
    print("    원복 후 불일치:", mon("cat /var/lib/prometheus/node-exporter/gage_sec.prom | grep integrity").strip())


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
