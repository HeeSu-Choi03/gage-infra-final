# 웹 서버 롤링 교체: 한 대씩 terraform -replace, 다음 대는 새 서버가 응답한 뒤 진행.
# 동시에 scripts/probe.py가 2 RPS로 가용성을 기록한다 (evidence/rolling-probe.txt).
$env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
$env:PYTHONIOENCODING = 'utf-8'
Push-Location terraform; $url = terraform output -raw service_url; Pop-Location
$probe = Start-Process python -ArgumentList '-I', 'scripts\probe.py', $url, '1800', 'evidence\rolling-probe.txt' -PassThru -NoNewWindow
Push-Location terraform
$count = [int](terraform output -raw web_count)
$addrs = terraform output -json addrs | ConvertFrom-Json   # 주소는 저장소에 적지 않는다
for ($i = 0; $i -lt $count; $i++) {
    "== web[$i] 교체 $(Get-Date -Format HH:mm:ss)"
    terraform apply -no-color -auto-approve -replace="cloudstack_instance.web[$i]" | Select-String 'Apply complete|Error'
    $ip = $addrs.web[$i]
    $o = '-o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL -o LogLevel=ERROR'
    for ($t = 0; $t -lt 90; $t++) {
        $r = ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL -o LogLevel=ERROR -o ConnectTimeout=10 -o "ProxyCommand=ssh $o -p 2222 -W %h:%p ubuntu@$($addrs.bastion)" ubuntu@$ip "curl -s -m3 127.0.0.1:8000/readyz; sleep 5"
        if ($r -match 'true') { "   web[$i] 준비됨 $(Get-Date -Format HH:mm:ss)"; break }
    }
}
Pop-Location
Stop-Process -Id $probe.Id
