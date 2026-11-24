# AI 작업 지침 (가게장부 최종과제)

AI(Claude Code)가 이 저장소에서 작업할 때 지키는 규칙. 과제 평가 "AI 활용 - 사전 설계·지침" 근거 문서.

## 우선순위
1순위 보안·규제, 2순위 가용성. 성능·비용은 목표치만 지키고 그 이상 최적화하지 않는다.

## 시크릿
- API 키, 비밀번호, tfvars, tfstate, kubeconfig 실제 값은 채팅·코드·로그·캡처에 넣지 않는다.
- 시크릿은 `terraform/terraform.tfvars`(gitignore)나 환경변수로만 받는다. AI는 이 파일을 출력(cat)하지 않는다.
- 커밋·제출 전 gitleaks로 검사한다.

## Terraform
- 인프라 자원은 전부 Terraform으로 만든다. 콘솔 수동 생성 금지.
- provider는 `cloudstack/cloudstack ~> 0.5.0` 고정 (수업 검증 버전).
- 변경 전 `fmt` → `validate` → 정적 분석 → `plan`. `apply`/`destroy`는 사람이 plan을 읽고 승인한 뒤에만 실행한다.
- 이 Terraform이 만들지 않은 기존 자원(이미 사용 중인 8 vCPU / 64 GiB)은 조회만 하고 수정·삭제하지 않는다. `import`도 하지 않는다.
- 설계는 가용분(8 vCPU / 64 GiB) 안에서만 한다.
- 방화벽·ACL의 출처를 `0.0.0.0/0`으로 열지 않는다. 기본 출처는 VPN 게이트웨이 SNAT 주소 `<VPN SNAT>` (VR은 VPN 클라이언트 대역이 아니라 이 주소를 본다, 2026-11-24 실측).
- egress는 허용 규칙 뒤에 전체 거부를 둔다 (기본 동작이 허용).
- plan 파일·`terraform show -json` 출력에는 sensitive 값이 평문으로 들어간다. 저장소·제출물에 넣지 않는다.
- 상태 있는 서버(DB)에 영향을 주는 plan("must be replaced")은 apply 전에 멈추고 확인한다.

## 검증
- AI가 만든 코드는 실행 결과(명령 출력, 수치)로 확인하고, 틀린 사례는 `ai-log.md`에 남긴다.
- 수치는 실제 측정값만 리포트에 쓴다. 추정치는 "가정"으로 표시한다.
