#!/bin/sh
# 보안 지표를 node_exporter textfile collector로 내보낸다 (cron 1분마다).
# Prometheus(mon)가 node 잡으로 함께 수집하고, 경보와 Grafana "Security" 대시보드가 쓴다.
d=/var/lib/prometheus/node-exporter
t=$(mktemp)
{
  # SSH 인증 실패 (최근 5분): 없는 사용자, 키 불일치
  n=$(journalctl -q --no-pager -t sshd -t sshd-session --since "-5min" 2>/dev/null \
      | grep -cE 'Invalid user|Failed (password|publickey)|Connection closed by authenticating user')
  echo "gage_sec_ssh_auth_failures_5m $n"
  # sudo 실행 횟수 (최근 5분)
  echo "gage_sec_sudo_commands_5m $(journalctl -q --no-pager -t sudo --since "-5min" 2>/dev/null | grep -c 'COMMAND=')"
  # 현재 로그인 세션 수
  echo "gage_sec_login_sessions $(who | wc -l)"
  # HTTP 인증 거부 누적 (401 잘못된 토큰, 403 접근 거부). logrotate로 줄면 rate()가 리셋으로 처리한다.
  if [ -f /var/log/nginx/access.log ]; then
    echo "gage_sec_http_auth_denied_total $(awk '$9==401||$9==403' /var/log/nginx/access.log | wc -l)"
  fi
  # 무결성: 부팅 시 만든 기준 해시와 다른 파일 수
  if [ -f /var/lib/gage/integrity.sha256 ]; then
    echo "gage_sec_integrity_mismatch $(sha256sum -c --quiet /var/lib/gage/integrity.sha256 2>/dev/null | wc -l)"
  fi
} > "$t"
chmod 644 "$t" && mv "$t" "$d/gage_sec.prom"
