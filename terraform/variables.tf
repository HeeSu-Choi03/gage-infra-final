variable "api_url" {
  description = "Solid Cloud(CloudStack) API 엔드포인트"
  type        = string
  default     = "https://dku.kloud.zone/client/api"
}

variable "api_key" {
  description = "API Key (콘솔 프로필 > 사용자 상세 > API 키 생성)"
  type        = string
  sensitive   = true
}

variable "secret_key" {
  description = "Secret Key"
  type        = string
  sensitive   = true
}

variable "name_prefix" {
  description = "자원 이름 접두사"
  type        = string
  default     = "gage"
}

variable "vpn_cidr" {
  # VPC 가상 라우터는 VPN 클라이언트 대역이 아니라 VPN 게이트웨이가 SNAT한 주소를 본다.
  # 실측(2026-11-24): bastion의 $SSH_CLIENT 값. 클라이언트 대역으로 두면 접속이 막힌다.
  description = "관리자·사용자 접근을 허용할 출처 (VPN 게이트웨이 SNAT 주소 /32, tfvars에서 지정)"
  type        = string
  validation {
    condition     = var.vpn_cidr != "0.0.0.0/0"
    error_message = "0.0.0.0/0은 허용하지 않는다."
  }
}

variable "vpc_cidr" {
  description = "VPC 사설 대역 (/16). tier는 이 안의 /24 1·2·3번을 쓴다. tfvars에서 지정"
  type        = string
  validation {
    condition     = can(cidrsubnet(var.vpc_cidr, 8, 3)) && endswith(var.vpc_cidr, "/16")
    error_message = "/16 대역이어야 한다."
  }
}

variable "ssh_public_key_path" {
  description = "VM에 등록할 SSH 공개키 경로"
  type        = string
  default     = "~/.ssh/id_ed25519.pub"
}

variable "vpc_offering" {
  # VR 이중화. 이 오퍼링의 VR은 user-data를 주지 않아 provision.tf가 SSH로 설정을 넣는다.
  # (Default VPC offering은 메타데이터조차 전달되지 않았다. 2026-11-24 실측)
  description = "VPC 오퍼링"
  type        = string
  default     = "Redundant VPC offering"
}

variable "web_count" {
  description = "웹 서버 대수"
  type        = number
  default     = 3 # 2026-11-24 부하 시험: 2대에서 웹 CPU 포화(400 RPS p95 1.2s) → 3대
}
