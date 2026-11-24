#!/bin/bash
# S4 이상 egress 시험: 내부 VM에서 외부로 허용 목록 밖 포트 연결이 막히는지 확인.
# 사용: ssh (bastion 경유) ubuntu@<VM> 'bash -s' < scripts/egress_test.sh
echo "host=$(hostname) $(date -u +%FT%TZ)"
for p in 443 4444 22 6667 8080; do
  if timeout 5 bash -c "</dev/tcp/1.1.1.1/$p" 2>/dev/null; then echo "1.1.1.1:$p 허용"; else echo "1.1.1.1:$p 차단"; fi
done
