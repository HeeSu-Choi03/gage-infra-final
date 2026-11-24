"""리포트용 다이어그램 PNG 생성 (docs/img/*.png). 실행: python docs/diagrams.py"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

plt.rcParams["font.family"] = "Malgun Gothic"
OUT = Path(__file__).parent / "img"
OUT.mkdir(exist_ok=True)

C = {"ext": "#E8EEF7", "vr": "#FFF4E0", "web": "#E3F2E6", "data": "#FBE6E6", "mgmt": "#EDE7F6",
     "edge": "#44546A", "sec": "#C0392B", "box": "#FFFFFF"}


def box(ax, x, y, w, h, text, fc="#FFFFFF", ec=C["edge"], fs=9, bold=False, ls="-", lw=1.2, va="center"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.12",
                                fc=fc, ec=ec, lw=lw, ls=ls))
    ty = y + h / 2 if va == "center" else y + h - 0.22
    ax.text(x + w / 2, ty, text, ha="center", va="center" if va == "center" else "top",
            fontsize=fs, weight="bold" if bold else "normal", linespacing=1.35)


def arrow(ax, p, q, text="", color=C["edge"], ls="-", off=(0, 0.12), fs=8, both=False, rad=0.0):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="<|-|>" if both else "-|>", mutation_scale=12,
                                 color=color, lw=1.3, ls=ls, connectionstyle=f"arc3,rad={rad}"))
    if text:
        ax.text((p[0] + q[0]) / 2 + off[0], (p[1] + q[1]) / 2 + off[1], text, ha="center",
                va="bottom", fontsize=fs, color=color,
                bbox=dict(fc="white", ec="none", pad=0.6, alpha=0.9))


def canvas(w, h):
    fig, ax = plt.subplots(figsize=(w, h), dpi=200)
    ax.set_xlim(0, w * 1.6)
    ax.set_ylim(0, h * 1.6)
    ax.axis("off")
    return fig, ax


def save(fig, name):
    fig.savefig(OUT / name, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def architecture():
    fig, ax = canvas(11, 7.2)
    # 외부
    box(ax, 0.3, 9.6, 3.0, 1.3, "운영자·사용자 PC\n(VPN 접속)", C["ext"], bold=True)
    box(ax, 4.2, 9.6, 3.4, 1.3, "VPN 게이트웨이\n(SNAT 주소 1개)", C["ext"])
    arrow(ax, (3.3, 10.25), (4.2, 10.25))
    # VR
    box(ax, 0.3, 7.0, 17.0, 2.1, "", C["vr"], ec="#B7791F", lw=1.6)
    ax.text(10.6, 8.85, "VPC 가상 라우터 (Redundant VPC offering, VR 2대)", fontsize=10, weight="bold", va="top")
    box(ax, 0.7, 7.25, 4.6, 1.15, "서비스 공용 IP\nLB 443 → web01~03 (round-robin)", fs=8.5)
    box(ax, 5.6, 7.25, 4.6, 1.15, "관리 공용 IP 포트포워딩\n2222→mon:22 · 3000→Grafana", fs=8.5)
    box(ax, 10.5, 7.25, 6.5, 1.15, "Network ACL (tier별)\ningress 출처 VPN SNAT 1개만\negress 80/443/53/123 외 전체 거부",
        "#FFFFFF", ec=C["sec"], fs=8.5)
    arrow(ax, (5.9, 9.6), (3.0, 8.4), "443 HTTPS", off=(-0.6, 0))
    arrow(ax, (6.4, 9.6), (7.9, 8.4), "2222 SSH · 3000", off=(0.9, 0))
    # tiers
    box(ax, 0.3, 0.3, 7.6, 6.2, "", C["web"], ec="#2F855A", lw=1.6)
    ax.text(0.55, 6.3, "web tier (/24)", fontsize=10, weight="bold", va="top")
    for i in range(3):
        box(ax, 0.6 + i * 2.45, 3.6, 2.2, 2.2, f"web0{i+1}\nNginx TLS 1.2+\n→ App(Docker)\n1 vCPU", fs=8.5)
    arrow(ax, (2.8, 4.1), (3.05, 4.1), color="#2F855A")
    arrow(ax, (5.25, 4.1), (5.5, 4.1), color="#2F855A")
    ax.text(4.1, 3.2, "앱 장애 시 옆 서버 8443으로 우회 (ring)", ha="center", fontsize=8, color="#2F855A")
    box(ax, 0.6, 0.6, 7.0, 2.2, "node_exporter · gage-secmon(보안 지표)\nHSTS · server_tokens off · 요청 16KB 제한",
        "#FFFFFF", ec="#2F855A", fs=8.5)
    arrow(ax, (5.0, 7.25), (6.6, 5.8))

    box(ax, 8.3, 0.3, 5.0, 6.2, "", C["data"], ec="#C53030", lw=1.6)
    ax.text(8.55, 6.3, "data tier (/24)", fontsize=10, weight="bold", va="top")
    box(ax, 9.1, 4.65, 3.4, 0.9, "DB VIP\n(Keepalived, primary만 보유)", "#FFFFFF", ec=C["sec"], fs=8.5)
    box(ax, 8.6, 1.9, 2.1, 2.3, "db01\nPostgreSQL 16\nPrimary\n+ Redis\n2 vCPU", fs=8.5)
    box(ax, 10.9, 1.9, 2.1, 2.3, "db02\nPostgreSQL 16\nReplica\n+ Redis\n2 vCPU", fs=8.5)
    arrow(ax, (10.7, 3.05), (10.9, 3.05), color="#C53030")
    ax.text(10.8, 1.25, "스트리밍 복제 · RLS(FORCE) · 감사 로그", ha="center", fontsize=8, color="#C53030")
    arrow(ax, (7.6, 4.6), (9.1, 5.1), "5432 TLS / 6379", off=(0, -0.75))

    box(ax, 13.7, 0.3, 3.6, 6.2, "", C["mgmt"], ec="#6B46C1", lw=1.6)
    ax.text(13.95, 6.3, "mgmt tier (/24)", fontsize=10, weight="bold", va="top")
    box(ax, 13.95, 0.6, 3.1, 5.2, "mon (1 vCPU)\n\nbastion (유일한\nSSH 진입점)\n\nPrometheus\nGrafana · blackbox\n보안 경보\n\npg_receivewal\n(WAL 실시간)\n암호화 베이스 백업",
        fs=8.5)
    arrow(ax, (9.5, 7.25), (16.6, 5.8), rad=0.12)
    arrow(ax, (13.95, 3.0), (13.0, 3.0), "WAL", color="#6B46C1", off=(0, 0.05))
    ax.text(8.65, -0.25, "합계 6 VM · 8 vCPU / 16 GB (가용 한도 8 vCPU 안)", ha="center", fontsize=9, color="#444")
    save(fig, "architecture.png")


def flows():
    fig, ax = canvas(11, 4.6)
    ax.text(0.2, 7.1, "① 요청 흐름", fontsize=11, weight="bold")
    steps = ["사용자\n(VPN)", "VR LB\n:443", "Nginx\nTLS 종단", "FastAPI\n토큰→매장", "Redis\n캐시", "VIP →\nPrimary DB\nRLS"]
    for i, s in enumerate(steps):
        box(ax, 0.2 + i * 2.95, 5.0, 2.3, 1.6, s, [C["ext"], C["vr"], C["web"], C["web"], C["data"], C["data"]][i], fs=9)
        if i:
            arrow(ax, (0.2 + (i - 1) * 2.95 + 2.3, 5.8), (0.2 + i * 2.95, 5.8))
    ax.text(9.1, 4.55, "앱 오류(502/503/504) → 옆 서버 8443으로 재시도", ha="center", fontsize=8.5, color="#2F855A")

    ax.text(0.2, 3.7, "② 변경·배포 흐름 (사람 승인 게이트 포함)", fontsize=11, weight="bold")
    steps = ["코드 수정\n(Terraform·앱)", "fmt ·\nvalidate", "plan", "정책 검사\nP1~P5", "gitleaks\n시크릿 검사", "사람이 plan\n확인·승인", "apply /\n롤링 -replace"]
    col = ["#FFFFFF", "#FFFFFF", "#FFFFFF", "#FDECEA", "#FDECEA", C["vr"], C["web"]]
    for i, s in enumerate(steps):
        box(ax, 0.2 + i * 2.52, 1.4, 2.05, 1.6, s, col[i], fs=8.8)
        if i:
            arrow(ax, (0.2 + (i - 1) * 2.52 + 2.05, 2.2), (0.2 + i * 2.52, 2.2))
    ax.text(8.8, 0.85, "위반·\"must be replaced\"(DB) 발견 시 중단하고 되돌아감", ha="center", fontsize=8.5, color=C["sec"])
    save(fig, "flows.png")


def secmon():
    fig, ax = canvas(11, 4.2)
    srcs = [("sshd / sudo 로그\n(journald)", 5.0), ("Nginx access.log\n401 / 403", 3.2), ("설정 파일 해시\nsshd_config·passwd·\nsudoers·authorized_keys", 1.2)]
    for t, y in srcs:
        box(ax, 0.2, y, 3.4, 1.5, t, C["web"], fs=8.5)
        arrow(ax, (3.6, y + 0.75), (4.6, 3.95))
    box(ax, 4.6, 3.1, 2.9, 1.7, "gage-secmon\n(cron 1분)\n→ textfile *.prom", "#FFFFFF", fs=9, bold=True)
    box(ax, 4.6, 0.6, 2.9, 1.6, "blackbox 프로브\nTLS 인증서 만료일", "#FFFFFF", fs=9)
    box(ax, 8.4, 3.1, 2.6, 1.7, "node_exporter\n:9100", "#FFFFFF", fs=9)
    arrow(ax, (7.5, 3.95), (8.4, 3.95))
    box(ax, 11.8, 1.6, 2.9, 3.2, "Prometheus\n(mon)\n\n경보 규칙\nSSHAuthFailures\nHttpAuthDeniedSpike\nIntegrityViolation\nTelemetryMissing\nTLSCertExpiring", C["mgmt"], fs=8.3)
    arrow(ax, (11.0, 3.95), (11.8, 3.95), "scrape 5s", off=(0, 0.05))
    arrow(ax, (7.5, 1.4), (11.8, 2.2))
    box(ax, 15.4, 3.3, 2.0, 1.5, "Grafana\nSecurity\n대시보드", C["mgmt"], fs=9, bold=True)
    box(ax, 15.4, 1.2, 2.0, 1.5, "운영자\n(런북 대응)", C["ext"], fs=9)
    arrow(ax, (14.7, 4.05), (15.4, 4.05))
    arrow(ax, (16.4, 3.3), (16.4, 2.7), color=C["sec"])
    ax.text(5.7, 6.55, "web01~03 · mon 에서 수집", fontsize=10, weight="bold", ha="center")
    save(fig, "security-monitoring.png")


def incident():
    fig, ax = canvas(11, 2.6)
    ax.text(0.2, 3.75, "③ 시나리오(장애·보안 사고) 대응 흐름", fontsize=11, weight="bold")
    steps = [("탐지\nPrometheus 경보\n(가용성·보안)", C["mgmt"]), ("확인\n대시보드·로그\n범위 판단", "#FFFFFF"),
             ("런북 조치\npg_promote,\nACL 차단 등", C["vr"]), ("개선\nTerraform 변경\nplan → apply", C["web"]),
             ("검증\nsmoke·부하·\n재시험 수치", "#FFFFFF"), ("포스트모템\n근본 원인\n재발 방지", "#FDECEA")]
    for i, (s, c) in enumerate(steps):
        box(ax, 0.2 + i * 2.95, 1.0, 2.35, 1.9, s, c, fs=8.8)
        if i:
            arrow(ax, (0.2 + (i - 1) * 2.95 + 2.35, 1.95), (0.2 + i * 2.95, 1.95))
    arrow(ax, (15.2, 1.0), (1.4, 1.0), color=C["sec"], rad=-0.12)
    ax.text(8.8, -0.55, "재발 방지책을 정책(P5 등)·경보 규칙으로 코드화 → 다음 탐지에 반영", ha="center", fontsize=8.5, color=C["sec"])
    save(fig, "incident.png")


if __name__ == "__main__":
    architecture()
    flows()
    incident()
    secmon()
    print(sorted(p.name for p in OUT.glob("*.png")))
