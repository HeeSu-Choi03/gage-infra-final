"""캡처의 계정 정보·자원 ID·IP를 가린다 (안내서: 캡처에서 IP, 키, 계정 정보는 보이지 않게).
좌표는 1568px 폭 크롬 캡처 기준. 실행: python scripts/mask_shots.py (덮어쓴다)"""
from pathlib import Path
from PIL import Image, ImageDraw

D = Path(__file__).resolve().parent.parent / "evidence" / "screenshots"
USER = (1400, 12, 1550, 40)  # 콘솔 오른쪽 위 학번·이름
BOXES = {
    "01-console-vm.jpg": [USER, (866, 180, 1075, 450)],                       # VM IP 열
    "02-console-vpc-tiers.jpg": [USER, (268, 314, 485, 336), (260, 484, 320, 506),   # VPC ID, 계정
                                 (1155, 227, 1290, 246), (1155, 367, 1290, 386), (1155, 508, 1290, 527)],  # tier CIDR
    "03-console-acl-web.jpg": [USER, (268, 262, 485, 282),                    # ACL ID
                               (862, 395, 1000, 414), (862, 724, 1000, 743)],  # 사설 대역 출처(0.0.0.0/0은 그대로)
    "04-grafana-security.jpg": [(20, 488, 770, 508), (788, 488, 1540, 508),   # 범례의 서버 주소
                                (16, 712, 770, 726), (1280, 585, 1400, 606)],
}

for name, boxes in BOXES.items():
    p = D / name
    im = Image.open(p).convert("RGB")
    dr = ImageDraw.Draw(im)
    for b in boxes:
        dr.rectangle(b, fill="#9AA0A6")
    im.save(p, quality=92)
    print("masked", name)
