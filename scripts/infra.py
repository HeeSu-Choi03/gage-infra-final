"""검증 스크립트 공통: 주소는 저장소에 적지 않고 `terraform output addrs`에서 읽는다."""
import json, subprocess

_TF = dict(cwd="terraform", capture_output=True, text=True, encoding="utf-8", shell=True)
A = json.loads(subprocess.run("terraform output -json addrs", **_TF).stdout)  # bastion, web[], db[], mon, db_vip

O = ["-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=NUL", "-o", "LogLevel=ERROR", "-o", "ConnectTimeout=15"]
BASTION = ["ssh", *O, "-p", "2222", f"ubuntu@{A['bastion']}"]
PROXY = "ProxyCommand=ssh " + " ".join(O[:6]) + f" -p 2222 -W %h:%p ubuntu@{A['bastion']}"


def on(ip, cmd):
    """bastion을 거쳐 내부 VM에서 명령 실행"""
    return subprocess.run(["ssh", *O, "-o", PROXY, f"ubuntu@{ip}", cmd], capture_output=True, text=True,
                          encoding="utf-8").stdout.strip()


def mon(cmd):
    """bastion(=mon)에서 직접 실행"""
    return subprocess.run(BASTION + [cmd], capture_output=True, text=True, encoding="utf-8").stdout
