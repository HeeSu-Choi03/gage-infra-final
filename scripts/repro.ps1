# 재현성 시험: destroy → apply → 다시 plan(변경 0이어야 함). 시간은 evidence/repro.txt에 기록.
$env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
Push-Location terraform
$out = @()
$t = Measure-Command { terraform destroy -no-color -auto-approve *> ..\evidence-destroy.log }
$out += "destroy: $([int]$t.TotalSeconds)s exit=$LASTEXITCODE  $((Select-String ..\evidence-destroy.log -Pattern 'Destroy complete').Line)"
$t = Measure-Command { terraform apply -no-color -auto-approve *> ..\evidence-apply-repro.log }
$out += "apply:   $([int]$t.TotalSeconds)s exit=$LASTEXITCODE  $((Select-String ..\evidence-apply-repro.log -Pattern 'Apply complete').Line)"
$out += "재 plan: $((terraform plan -no-color | Select-String 'No changes|Plan:').Line)"
$out += "service_url: $(terraform output -raw service_url)"
Pop-Location
$out | Out-File -Encoding utf8 evidence\repro.txt
$out
