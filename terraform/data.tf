# 조회 전용. 인프라를 바꾸지 않는다.
data "cloudstack_zone" "dku" {
  filter {
    name  = "name"
    value = "DKU"
  }
}

data "cloudstack_template" "ubuntu" {
  template_filter = "featured"
  filter {
    name  = "name"
    value = "^Ubuntu_24.04$" # 앵커 없으면 Ubuntu_24.04_VSCode가 걸린다
  }
}

data "cloudstack_service_offering" "small" {
  filter {
    name  = "name"
    value = "Small"
  }
}

data "cloudstack_service_offering" "medium" {
  filter {
    name  = "name"
    value = "Medium"
  }
}
