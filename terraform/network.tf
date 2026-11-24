# VPC 1개 + tier 3개(web/data/mgmt). tier 사이 트래픽은 Network ACL로만 허용한다.
locals {
  # 주소는 저장소에 두지 않는다. var.vpc_cidr(tfvars)에서 tier를 /24로 나눠 계산한다.
  vpc_cidr = var.vpc_cidr
  tier_net = { web = 1, data = 2, mgmt = 3 } # VPC 안 /24 번호
  tiers = { for k, n in local.tier_net : k => {
    cidr     = cidrsubnet(var.vpc_cidr, 8, n)
    gw       = cidrhost(cidrsubnet(var.vpc_cidr, 8, n), 1)
    offering = k == "web" ? "DefaultIsolatedNetworkOfferingForVpcNetworks" : "DefaultIsolatedNetworkOfferingForVpcNetworksNoLB" # web만 공용 LB 필요
  } }
  db_vip = cidrhost(local.tiers.data.cidr, 100)

  # 모든 tier 공통 egress: VPC 내부, 패키지 설치(80/443), DNS, NTP
  common_egress = [
    { cidr = local.vpc_cidr, proto = "all", ports = [] },
    { cidr = "0.0.0.0/0", proto = "tcp", ports = ["80", "443"] },
    { cidr = "0.0.0.0/0", proto = "udp", ports = ["53", "123"] },
  ]

  ingress = {
    web = [
      { cidr = var.vpn_cidr, proto = "tcp", ports = ["443"] },                        # 사용자(VPN) → LB → web
      { cidr = local.tiers.web.cidr, proto = "tcp", ports = ["443", "8443"] },        # VR LB 트래픽, 웹 간 장애 우회
      { cidr = local.tiers.mgmt.cidr, proto = "tcp", ports = ["22", "443", "9100"] }, # bastion SSH, 모니터링
    ]
    data = [
      { cidr = local.tiers.web.cidr, proto = "tcp", ports = ["5432", "6379"] }, # 앱 → DB/캐시만
      { cidr = local.tiers.mgmt.cidr, proto = "tcp", ports = ["22", "5432", "9100", "9187"] },
    ]
    mgmt = [
      { cidr = var.vpn_cidr, proto = "tcp", ports = ["22", "3000"] }, # 관리자 SSH, Grafana
    ]
  }
}

resource "cloudstack_vpc" "main" {
  name         = "${var.name_prefix}-vpc"
  cidr         = local.vpc_cidr
  vpc_offering = var.vpc_offering
  zone         = data.cloudstack_zone.dku.name
}

resource "cloudstack_network_acl" "tier" {
  for_each = local.tiers
  name     = "${var.name_prefix}-acl-${each.key}"
  vpc_id   = cloudstack_vpc.main.id
}

resource "cloudstack_network_acl_rule" "tier" {
  for_each = local.tiers
  acl_id   = cloudstack_network_acl.tier[each.key].id

  dynamic "rule" {
    for_each = local.ingress[each.key]
    content {
      action       = "allow"
      cidr_list    = [rule.value.cidr]
      protocol     = rule.value.proto
      ports        = rule.value.ports
      traffic_type = "ingress"
    }
  }

  dynamic "rule" {
    for_each = local.common_egress
    content {
      action       = "allow"
      cidr_list    = [rule.value.cidr]
      protocol     = rule.value.proto
      ports        = rule.value.ports
      traffic_type = "egress"
    }
  }
}

# 사용자 정의 ACL의 egress 기본 동작이 "허용"이었다(S4 시험, 2026-11-24). 허용 규칙 뒤에 전체 거부를 둔다.
# provider 0.5는 규칙 번호를 못 정하므로 별도 자원 + depends_on으로 허용 규칙보다 나중(큰 번호)에 만든다.
resource "cloudstack_network_acl_rule" "deny_egress" {
  for_each = local.tiers
  acl_id   = cloudstack_network_acl.tier[each.key].id
  rule {
    action       = "deny"
    cidr_list    = ["0.0.0.0/0"]
    protocol     = "all"
    traffic_type = "egress"
  }
  depends_on = [cloudstack_network_acl_rule.tier]
}

resource "cloudstack_network" "tier" {
  for_each         = local.tiers
  name             = "${var.name_prefix}-${each.key}"
  cidr             = each.value.cidr
  gateway          = each.value.gw
  network_offering = each.value.offering
  vpc_id           = cloudstack_vpc.main.id
  acl_id           = cloudstack_network_acl.tier[each.key].id
  zone             = data.cloudstack_zone.dku.name
}

# 공용 IP 2개: 서비스용(LB) / 관리용(bastion SSH, Grafana)
resource "cloudstack_ipaddress" "service" {
  vpc_id = cloudstack_vpc.main.id
  zone   = data.cloudstack_zone.dku.name
}

resource "cloudstack_ipaddress" "mgmt" {
  vpc_id = cloudstack_vpc.main.id
  zone   = data.cloudstack_zone.dku.name
}

resource "cloudstack_loadbalancer_rule" "https" {
  name          = "${var.name_prefix}-https"
  ip_address_id = cloudstack_ipaddress.service.id
  network_id    = cloudstack_network.tier["web"].id
  algorithm     = "roundrobin"
  public_port   = 443
  private_port  = 443
  member_ids    = cloudstack_instance.web[*].id
}

resource "cloudstack_port_forward" "mgmt" {
  ip_address_id = cloudstack_ipaddress.mgmt.id

  forward {
    protocol           = "tcp"
    public_port        = 2222
    private_port       = 22
    virtual_machine_id = cloudstack_instance.mon.id
  }

  forward {
    protocol           = "tcp"
    public_port        = 3000
    private_port       = 3000
    virtual_machine_id = cloudstack_instance.mon.id
  }
}
