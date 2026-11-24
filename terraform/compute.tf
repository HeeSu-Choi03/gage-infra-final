# 시크릿은 Terraform이 생성한다. 값은 state(gitignore)에만 남고 코드·저장소에는 없다.
resource "random_password" "secret" {
  for_each = toset(["db_app", "db_repl", "redis", "grafana", "backup", "tenant_a", "tenant_b"])
  length   = 32
  special  = false
}

locals {
  pw = { for k, v in random_password.secret : k => v.result }
  ip = {
    web = [for i in range(var.web_count) : cidrhost(local.tiers.web.cidr, 11 + i)] # .11, .12, ...
    db  = [for i in range(2) : cidrhost(local.tiers.data.cidr, 11 + i)]
    mon = cidrhost(local.tiers.mgmt.cidr, 11)
  }
  common = {
    db_vip     = local.db_vip
    web_cidr   = local.tiers.web.cidr
    data_cidr  = local.tiers.data.cidr
    mgmt_cidr  = local.tiers.mgmt.cidr
    ssh_pubkey = trimspace(file(pathexpand(var.ssh_public_key_path)))
    secmon_sh  = base64gzip(file("${path.module}/templates/secmon.sh")) # 보안 지표 수집 (web, mon)
  }
}

resource "cloudstack_ssh_keypair" "admin" {
  name       = "${var.name_prefix}-admin"
  public_key = local.common.ssh_pubkey
}

resource "cloudstack_instance" "web" {
  count            = var.web_count
  name             = format("%s-web%02d", var.name_prefix, count.index + 1)
  service_offering = data.cloudstack_service_offering.small.name
  template         = data.cloudstack_template.ubuntu.id
  zone             = data.cloudstack_zone.dku.name
  network_id       = cloudstack_network.tier["web"].id
  ip_address       = local.ip.web[count.index]
  keypair          = cloudstack_ssh_keypair.admin.name
  expunge          = true                    # destroy 시 볼륨까지 회수 (한도 반환)
  lifecycle { ignore_changes = [user_data] } # 실제 설정은 provision.tf가 SSH로 넣는다
  user_data = local.ud_web[count.index]
}

resource "cloudstack_instance" "db" {
  count            = 2
  name             = format("%s-db%02d", var.name_prefix, count.index + 1)
  service_offering = data.cloudstack_service_offering.medium.name
  template         = data.cloudstack_template.ubuntu.id
  zone             = data.cloudstack_zone.dku.name
  network_id       = cloudstack_network.tier["data"].id
  ip_address       = local.ip.db[count.index]
  keypair          = cloudstack_ssh_keypair.admin.name
  expunge          = true
  lifecycle { ignore_changes = [user_data] } # 실제 설정은 provision.tf가 SSH로 넣는다
  user_data = local.ud_db[count.index]
}

resource "cloudstack_instance" "mon" {
  name             = "${var.name_prefix}-mon"
  service_offering = data.cloudstack_service_offering.small.name
  template         = data.cloudstack_template.ubuntu.id
  zone             = data.cloudstack_zone.dku.name
  network_id       = cloudstack_network.tier["mgmt"].id
  ip_address       = local.ip.mon
  keypair          = cloudstack_ssh_keypair.admin.name
  expunge          = true
  lifecycle { ignore_changes = [user_data] } # 실제 설정은 provision.tf가 SSH로 넣는다
  user_data = local.ud_mon
}

# 렌더링한 cloud-config. VM user_data와 SSH 프로비저닝(provision.tf)이 같이 쓴다.
locals {
  ud_web = [for i in range(var.web_count) : templatefile("${path.module}/templates/web.yaml.tftpl", merge(local.common, {
    hostname     = format("web%02d", i + 1)
    peer_ip      = local.ip.web[(i + 1) % var.web_count]
    db_app_pw    = local.pw.db_app
    redis_pw     = local.pw.redis
    main_py      = base64gzip(file("${path.module}/../app/main.py"))
    requirements = base64gzip(file("${path.module}/../app/requirements.txt"))
    dockerfile   = base64gzip(file("${path.module}/../app/Dockerfile"))
  }))]
  ud_db = [for i in range(2) : templatefile("${path.module}/templates/db.yaml.tftpl", merge(local.common, {
    hostname     = format("db%02d", i + 1)
    role         = i == 0 ? "primary" : "replica"
    self_ip      = local.ip.db[i]
    peer_ip      = local.ip.db[1 - i]
    primary_ip   = local.ip.db[0]
    db_app_pw    = local.pw.db_app
    db_repl_pw   = local.pw.db_repl
    redis_pw     = local.pw.redis
    tenant_a_sha = sha256(local.pw.tenant_a)
    tenant_b_sha = sha256(local.pw.tenant_b)
    schema_sql   = base64gzip(file("${path.module}/../app/schema.sql"))
  }))]
  ud_mon = templatefile("${path.module}/templates/mon.yaml.tftpl", merge(local.common, {
    web_ips    = local.ip.web
    db_ips     = local.ip.db
    db_repl_pw = local.pw.db_repl
    grafana_pw = local.pw.grafana
    backup_pw  = local.pw.backup
    sec_dash   = base64gzip(file("${path.module}/templates/security-dashboard.json"))
  }))
}
