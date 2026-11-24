# Redundant VPC의 VR은 메타데이터·SSH 키는 주지만 user-data는 주지 않는다(2026-11-24 실측).
# 그래서 Terraform이 bastion(mon) 경유 SSH로 같은 cloud-config를 NoCloud seed로 넣고 재부팅한다.
locals {
  ssh_key = file(pathexpand(replace(var.ssh_public_key_path, ".pub", "")))
  bastion = cloudstack_ipaddress.mgmt.ip_address
  seed_cmd = [
    "sudo mkdir -p /var/lib/cloud/seed/nocloud",
    "sudo mv /tmp/user-data /var/lib/cloud/seed/nocloud/user-data",
    "echo 'datasource_list: [NoCloud, None]' | sudo tee /etc/cloud/cloud.cfg.d/99-gage.cfg",
    "sudo cloud-init clean --logs",
    "sudo systemd-run --on-active=3 /usr/bin/systemctl reboot",
  ]
  # mon은 bastion이므로 다른 VM을 다 넣은 뒤 마지막에 재부팅한다.
  targets = merge(
    { for i, v in local.ud_web : "web${i}" => { ip = local.ip.web[i], ud = v, id = cloudstack_instance.web[i].id } },
    { for i, v in local.ud_db : "db${i}" => { ip = local.ip.db[i], ud = v, id = cloudstack_instance.db[i].id } },
  )
}

resource "terraform_data" "provision" {
  for_each         = local.targets
  triggers_replace = [each.value.id] # 불변 인프라: 설정 변경은 VM 교체(-replace)로 반영

  connection {
    type         = "ssh"
    user         = "ubuntu"
    private_key  = local.ssh_key
    host         = each.value.ip
    port         = 22
    bastion_host = local.bastion
    bastion_port = 2222
    timeout      = "10m"
  }

  provisioner "file" {
    content     = each.value.ud
    destination = "/tmp/user-data"
  }
  provisioner "remote-exec" {
    inline = concat(
      ["printf 'instance-id: ${each.value.id}\nlocal-hostname: ${each.key}\n' | sudo tee /tmp/meta-data >/dev/null",
      "sudo mkdir -p /var/lib/cloud/seed/nocloud && sudo mv /tmp/meta-data /var/lib/cloud/seed/nocloud/meta-data"],
      local.seed_cmd
    )
  }
  depends_on = [cloudstack_port_forward.mgmt, cloudstack_network_acl_rule.tier]
}

resource "terraform_data" "provision_mon" {
  triggers_replace = [cloudstack_instance.mon.id]

  connection {
    type        = "ssh"
    user        = "ubuntu"
    private_key = local.ssh_key
    host        = local.bastion
    port        = 2222
    timeout     = "10m"
  }

  provisioner "file" {
    content     = local.ud_mon
    destination = "/tmp/user-data"
  }
  provisioner "remote-exec" {
    inline = concat(
      ["printf 'instance-id: ${cloudstack_instance.mon.id}\nlocal-hostname: mon\n' | sudo tee /tmp/meta-data >/dev/null",
      "sudo mkdir -p /var/lib/cloud/seed/nocloud && sudo mv /tmp/meta-data /var/lib/cloud/seed/nocloud/meta-data"],
      local.seed_cmd
    )
  }
  depends_on = [terraform_data.provision]
}
