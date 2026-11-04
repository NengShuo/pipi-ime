# -*- coding: utf-8 -*-
"""
皮皮输入法 · 图标生成器
=====================================
主视觉：黄色大写 P（参考搜狗输入法那个 S 的思路：纯字母、无底框）。

为什么用字体渲染而不是几何拼接：
几何拼出来的 P，碗的内孔比例很难调准，稍微偏一点就从「P」变成「P 带个点」。
字体里的字形是专业字体设计师调过的，内孔比例、笔画粗细都是对的。

配色策略：亮黄渐变填充 + 深棕描边
  深色任务栏 → 亮黄跳出来
  浅色皮肤   → 深棕描边勾出轮廓
"""

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os

S = 1024

YELLOW_TOP = (255, 218, 88, 255)
YELLOW_BOT = (246, 166, 8, 255)
OUTLINE = (124, 74, 4, 255)

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\segoeuib.ttf",
    r"C:\Windows\Fonts\arialbd.ttf",
    r"C:\Windows\Fonts\verdanab.ttf",
]


def _pick_font():
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            return p
    raise RuntimeError("找不到可用的粗体字体")


FONT = _pick_font()


def _glyph_mask(size, pad_ratio=0.10):
    """把字母 P 渲染成蒙版，并做视觉居中（按实际墨迹边界，不是按行高）。"""
    fnt = ImageFont.truetype(FONT, int(size * 1.9))

    # 用字体自身的度量拿到墨迹矩形，避免画布不够大把字形裁掉
    x0, y0, x1, y1 = fnt.getbbox("P")
    w, h = x1 - x0, y1 - y0
    tmp = Image.new("L", (w + 8, h + 8), 0)
    ImageDraw.Draw(tmp).text((4 - x0, 4 - y0), "P", font=fnt, fill=255)

    bbox = tmp.getbbox()
    if not bbox:
        raise RuntimeError("字形渲染失败")
    glyph = tmp.crop(bbox)

    # 等比缩放到目标区域（留出描边和呼吸空间）
    target = int(size * (1 - pad_ratio * 2))
    w, h = glyph.size
    scale = min(target / w, target / h)
    glyph = glyph.resize((max(1, int(w * scale)), max(1, int(h * scale))),
                         Image.LANCZOS)

    canvas = Image.new("L", (size, size), 0)
    canvas.paste(glyph, ((size - glyph.size[0]) // 2,
                         (size - glyph.size[1]) // 2))
    return canvas


def draw_p(size):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    k = size / 1024.0
    stroke = max(2, int(32 * k))

    mask = _glyph_mask(size)

    # 深棕描边：把蒙版向外膨胀
    outline_mask = mask.filter(ImageFilter.MaxFilter(2 * stroke + 1))

    # 纵向渐变黄
    grad = Image.new("RGBA", (1, size))
    for y in range(size):
        t = y / max(1, size - 1)
        grad.putpixel((0, y), tuple(
            int(YELLOW_TOP[i] + (YELLOW_BOT[i] - YELLOW_TOP[i]) * t)
            for i in range(3)
        ) + (255,))
    grad = grad.resize((size, size))

    img.paste(Image.new("RGBA", (size, size), OUTLINE), (0, 0), outline_mask)
    img.paste(grad, (0, 0), mask)
    return img


def main():
    sizes = [16, 20, 24, 32, 48, 64, 96, 128, 256]
    frames = []
    for s in sizes:
        # 小尺寸按最终像素直接渲染，避免缩放把笔画糊掉
        im = draw_p(s)
        im.save(f"pipi-p-{s}.png")
        frames.append(im)

    big = draw_p(1024).resize((256, 256), Image.LANCZOS)
    big.save("pipi-p-256.png")
    frames.append(big)

    frames[-1].save("pipi-p.ico", sizes=[(s, s) for s in sorted(set(sizes + [256]))])
    print("ok", sizes, "font:", os.path.basename(FONT))


if __name__ == "__main__":
    main()
