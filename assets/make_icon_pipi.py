# -*- coding: utf-8 -*-
"""
皮皮输入法 · 图标 v2（白底 + 黄框 + 黄色 P）
==============================================
需求：右下角角标改成「白底、中间一个 P、外面一圈黄框」。

小尺寸是唯一的设计约束：
  Windows 托盘图标实际只显示 16×16，候选窗角标 20~24，
  所以「框」的粗细、P 的笔画粗细都得按 16px 反推，不能只在大图好看。
做法：1024 画布上画，再 Lanczos 降采样到各档；每档单独调线宽会糊，所以统一比例。
"""

import os

from PIL import Image, ImageDraw, ImageFont

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
S = 1024            # 绘制画布
SS = 2              # 额外放大倍数（先 2048 画，再降采样）

WHITE = (255, 255, 255, 255)
GOLD = (255, 194, 10, 255)      # 边框：亮黄
P_GOLD = (232, 152, 0, 255)     # 字母：偏橙的深黄，白底上更实
P_DARK = (58, 58, 58, 255)      # 备选方案：深灰字母

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\segoeuib.ttf",   # Segoe UI Bold
    r"C:\Windows\Fonts\arialbd.ttf",
    r"C:\Windows\Fonts\verdanab.ttf",
]

SIZES = [16, 20, 24, 32, 40, 48, 64, 96, 128, 256]


def pick_font():
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            return p
    raise RuntimeError("找不到粗体字体")


def render(letter_color, bg=WHITE, ring=GOLD):
    """返回 S×S 的单图（RGBA）"""
    n = S * SS
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # ── 底板 ──────────────────────────────────────────────
    # 留一点外边距，避免在任务栏里顶到别的图标
    m = int(n * 0.02)
    inset = int(n * 0.048)          # 边框宽度：16px 图上约 0.8px，再粗就糊成一圈黄点了
    radius = int(n * 0.24)
    d.rounded_rectangle(
        [m + inset // 2, m + inset // 2, n - m - inset // 2, n - m - inset // 2],
        radius=radius,
        fill=bg,
        outline=ring,
        width=inset,
    )

    # ── 字母 P ───────────────────────────────────────────
    font = ImageFont.truetype(pick_font(), int(n * 0.70))
    x0, y0, x1, y1 = font.getbbox("P")
    gw, gh = x1 - x0, y1 - y0
    # 按墨迹边界居中（不是按行高，否则 P 会往下掉）
    pos = ((n - gw) / 2 - x0, (n - gh) / 2 - y0)
    d.text(pos, "P", font=font, fill=letter_color)

    return img.resize((S, S), Image.LANCZOS)


def save_all(img, name):
    img.save(os.path.join(OUT_DIR, f"{name}.ico"),
             sizes=[(s, s) for s in SIZES])
    img.resize((256, 256), Image.LANCZOS).save(os.path.join(OUT_DIR, f"{name}-256.png"))
    for s in (16, 32, 48):
        img.resize((s, s), Image.LANCZOS).save(os.path.join(OUT_DIR, f"{name}-{s}.png"))
    print(f"  {name}.ico  ({len(SIZES)} 档: {SIZES})")


def contact_sheet(variants):
    """把多套方案放大画在一起，方便肉眼比小尺寸效果"""
    cell, pad = 64, 16
    cols = len(variants) * 3
    w = cols * (cell + pad) + pad
    h = cell + pad * 2
    sheet = Image.new("RGBA", (w, h), (245, 245, 245, 255))
    for vi, (_, img) in enumerate(variants):
        for si, s in enumerate((16, 24, 32)):
            big = img.resize((s, s), Image.LANCZOS).resize((cell, cell), Image.NEAREST)
            x = pad + (vi * 3 + si) * (cell + pad)
            sheet.alpha_composite(big, (x, pad))
    return sheet


def main():
    print("生成图标：")
    v_gold = render(P_GOLD)
    v_dark = render(P_DARK)

    save_all(v_gold, "pipi-p")
    save_all(v_gold, "pipi-hat")
    v_dark.save(os.path.join(OUT_DIR, "_variant_darkP.ico"),
                sizes=[(s, s) for s in SIZES])

    contact_sheet([("金黄 P", v_gold), ("深灰 P", v_dark)]).save(
        os.path.join(OUT_DIR, "_sheet.png"))
    print("  预览对比图 -> _sheet.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
