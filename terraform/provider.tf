# 자격증명은 코드에 적지 않는다. terraform.tfvars(gitignore) 또는 TF_VAR_* 환경변수로 받는다.
terraform {
  required_version = ">= 1.0"
  required_providers {
    cloudstack = {
      source  = "cloudstack/cloudstack"
      version = "~> 0.5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "cloudstack" {
  api_url    = var.api_url
  api_key    = var.api_key
  secret_key = var.secret_key
}
