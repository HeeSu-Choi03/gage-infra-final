output "zone_id" {
  value = data.cloudstack_zone.dku.id
}

output "template_id" {
  value = data.cloudstack_template.ubuntu.id
}

output "offering_ids" {
  value = {
    small  = data.cloudstack_service_offering.small.id
    medium = data.cloudstack_service_offering.medium.id
  }
}

output "service_url" {
  value = "https://${cloudstack_ipaddress.service.ip_address}"
}

# 테스트 스크립트(scripts/smoke.py)가 읽는다. 화면 출력 금지.
output "tenant_tokens" {
  value     = { a = local.pw.tenant_a, b = local.pw.tenant_b }
  sensitive = true
}

output "web_count" {
  value = var.web_count
}

# 주소는 저장소에 적지 않고, 검증 스크립트가 여기서 읽는다 (scripts/infra.py).
output "addrs" {
  description = "bastion=관리 공용 IP, 나머지는 사설"
  value = {
    bastion = cloudstack_ipaddress.mgmt.ip_address
    web     = local.ip.web
    db      = local.ip.db
    mon     = local.ip.mon
    db_vip  = local.db_vip
    service = cloudstack_ipaddress.service.ip_address
    vpc     = var.vpc_cidr
    vpn_src = var.vpn_cidr
    tiers   = { for k, t in local.tiers : k => t.cidr }
  }
}
