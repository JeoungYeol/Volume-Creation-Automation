"""
아이콘 생성 스크립트
AutoMediaFormatter의 앱 아이콘을 생성합니다.
"""

from PIL import Image, ImageDraw, ImageFont
import math
import os


def create_icon():
    size = 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx, cy = size // 2, size // 2

    # ── 배경: 둥근 사각형 ──
    bg_color = (26, 26, 46)  # #1a1a2e
    margin = 8
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=40,
        fill=bg_color,
    )

    # ── 미세한 테두리 ──
    border_color = (14, 165, 233, 80)  # #0ea5e9 반투명
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=40,
        outline=border_color,
        width=2,
    )

    # ── SD카드 모양 (중앙) ──
    card_color = (14, 165, 233)  # #0ea5e9
    card_dark = (8, 120, 180)

    # SD카드 본체 좌표 (모서리 잘린 형태)
    card_left = 70
    card_right = 186
    card_top = 50
    card_bottom = 210
    notch = 25  # 우측 상단 모서리 컷

    card_points = [
        (card_left, card_top),
        (card_right - notch, card_top),
        (card_right, card_top + notch),
        (card_right, card_bottom),
        (card_left, card_bottom),
    ]
    draw.polygon(card_points, fill=card_color)

    # ── 카드 내부 라인 (접점 표현) ──
    line_color = (26, 26, 46)
    line_y_start = 70
    line_spacing = 16
    line_width = 3
    for i in range(5):
        lx = card_left + 20 + i * 18
        draw.line(
            [(lx, line_y_start), (lx, line_y_start + 40)],
            fill=line_color,
            width=line_width,
        )

    # ── 순환 화살표 (자동 포맷 의미) ──
    arrow_color = (34, 197, 94)  # #22c55e 성공 그린

    # 원호를 점으로 찍어서 그리기
    arrow_cx, arrow_cy = cx, 168
    arrow_r = 22
    arrow_width = 4

    # 270도 원호 (점으로)
    for angle_deg in range(0, 270, 3):
        angle = math.radians(angle_deg - 90)
        x = arrow_cx + arrow_r * math.cos(angle)
        y = arrow_cy + arrow_r * math.sin(angle)
        draw.ellipse(
            [x - arrow_width / 2, y - arrow_width / 2, x + arrow_width / 2, y + arrow_width / 2],
            fill=arrow_color,
        )

    # 화살표 머리
    arrow_end_angle = math.radians(270 - 90)
    ax = arrow_cx + arrow_r * math.cos(arrow_end_angle)
    ay = arrow_cy + arrow_r * math.sin(arrow_end_angle)
    arrow_head = [
        (ax - 8, ay - 2),
        (ax + 4, ay + 8),
        (ax + 4, ay - 12),
    ]
    draw.polygon(arrow_head, fill=arrow_color)

    # ── 저장 ──
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources")
    os.makedirs(output_dir, exist_ok=True)

    # PNG 저장
    png_path = os.path.join(output_dir, "icon.png")
    img.save(png_path, "PNG")
    print(f"PNG 저장: {png_path}")

    # ICO 저장 (여러 크기 포함)
    ico_path = os.path.join(output_dir, "icon.ico")
    icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(ico_path, format="ICO", sizes=icon_sizes)
    print(f"ICO 저장: {ico_path}")

    return ico_path, png_path


if __name__ == "__main__":
    create_icon()
