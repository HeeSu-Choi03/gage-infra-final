# 가게장부 — 소상공인 주문·재고 관리 인프라

인프라 설계 및 구축 (2026-2) 최종과제. 우선순위: **1. 보안·규제 / 2. 가용성**

공개 저장소: https://github.com/HeeSu-Choi03/gage-infra-final
(주소·학번 같은 환경 정보는 저장소에 두지 않는다. 주소는 `terraform.tfvars`와 `terraform output`에서만 쓴다.)

## 구성

```
README.md          소개, 구성도, 주요 수치, 실행 방법
CLAUDE.md          AI 작업 지침
ai-log.md          AI 활용 기록
THIRD_PARTY.md     오픈소스 라이선스·출처
docs/REPORT.md     리포트 원본 (REPORT.pdf·REPORT.docx와 같은 내용, 그림은 docs/img/)
.github/workflows  push마다 fmt·validate·Trivy·정책 selftest·gitleaks
terraform/         인프라 코드
scripts/           검증·시험 스크립트
policies/          Policy as Code (plan JSON 검사)
app/               FastAPI 앱, 스키마(RLS)
evidence/          측정 결과 원본
```

## 실행 방법

사전 조건: Solid Cloud VPN 연결, Terraform 1.x, Python 3.

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars   # 값 직접 입력 (커밋 금지)
python ../scripts/cs_probe.py                   # 오퍼링·한도·현재 VM 확인 (읽기 전용)
terraform init
terraform fmt -check && terraform validate
terraform plan
terraform apply                                 # plan 확인 후
```

## 주요 수치 (2026-11-24 실측, 근거는 evidence/)

| 항목 | 값 |
|---|---|
| 50 RPS (목표 피크) | p95 124ms, 오류 0% |
| 400 RPS, web 3대 | p95 201ms (2대일 때 1167ms), 오류 0% |
| 웹 앱 1대 장애 | 성공률 100% (우회 적용 전 50%) |
| DB primary 장애 | RTO 11.4초, RPO 0 |
| 암호화 백업 복구 | 18초, 데이터 일치 |
| 롤링 교체 중 가용성 | 99.47% |
| 보안 경보 (SSH 대입·토큰 추측·설정 변조) | 3종 모두 탐지, 28~93초 |
| destroy → apply | 163초 + 261초, 다시 plan 변경 0 |
| 정책 검사 P1~P5 | 위반 0건 |

## 검증 스크립트

```bash
python scripts/smoke.py                 # 헬스·RLS 테넌트 격리
python scripts/load.py 50 60 50rps      # 부하
python scripts/failover_web.py          # 웹 앱 장애
python scripts/failover_db.py           # DB 장애 (RTO/RPO)
powershell -File scripts/rolling.ps1    # 웹 롤링 교체 + 가용성 프로브
powershell -File scripts/repro.ps1      # destroy → apply
python policies/check_plan.py <plan.json>
python scripts/sec_test.py              # 보안 경보 시험 (SSH 대입, 토큰 추측, 설정 변조)
python docs/diagrams.py; python docs/build_docx.py   # 그림 생성 → REPORT.docx
```
