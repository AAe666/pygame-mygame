# -*- coding: utf-8 -*-
"""生成 Greedy Dash 的 exe 图标 (icon.ico)。
配色取自 settings.py：深紫->深蓝渐变底、青蓝飞船、金色宝石。
高分辨率绘制后降采样以获得抗锯齿，最终导出多尺寸 .ico。
"""
from PIL import Image, ImageDraw

SS = 4                      # 超采样倍数
BASE = 256
S = BASE * SS

# ---------- 配色 (取自 settings.py) ----------
C_BG_TOP = (42, 22, 74)
C_BG_BOTTOM = (14, 18, 58)
C_SHIP_CORE = (0, 200, 255)
C_SHIP_CORE2 = (120, 235, 255)
C_SHIP_EDGE = (255, 255, 255)
C_FLAME = (255, 170, 60)
C_GOLD = (255, 210, 90)
C_GEM = (255, 90, 130)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def rounded_mask(size, radius):
    m = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    return m


def make_base():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    # 垂直渐变背景
    grad = Image.new("RGBA", (S, S))
    gd = grad.load()
    for y in range(S):
        t = y / (S - 1)
        c = lerp(C_BG_TOP, C_BG_BOTTOM, t)
        for x in range(S):
            gd[x, y] = (c[0], c[1], c[2], 255)
    mask = rounded_mask(S, int(S * 0.22))
    img.paste(grad, (0, 0), mask)

    d = ImageDraw.Draw(img, "RGBA")

    # 背景星光点缀
    import random
    random.seed(7)
    for _ in range(70):
        x = random.randint(0, S - 1)
        y = random.randint(0, S - 1)
        r = random.choice([1, 1, 2, 2, 3]) * SS
        a = random.randint(60, 180)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, a))
    # 用圆角遮罩裁掉溢出的星点
    star_layer = img.copy()
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    img.paste(star_layer, (0, 0), mask)
    d = ImageDraw.Draw(img, "RGBA")

    cx = S // 2

    # ---------- 飞船光晕 ----------
    glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    gdr = ImageDraw.Draw(glow)
    gr = int(S * 0.30)
    gy = int(S * 0.50)
    for i in range(gr, 0, -1):
        a = int(70 * (1 - i / gr))
        gdr.ellipse([cx - i, gy - i, cx + i, gy + i], fill=(0, 180, 255, a))
    img = Image.alpha_composite(img, glow)
    d = ImageDraw.Draw(img, "RGBA")

    # ---------- 尾焰 ----------
    fw = int(S * 0.10)
    fy0 = int(S * 0.66)
    fy1 = int(S * 0.80)
    d.polygon([(cx - fw, fy0), (cx + fw, fy0), (cx, fy1)], fill=C_FLAME + (255,))
    d.polygon([(cx - fw // 2, fy0), (cx + fw // 2, fy0), (cx, int(S * 0.74))],
              fill=(255, 235, 150, 255))

    # ---------- 飞船本体（向上箭头/三角）----------
    top = (cx, int(S * 0.22))
    left = (int(S * 0.28), int(S * 0.68))
    right = (int(S * 0.72), int(S * 0.68))
    notch = (cx, int(S * 0.58))   # 尾部内凹
    ship = [top, right, notch, left]
    # 白色描边
    d.polygon(ship, fill=C_SHIP_EDGE + (255,))
    # 内层青蓝（缩放一点）
    def shrink(pts, k):
        cxp = sum(p[0] for p in pts) / len(pts)
        cyp = sum(p[1] for p in pts) / len(pts)
        return [(int(cxp + (p[0] - cxp) * k), int(cyp + (p[1] - cyp) * k)) for p in pts]
    d.polygon(shrink(ship, 0.82), fill=C_SHIP_CORE + (255,))
    d.polygon(shrink(ship, 0.5), fill=C_SHIP_CORE2 + (255,))

    # ---------- 座舱宝石（金红）----------
    gemr = int(S * 0.055)
    gy2 = int(S * 0.44)
    d.ellipse([cx - gemr, gy2 - gemr, cx + gemr, gy2 + gemr], fill=C_GOLD + (255,))
    d.ellipse([cx - gemr // 2, gy2 - gemr // 2, cx + gemr // 2, gy2 + gemr // 2],
              fill=C_GEM + (255,))

    return img


def main():
    big = make_base()
    icon = big.resize((BASE, BASE), Image.LANCZOS)
    icon.save("icon.png")
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    icon.save("icon.ico", format="ICO", sizes=sizes)
    print("saved icon.png / icon.ico")


if __name__ == "__main__":
    main()
