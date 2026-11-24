# AI 활용 기록

- 도구: Claude Code (Claude Opus 5.5)
- 지침: [CLAUDE.md](CLAUDE.md)

## 맡긴 일과 확인 방법

| 날짜 | 맡긴 일 | 확인 방법 | 결과 |
|---|---|---|---|
| 2026-11-24 | 강의자료·과제 안내서 분석, 아키텍처 초안 | 안내서 평가 기준표와 대조 | 채택 |
| 2026-11-24 | 저장소 뼈대, Terraform provider/data, 환경 확인 스크립트 | fmt·validate, 스크립트 실행 결과, `--selftest` | 채택 |
| 2026-11-24 | VPC·ACL·LB·VM Terraform, cloud-init, 앱(RLS) | plan 검토(27개 생성, 기존 자원 변경 0), 정책 검사, 실제 접속 | 수정 후 채택 (아래 틀린 사례) |

## AI가 틀린 사례 (2건 이상)

| 날짜 | AI 결과 | 무엇이 틀렸나 | 어떻게 알았나 | 수정 |
|---|---|---|---|---|
| 2026-11-24 | 허용 출처를 VPN 대역 `<사설IP>`로 설정 (W1 실습 값 그대로) | VPC 가상 라우터는 VPN 게이트웨이가 SNAT한 `<VPN SNAT>`을 출처로 봄. 2222/443 모두 차단됨 | `Test-NetConnection` 실패 → 임시로 <사설IP> 허용 후 bastion에서 `$SSH_CLIENT` 확인 | `vpn_cidr`를 `<VPN SNAT>`로 변경 (더 좁아짐), 임시 규칙 삭제 |
| 2026-11-24 | Checkov 커스텀 정책(Python)을 작성 | Checkov 3.4.7이 외부 정책을 로드하지 못해 결과 0건(빈 출력). "0건 = 통과"로 오인할 뻔함 | 출력에 Passed/Failed 요약 자체가 없음을 확인 | 표준 라이브러리로 plan JSON을 검사하는 `policies/check_plan.py`로 교체, 위반 샘플로 selftest |
| 2026-11-24 | Redundant VPC offering으로 VR 이중화 설계 | 해당 오퍼링의 VR이 user-data 엔드포인트에 응답하지 않아 cloud-init 설정이 전혀 적용되지 않음 | VM에서 `curl <사설IP>/latest/user-data` 40초 타임아웃, 메타데이터는 200. API `getVirtualMachineUserData`로는 정상 저장 확인 | (아래 4번 사례로 이어짐) |
| 2026-11-24 | Default VPC offering으로 바꾸면 user-data가 전달될 것이라 판단 | 기본 VR에서는 메타데이터까지 전달되지 않아 호스트명이 `ubuntu`로 남고 SSH도 뜨지 않음 | 2222 타임아웃 → 콘솔 화면에서 호스트명 `ubuntu` 확인, 재부팅 후에도 동일 | Redundant VPC로 복귀, `provision.tf`에서 bastion 경유 SSH로 같은 cloud-config를 NoCloud seed로 넣고 재부팅 |
| 2026-11-24 | bastion 경유 SSH 프로비저닝을 기본 MTU(1500)로 설계 | tier 간 경로에서 큰 패킷이 버려져 TCP 연결·배너는 되지만 SSH 키 교환에서 멈춤 (Terraform: `remote command exited without exit status`) | bastion에서 `nc`로 배너는 수신, `ssh`는 20초 무응답 → `ip link set ens3 mtu 1400` 후 즉시 통과 | 모든 cloud-config에 `bootcmd`로 MTU 1400 설정 |
| 2026-11-24 | keepalived 설정을 한 줄 `{ a; b }` 형식으로 작성 | keepalived는 `;`를 구분자로 쓰지 않아 경로가 `pg_is_primary;`로 읽힘 → 상태 검사 비활성화, primary가 죽어도 VIP가 안 옮겨감 | DB 장애 시험에서 db02 승격 후에도 VIP가 db01에 남음 → `journalctl -u keepalived`에 "cannot be accessed" | 여러 줄 형식으로 수정, DB VM 2대를 `-replace`로 재생성 후 재시험 |
| 2026-11-24 | 웹 장애 우회용 8443에 `allow <내 peer>`만 허용 | 링 구조라 나에게 넘겨주는 쪽은 peer의 반대편 → 우회 요청이 403. 3대 확장 직후 web03 기동 지연 동안 오류율 33% | 400 RPS 시험 코드 분포 403 6000건 | `allow <web /24>`(web tier) |
| 2026-11-24 | 프로비저닝 트리거에서 user-data 해시를 빼는 변경을 바로 apply | 트리거 정의 변경 자체가 교체로 잡혀 DB 포함 전 VM에서 cloud-init 재실행·재부팅 (plan에 "must be replaced" 6건이 보였음) | plan 출력 재확인 | DB 데이터·역할 이상 없음 확인(주문 수 일치, VIP 유지). 교훈: 상태 있는 서버의 provision 교체는 plan에서 멈추고 확인 |
| 2026-11-24 | nginx 설정(write_files)이 참조하는 TLS 인증서를 runcmd에서 생성 | 패키지 설치 단계에서 nginx가 시작되며 인증서가 없어 dpkg 실패(`iF`), cloud-init status error. 서비스는 runcmd 뒤 동작해 겉으로 드러나지 않음 | `cloud-init status --long`, `/var/log/cloud-init-output.log` | 인증서 생성을 bootcmd로 이동 |
| 2026-11-24 | pg_receivewal을 고정 폴더 `/backup/wal`에 저장 | DB 클러스터 재생성 후 이전 timeline 파일과 충돌해 WAL 백업이 멈춤 ("starting timeline 2 is not present") | `journalctl -u pg-receivewal` | 클러스터 ID(IDENTIFY_SYSTEM)별 폴더에 저장 |
| 2026-11-24 | egress 허용 규칙만 두면 나머지는 막힌다고 가정, 1.1.1.1의 4444/22/6667 "차단"을 근거로 판단 | ACL egress 기본 동작이 허용이었음. 그 포트들은 상대가 안 열었을 뿐. Cloudflare가 실제로 여는 2052/8880/8080 등은 모두 통과 | 같은 목적지에 대해 내 PC와 VM 결과 비교, HTTP 응답 헤더 확인 | 별도 `deny_egress` 규칙(허용 뒤 번호) 추가, 정책 P5로 강제 |
| 2026-11-24 | `.gitignore`에 `*.tfplan`만 두고 plan 파일을 `tf.plan`, plan JSON을 `evidence/`에 저장 | 두 파일 모두 저장소에 들어갈 수 있었음. plan·show -json에는 sensitive 값이 평문 | S4 시험 중 `git add -A` 후 스테이징 목록 확인 | `*.plan`, `tfplan.json`, `evidence-apply*.log` 제외 (커밋 전 발견, 유출 없음) |
| 2026-11-24 | postgres exporter를 패키지 설치만 하고 접속 정보 미설정, 경보식 `sum(pg_up) < 1` | `pg_up` 항상 0 → `NoPostgresPrimary`가 정상 상태에서도 계속 firing. 식도 "primary 없음"이 아니라 "DB 둘 다 다운"을 뜻함 | Prometheus `/api/v1/alerts`, exporter 로그 "empty dsn" | 소켓 peer 인증 DSN 추가, `absent(pg_up==1 and pg_replication_is_replica==0)`로 수정 |
