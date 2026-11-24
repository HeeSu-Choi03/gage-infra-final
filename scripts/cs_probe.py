"""Solid Cloud(CloudStack) 환경 확인. 읽기 전용(list* API만 호출).

키는 terraform/terraform.tfvars에서 읽고 화면에 출력하지 않는다. VPN 연결 필요.
  python scripts/cs_probe.py            # 오퍼링·한도·현재 VM 출력
  python scripts/cs_probe.py --selftest # 오프라인 자체 점검
"""
import base64, hashlib, hmac, json, re, sys, urllib.error, urllib.parse, urllib.request
from pathlib import Path

API_URL = "https://dku.kloud.zone/client/api"
TFVARS = Path(__file__).resolve().parent.parent / "terraform" / "terraform.tfvars"


def parse_tfvars(text):
    return dict(re.findall(r'^\s*(\w+)\s*=\s*"([^"]*)"', text, re.M))


def signed_query(params, secret):
    # CloudStack 서명: 키 소문자 정렬 → 값 URL 인코딩 → 전체 소문자 → HMAC-SHA1 → base64
    q = "&".join(f"{k}={urllib.parse.quote(str(v), safe='')}"
                 for k, v in sorted(params.items(), key=lambda kv: kv[0].lower()))
    sig = base64.b64encode(hmac.new(secret.encode(), q.lower().encode(), hashlib.sha1).digest()).decode()
    return f"{q}&signature={urllib.parse.quote(sig, safe='')}"


def call(command, key, secret, **params):
    url = f"{API_URL}?{signed_query({'command': command, 'apikey': key, 'response': 'json', **params}, secret)}"
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            body = json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"[{command}] HTTP {e.code}: {e.read().decode(errors='replace')[:300]}")
    except urllib.error.URLError as e:
        sys.exit(f"[{command}] 접속 실패: {e.reason}  (VPN 연결 확인)")
    return next(iter(body.values()))  # {"listxxxresponse": {...}}


def main():
    if not TFVARS.exists():
        sys.exit(f"{TFVARS} 없음. terraform.tfvars.example을 복사해 값을 채우세요.")
    v = parse_tfvars(TFVARS.read_text(encoding="utf-8"))
    key, secret = v.get("api_key", ""), v.get("secret_key", "")
    if not key or not secret or key.startswith("여기에"):
        sys.exit("terraform.tfvars에 api_key/secret_key를 채우세요.")

    print("== 계정 자원 (사용 / 한도) ==")
    a = call("listAccounts", key, secret)["account"][0]
    for name in ("vm", "cpu", "memory", "primarystorage", "network", "vpc", "ip", "volume", "snapshot"):
        print(f"  {name:15} {a.get(name + 'total')} / {a.get(name + 'limit')}  (가용 {a.get(name + 'available')})")

    print("\n== 현재 VM ==")
    for vm in call("listVirtualMachines", key, secret).get("virtualmachine", []):
        print(f"  {vm['name']:30} {vm['state']:10} {vm.get('serviceofferingname')} "
              f"{vm.get('cpunumber')}vCPU/{vm.get('memory')}MB")

    print("\n== 네트워크 오퍼링 (Enabled) ==")
    for o in call("listNetworkOfferings", key, secret, state="Enabled").get("networkoffering", []):
        svcs = ",".join(sorted(s["name"] for s in o.get("service", [])))
        print(f"  {o['name']}  [{o['guestiptype']}{', VPC용' if o.get('forvpc') else ''}]  {svcs}")

    print("\n== VPC 오퍼링 ==")
    for o in call("listVPCOfferings", key, secret).get("vpcoffering", []) or [{"name": "(없음)"}]:
        print(f"  {o['name']}  {o.get('state', '')}")


def selftest():
    assert parse_tfvars('api_key = "a"\n# x = "no"\nsecret_key="b"\n') == {"api_key": "a", "secret_key": "b"}
    q = signed_query({"command": "listZones", "apikey": "K", "response": "json"}, "S")
    assert q.startswith("apikey=K&command=listZones&response=json&signature="), q
    assert q == signed_query({"response": "json", "apikey": "K", "command": "listZones"}, "S")  # 순서 무관
    print("selftest ok")


if __name__ == "__main__":
    selftest() if "--selftest" in sys.argv else main()
