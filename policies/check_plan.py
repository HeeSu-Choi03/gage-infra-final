"""가게장부 Policy as Code: terraform plan JSON을 규칙으로 검사한다 (표준 라이브러리만 사용).

범용 스캐너(Trivy, Checkov)에는 CloudStack 리소스 규칙이 없어 직접 작성했다.
  terraform show -json tf.plan > plan.json
  python policies/check_plan.py plan.json     # 위반 시 exit 1
  python policies/check_plan.py --selftest
"""
import json, sys

ALLOWED_OFFERINGS = {"Small", "Medium"}
ALLOWED_PUBLIC_PORTS = {443, 2222, 3000}


def check(resources):
    """resources: [{type, address, values}] → 위반 메시지 목록"""
    errors = []
    for r in resources:
        t, a, v = r["type"], r["address"], r.get("values") or {}
        if t == "cloudstack_network_acl_rule":                                    # P1
            for rule in v.get("rule") or []:
                if rule.get("traffic_type") == "ingress" and "0.0.0.0/0" in (rule.get("cidr_list") or []):
                    errors.append(f"P1 {a}: ingress가 0.0.0.0/0에 열려 있음 (ports={rule.get('ports')})")
        if t == "cloudstack_instance":
            if v.get("service_offering") not in ALLOWED_OFFERINGS:               # P2
                errors.append(f"P2 {a}: 오퍼링 {v.get('service_offering')} 은 허용 목록 밖 (비용·한도 상한)")
            if v.get("expunge") is not True:                                     # P3
                errors.append(f"P3 {a}: expunge=true가 아님 (destroy 후 볼륨 잔존)")
        if t == "cloudstack_port_forward":                                       # P4
            for f in v.get("forward") or []:
                if f.get("public_port") not in ALLOWED_PUBLIC_PORTS:
                    errors.append(f"P4 {a}: 공개 포트 {f.get('public_port')} 는 허용 목록 밖")
        if t == "cloudstack_loadbalancer_rule" and v.get("public_port") not in ALLOWED_PUBLIC_PORTS:
            errors.append(f"P4 {a}: LB 공개 포트 {v.get('public_port')} 는 허용 목록 밖")
    acls = [r for r in resources if r["type"] == "cloudstack_network_acl"]       # P5
    denies = [r for r in resources if r["type"] == "cloudstack_network_acl_rule" and any(
        x.get("action") == "deny" and x.get("traffic_type") == "egress" and "0.0.0.0/0" in (x.get("cidr_list") or [])
        for x in (r.get("values") or {}).get("rule") or [])]
    if len(denies) < len(acls):
        errors.append(f"P5 ACL {len(acls)}개 중 egress 전체 거부가 있는 것은 {len(denies)}개 (기본 동작이 허용이라 필수)")
    return errors


def from_plan(plan):
    out = []
    for rc in plan.get("resource_changes", []):
        if "delete" in rc["change"]["actions"] and rc["change"]["after"] is None:
            continue
        out.append({"type": rc["type"], "address": rc["address"], "values": rc["change"]["after"]})
    return out


def selftest():
    good = [
        {"type": "cloudstack_network_acl_rule", "address": "ok", "values": {"rule": [
            {"traffic_type": "ingress", "cidr_list": ["<사설IP>"], "ports": ["443"]},
            {"traffic_type": "egress", "cidr_list": ["0.0.0.0/0"], "ports": ["443"]}]}},
        {"type": "cloudstack_instance", "address": "vm", "values": {"service_offering": "Small", "expunge": True}},
        {"type": "cloudstack_port_forward", "address": "pf", "values": {"forward": [{"public_port": 2222}]}},
    ]
    good.append({"type": "cloudstack_network_acl", "address": "a", "values": {}})
    good.append({"type": "cloudstack_network_acl_rule", "address": "d", "values": {"rule": [
        {"action": "deny", "traffic_type": "egress", "cidr_list": ["0.0.0.0/0"]}]}})
    bad = [
        {"type": "cloudstack_network_acl", "address": "a", "values": {}},
        {"type": "cloudstack_network_acl_rule", "address": "acl", "values": {"rule": [
            {"traffic_type": "ingress", "cidr_list": ["0.0.0.0/0"], "ports": ["22"]}]}},
        {"type": "cloudstack_instance", "address": "vm", "values": {"service_offering": "XLarge", "expunge": False}},
        {"type": "cloudstack_port_forward", "address": "pf", "values": {"forward": [{"public_port": 22}]}},
    ]
    assert check(good) == [], check(good)
    assert [e[:2] for e in check(bad)] == ["P1", "P2", "P3", "P4", "P5"], check(bad)
    print("selftest ok")


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        selftest()
        sys.exit(0)
    plan = json.load(open(sys.argv[1], encoding="utf-8-sig"))
    errs = check(from_plan(plan))
    rs = from_plan(plan)
    print(f"검사 자원 {len(rs)}개, 규칙 P1~P5, 위반 {len(errs)}건")
    for e in errs:
        print("  FAIL", e)
    sys.exit(1 if errs else 0)
