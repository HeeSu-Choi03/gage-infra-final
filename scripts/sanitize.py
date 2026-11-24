"""공개 전 텍스트의 사설 IP를 역할 이름으로 바꾼다 (실제 주소는 terraform output에서만 읽는다).
사용(저장소 루트): python scripts/sanitize.py <파일...>   인자 없으면 git이 추적하는 텍스트 파일 전부."""
import re, subprocess, sys
from pathlib import Path
from infra import A


def mapping():
    m = {A["service"]: "<서비스 공용IP>", A["bastion"]: "<관리 공용IP>", A["db_vip"]: "<DB VIP>", A["mon"]: "<mon>",
         A["vpn_src"]: "<VPN SNAT>", A["vpn_src"].split("/")[0]: "<VPN SNAT>", A["vpc"]: "<VPC /16>"}
    for k, c in A["tiers"].items():
        m[c] = f"<{k} /24>"
    for role in ("web", "db"):
        for i, ip in enumerate(A[role]):
            m[ip] = f"<{role}0{i + 1}>"
    return dict(sorted(m.items(), key=lambda kv: -len(kv[0])))  # 긴 것(/24 포함)부터


PRIVATE = re.compile(r"\b10\.\d{1,3}\.\d{1,3}\.(?:\d{1,3}|x)(?:/\d{1,2})?\b")


def clean(text, m):
    for k, v in m.items():
        text = re.sub(re.escape(k) + r"(?![\d/])", v, text)
    return PRIVATE.sub("<사설IP>", text)


if __name__ == "__main__":
    files = sys.argv[1:] or [f for f in subprocess.run(["git", "ls-files"], capture_output=True, text=True,
                                                         encoding="utf-8").stdout.splitlines()
                             if not f.endswith((".png", ".jpg", ".docx", ".pdf"))]
    m = mapping()
    for f in files:
        p = Path(f)
        s = p.read_text(encoding="utf-8")
        t = clean(s, m)
        if t != s:
            p.write_text(t, encoding="utf-8")
            print("sanitized", f)
