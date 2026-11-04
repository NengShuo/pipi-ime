"""
皮皮输入法 · 图标生成
画一顶黄色鸭舌帽，输出多尺寸 .ico 供小狼毫状态栏 / 托盘使用

用法：python make_icon.py
产出：
  assets/pipi-hat.ico      多尺寸图标
  assets/pipi-hat-256.png  预览图
  %APPDATA%\\Rime\\pipi-hat.ico  实际被输入法读取的那份
"""

import os
import shutil

from PIL import Image, ImageDraw

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
RIME_DIR = os.path.expandvars(r"%APPDATA%\Rime")

S = 1024  # 先在大画布上绘制，缩小后边缘才干净

# 配色
YELLOW = (255, 201, 51, 255)      # 帽身亮黄
YELLOW_DARK = (224, 146, 0, 255)  # 帽檐深黄，和帽身拉开层次
YELLOW_SHADE = (198, 122, 0, 255) # 帽檐下缘阴影
OUTLINE = (122, 78, 0, 255)       # 描边深棕
BUTTON = (255, 226, 128, 255)     # 顶扣高光


def draw_hat(size=S):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    k = size / 1024.0

    def sc(*vals):
        return [v * k for v in vals]

    lw = max(2, int(30 * k))

    # 正面棒球帽：扁圆的帽冠 + 一条更宽、两端圆润的檐
    # 帽冠要「扁」（宽 > 高的两倍），太窄高就会像钟
    CROWN_BOT = 650
    crown_box = sc(162, 300, 862, CROWN_BOT * 2 - 300)   # 半圆，圆心落在 650

    # 1. 帽檐：一个扁椭圆，只比帽冠宽一点点，主要在下方露出
    d.ellipse(sc(130, 636, 894, 792), fill=YELLOW_DARK)

    # 2. 帽檐下缘压深一点，做厚度
    d.ellipse(sc(150, 726, 874, 792), fill=YELLOW_SHADE)

    # 3. 帽冠盖上去，遮住檐的中间上半部分，两侧和下方露出檐
    d.pieslice(crown_box, 180, 360, fill=YELLOW)

    # 4. 帽冠正中一条竖缝，这是帽子最容易识别的细节
    d.line(sc(512, 330, 512, 640), fill=OUTLINE, width=max(2, int(14 * k)))

    # 5. 轮廓
    d.pieslice(crown_box, 180, 360, outline=OUTLINE, width=lw)
    d.ellipse(sc(130, 636, 894, 792), outline=OUTLINE, width=lw)

    return img


def main():
    big = draw_hat(S)
    big.save(os.path.join(OUT_DIR, "pipi-hat-256.png"), sizes=[(256, 256)])

    # ico 需要的尺寸：小尺寸用于状态栏，大尺寸用于托盘/任务栏
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    ico_path = os.path.join(OUT_DIR, "pipi-hat.ico")
    big.save(ico_path, format="ICO", sizes=sizes)
    print(f"生成: {ico_path}")

    if os.path.isdir(RIME_DIR):
        target = os.path.join(RIME_DIR, "pipi-hat.ico")
        shutil.copyfile(ico_path, target)
        print(f"已复制到: {target}")
    else:
        print(f"警告: Rime 用户目录不存在 {RIME_DIR}")


if __name__ == "__main__":
    main()
