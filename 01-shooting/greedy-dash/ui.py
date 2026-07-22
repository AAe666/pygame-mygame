# -*- coding: utf-8 -*-
"""
UI 绘制：主菜单、游戏说明（可滚动）、暂停、HUD、BOSS 出场、结算（通关/失败）、浮动文字
"""
import math

import pygame

from settings import *
import settings as S
import gamedoc as G


# ---------- 字体 ----------
_font_cache = {}

def get_font(size, bold=False):
    names = ["Microsoft YaHei", "SimHei", "SimSun", "Arial"]
    for n in names:
        try:
            f = pygame.font.SysFont(n, size, bold=bold)
            if f:
                return f
        except Exception:
            continue
    return pygame.font.Font(None, size)


def _fmt_val(v):
    """格式化数值：浮点整数部分去 .0，小数保留一位（不四舍五入）。"""
    if isinstance(v, float):
        if v == int(v):
            return str(int(v))
        return "%.1f" % v
    return str(v)


# ---------- 通用按钮 ----------
def _draw_btn(screen, rect, text, hovered, text_col=C_GOLD,
              border_col=C_RESUME_BORDER, font_size=22):
    bg = (40, 46, 80, 245) if hovered else (20, 24, 50, 230)
    pygame.draw.rect(screen, bg, rect, border_radius=12)
    pygame.draw.rect(screen, border_col, rect, 2, border_radius=12)
    pygame.draw.rect(screen, border_col, rect.inflate(-6, -6), 1, border_radius=8)
    bs = get_font(font_size, bold=True).render(text, True, text_col)
    screen.blit(bs, bs.get_rect(center=rect.center))


# ---------- 暂停按钮 ----------
PAUSE_BTN = pygame.Rect(10, 10, 30, 30)

def draw_pause_button(screen, hovered=False):
    surf = pygame.Surface((PAUSE_BTN.w, PAUSE_BTN.h), pygame.SRCALPHA)
    bg = (30, 30, 55, 200) if not hovered else (50, 50, 85, 220)
    pygame.draw.rect(surf, bg, (0, 0, PAUSE_BTN.w, PAUSE_BTN.h), border_radius=6)
    pygame.draw.rect(surf, C_RESUME_BORDER, (0, 0, PAUSE_BTN.w, PAUSE_BTN.h),
                     1, border_radius=6)
    bw, bh, gap = 4, 16, 6
    total = bw * 2 + gap
    start_x = (PAUSE_BTN.w - total) / 2
    cy = (PAUSE_BTN.h - bh) / 2
    pygame.draw.rect(surf, C_PAUSE_ICON, (start_x, cy, bw, bh))
    pygame.draw.rect(surf, C_PAUSE_ICON, (start_x + bw + gap, cy, bw, bh))
    screen.blit(surf, PAUSE_BTN.topleft)


# ---------- 暂停遮罩（三按钮）----------
RESUME_BTN = pygame.Rect(SCREEN_W // 2 - 110, SCREEN_H // 2 - 100, 220, 50)
PAUSE_RESTART_BTN = pygame.Rect(SCREEN_W // 2 - 110, SCREEN_H // 2 - 40, 220, 50)
PAUSE_MENU_BTN = pygame.Rect(SCREEN_W // 2 - 110, SCREEN_H // 2 + 20, 220, 50)


def draw_pause_overlay(screen):
    mp = pygame.mouse.get_pos()
    overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    overlay.fill((*C_OVERLAY, 180))
    screen.blit(overlay, (0, 0))
    tf = get_font(40, bold=True)
    ts = tf.render("已暂停", True, C_TEXT)
    screen.blit(ts, ts.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - 170)))
    rect = RESUME_BTN
    hov = rect.collidepoint(mp)
    _draw_btn(screen, rect, "", hov)
    cx, cy = rect.center
    tri = [(cx - 18, cy - 12), (cx - 18, cy + 12), (cx + 12, cy)]
    pygame.draw.polygon(screen, C_PLAY_TRI, tri)
    rl = get_font(18).render("继续游戏", True, C_TEXT)
    screen.blit(rl, rl.get_rect(midleft=(cx + 22, cy)))
    _draw_btn(screen, PAUSE_RESTART_BTN, "重新开始",
              PAUSE_RESTART_BTN.collidepoint(mp), text_col=(255, 120, 130))
    _draw_btn(screen, PAUSE_MENU_BTN, "返回主菜单",
              PAUSE_MENU_BTN.collidepoint(mp), text_col=(180, 220, 255))
    font = get_font(14)
    txt = font.render("ESC 继续    点击按钮选择", True, C_TEXT_DIM)
    rect = txt.get_rect(center=(SCREEN_W // 2, PAUSE_MENU_BTN.bottom + 28))
    screen.blit(txt, rect)


# ---------- 波次提示 ----------
def draw_wave_intro(screen, wave, alpha):
    if alpha <= 0:
        return
    font = get_font(56, bold=True)
    surf = font.render("第 %d 波" % wave, True, C_GOLD)
    surf.set_alpha(int(alpha))
    rect = surf.get_rect(center=(SCREEN_W // 2, SCREEN_H * 0.32))
    screen.blit(surf, rect)
    sub = get_font(18).render("WAVE %d" % wave, True, C_TEXT_DIM)
    sub.set_alpha(int(alpha * 0.8))
    srect = sub.get_rect(center=(SCREEN_W // 2, SCREEN_H * 0.32 + 44))
    screen.blit(sub, srect)


# ---------- HUD ----------
class HUD:
    def __init__(self):
        self.prev = {}
        self.pop = {}
        self.big_font = get_font(40, bold=True)

    def _push(self, key, value):
        if key not in self.prev:
            self.prev[key] = value
            self.pop[key] = 0.0
        elif value != self.prev[key]:
            self.prev[key] = value
            self.pop[key] = 1.0

    def update(self, dt, player, wave, level):
        self._push("atk", player.attack)
        self._push("spd", round(1.0 / player.fire_interval, 1))
        self._push("units", player.alive_count())
        self._push("wave", wave)
        self._push("level", level)
        for k in self.pop:
            if self.pop[k] > 0:
                self.pop[k] = max(0.0, self.pop[k] - dt * 3.0)

    def _draw_stat(self, screen, x, y, label, value, key, color=C_TEXT):
        lf = get_font(14)
        ls = lf.render(label, True, C_TEXT_DIM)
        screen.blit(ls, (x, y))
        scale = 1.0 + 0.35 * self.pop.get(key, 0.0)
        vf = get_font(int(22 * scale), bold=True)
        vs = vf.render(_fmt_val(value), True, color)
        screen.blit(vs, vs.get_rect(topleft=(x, y + 18)))

    def draw(self, screen, player, wave, level):
        self._draw_stat(screen, 50, 8, "攻击", player.attack, "atk", C_GOLD)
        self._draw_stat(screen, 130, 8, "攻速/秒", round(1.0 / player.fire_interval, 1), "spd", C_SHIP_CORE2)
        self._draw_stat(screen, 230, 8, "单位", "%d/%d" % (player.alive_count(), MAX_UNITS), "units", C_CLONE_GLOW)
        self._draw_stat(screen, SCREEN_W - 150, 8, "波次", wave, "wave", C_GOLD)
        self._draw_stat(screen, SCREEN_W - 70, 8, "宝箱等级", level, "level", C_CHEST_LID)
        hint = get_font(13).render("移动鼠标控制队伍    ESC 暂停    结束点按钮重开", True, C_TEXT_DIM)
        screen.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2, SCREEN_H - 16))


# ---------- 浮动奖励文字 ----------
class FloatingText:
    def __init__(self, x, y, text, color=C_GOLD):
        self.x = x
        self.y = y
        self.text = text
        self.color = color
        self.life = 1.2
        self.max_life = 1.2
        self.vy = -30

    def update(self, dt):
        self.y += self.vy * dt
        self.life -= dt

    def draw(self, screen):
        if self.life <= 0:
            return
        ratio = self.life / self.max_life
        font = get_font(18, bold=True)
        surf = font.render(self.text, True, self.color)
        surf.set_alpha(int(255 * ratio))
        screen.blit(surf, (int(self.x - surf.get_width() // 2), int(self.y)))


# ---------- BOSS 出场展示 ----------
def draw_boss_intro(screen, t):
    overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 170))
    screen.blit(overlay, (0, 0))
    cx, cy = SCREEN_W // 2, SCREEN_H // 2 - 20
    pulse = 1 + 0.18 * math.sin(t * 4)
    for r, col in [(150 * pulse, (180, 40, 120)),
                   (100 * pulse, (255, 80, 150)),
                   (60 * pulse, (255, 200, 200))]:
        g = pygame.Surface((int(r * 2), int(r * 2)), pygame.SRCALPHA)
        for rr in range(int(r), 0, -2):
            a = int(70 * (1 - rr / r))
            pygame.draw.circle(g, (*col, a), (int(r), int(r)), rr)
        screen.blit(g, (int(cx - r), int(cy - r)),
                    special_flags=pygame.BLEND_ADD)


def draw_boss_intro_name(screen, name, phase, t):
    cx = SCREEN_W // 2
    cy = SCREEN_H // 2 - 130
    tag_f = get_font(20, bold=True)
    tag = tag_f.render("- BOSS -", True, (255, 120, 160))
    tag.set_alpha(int(180 + 60 * math.sin(t * 5)))
    screen.blit(tag, tag.get_rect(center=(cx, cy - 50)))
    name_f = get_font(46, bold=True)
    glow_col = (255, 70, 130) if phase >= 2 else (255, 150, 200)
    for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
        s = name_f.render(name, True, glow_col)
        s.set_alpha(120)
        screen.blit(s, s.get_rect(center=(cx + dx, cy + dy)))
    main = name_f.render(name, True, (255, 240, 245))
    screen.blit(main, main.get_rect(center=(cx, cy)))
    sub_f = get_font(16)
    sub = sub_f.render("准备战斗 ...", True, C_TEXT_DIM)
    sub.set_alpha(int(150 + 80 * math.sin(t * 3)))
    screen.blit(sub, sub.get_rect(center=(cx, cy + 46)))


# ---------- 金身道具槽 / 无敌金边 ----------
def draw_item_slots(screen, invuln_item, clone_item, t):
    """左上角道具槽：上=无敌道具（左键），下=分身道具（右键）。"""
    # 无敌道具槽
    _draw_slot(screen, INVULN_SLOT_POS, INVULN_SLOT_R, invuln_item, t,
               C_INVULN_GOLD, C_INVULN_SLOT, "invuln")
    # 分身道具槽
    _draw_slot(screen, CLONE_SLOT_POS, INVULN_SLOT_R, clone_item, t,
               C_CLONE_GLOW, (60, 50, 90), "clone")


def _draw_slot(screen, pos, r, has_item, t, glow_col, empty_col, kind):
    cx, cy = pos
    slot_col = glow_col if has_item else empty_col
    pygame.draw.circle(screen, (20, 18, 30), (cx, cy), r + 2)
    pygame.draw.circle(screen, slot_col, (cx, cy), r, 2)
    if has_item:
        pulse = 1 + 0.18 * math.sin(t * 6)
        gr = int(r * 1.4 * pulse)
        g = pygame.Surface((gr * 2, gr * 2), pygame.SRCALPHA)
        for rr in range(gr, 0, -2):
            a = int(60 * (1 - rr / gr))
            pygame.draw.circle(g, (*glow_col, a), (gr, gr), rr)
        screen.blit(g, (cx - gr, cy - gr), special_flags=pygame.BLEND_ADD)
        if kind == "invuln":
            # 五角星图标
            pts = []
            for i in range(10):
                ang = -math.pi / 2 + i / 10 * math.tau + t * 0.5
                rr = r * 0.62 if i % 2 == 0 else r * 0.28
                pts.append((cx + math.cos(ang) * rr, cy + math.sin(ang) * rr))
            pygame.draw.polygon(screen, glow_col, pts)
            pygame.draw.polygon(screen, (255, 255, 255), pts, 1)
        else:
            # 分身图标：双菱形
            for ox in (-4, 4):
                pts = [(cx + ox, cy - 8), (cx + ox + 5, cy),
                       (cx + ox, cy + 8), (cx + ox - 5, cy)]
                pygame.draw.polygon(screen, glow_col, pts)
                pygame.draw.polygon(screen, (255, 255, 255), pts, 1)


def draw_invuln_border(screen, t):
    pulse = 0.7 + 0.3 * math.sin(t * 10)
    col = (int(255 * pulse), int(215 * pulse), int(90 * pulse))
    thick = 5
    pygame.draw.rect(screen, col, (0, 0, SCREEN_W, thick))
    pygame.draw.rect(screen, col, (0, SCREEN_H - thick, SCREEN_W, thick))
    pygame.draw.rect(screen, col, (0, 0, thick, SCREEN_H))
    pygame.draw.rect(screen, col, (SCREEN_W - thick, 0, thick, SCREEN_H))


# ======================================================================
# 主菜单
# ======================================================================
MENU_BTN_W, MENU_BTN_H = 280, 54
MENU_BTN_GAP = 14
MENU_ITEMS = [
    ("easy",      "简单",    "怪物更脆，BOSS 仅二阶段",      (120, 220, 120)),
    ("normal",    "普通",    "标准难度，BOSS 仅二阶段",      (255, 210, 90)),
    ("hard",      "困难",    "怪物更强，BOSS 三阶段",        (255, 130, 90)),
    ("nightmare", "噩梦",    "11 关含压轴 BOSS，三阶段",     (220, 80, 120)),
    ("help",      "游戏说明", "查看玩法 / BOSS / 数值",       (120, 180, 255)),
]


def menu_btn_rect(index):
    total = len(MENU_ITEMS) * MENU_BTN_H + (len(MENU_ITEMS) - 1) * MENU_BTN_GAP
    top = (SCREEN_H - total) // 2 + 60
    return pygame.Rect((SCREEN_W - MENU_BTN_W) // 2,
                       top + index * (MENU_BTN_H + MENU_BTN_GAP),
                       MENU_BTN_W, MENU_BTN_H)


def draw_main_menu(screen, t):
    mp = pygame.mouse.get_pos()
    cx = SCREEN_W // 2
    title_f = get_font(56, bold=True)
    for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
        s = title_f.render("Greedy Dash", True, (180, 80, 220))
        s.set_alpha(110)
        screen.blit(s, s.get_rect(center=(cx + dx, 120 + dy)))
    main = title_f.render("Greedy Dash", True, (255, 230, 255))
    screen.blit(main, main.get_rect(center=(cx, 120)))
    sub = get_font(20).render("贪逼牛逼 · 选择难度开始", True, C_TEXT_DIM)
    screen.blit(sub, sub.get_rect(center=(cx, 168)))
    for i, (key, name, desc, col) in enumerate(MENU_ITEMS):
        rect = menu_btn_rect(i)
        hov = rect.collidepoint(mp)
        bg = (50, 56, 95, 250) if hov else (24, 28, 55, 235)
        pygame.draw.rect(screen, bg, rect, border_radius=14)
        pygame.draw.rect(screen, col, rect, 2, border_radius=14)
        pygame.draw.rect(screen, col, rect.inflate(-6, -6), 1, border_radius=10)
        nf = get_font(24, bold=True).render(name, True, col)
        screen.blit(nf, nf.get_rect(midleft=(rect.x + 24, rect.centery)))
        df = get_font(14).render(desc, True, C_TEXT_DIM)
        screen.blit(df, df.get_rect(midright=(rect.right - 18, rect.centery)))
    hint = get_font(13).render("点击难度开始游戏 · 作者：%s" % AUTHOR,
                               True, C_TEXT_DIM)
    screen.blit(hint, hint.get_rect(center=(cx, SCREEN_H - 24)))


# ======================================================================
# 游戏说明（分页 + 垂直滚动）
# ======================================================================
DOC_PAGE_COUNT = 6
DOC_BTN_Y = SCREEN_H - 46
DOC_PREV_BTN = pygame.Rect(40, DOC_BTN_Y, 90, 32)
DOC_NEXT_BTN = pygame.Rect(SCREEN_W - 130, DOC_BTN_Y, 90, 32)
DOC_BACK_BTN = pygame.Rect(SCREEN_W // 2 - 60, DOC_BTN_Y, 120, 32)

# 滚动可视区
HELP_CONTENT_TOP = 86
HELP_CONTENT_BOTTOM = DOC_BTN_Y - 12
HELP_CONTENT_H = HELP_CONTENT_BOTTOM - HELP_CONTENT_TOP
HELP_CONTENT_W = SCREEN_W - 64        # 内容宽度（右侧留滚动条）
SCROLLBAR_X = SCREEN_W - 14
SCROLLBAR_W = 6
SCROLL_STEP = 52                      # 每次滚轮步进

_DOC_TITLES = ["游戏玩法", "操作方式", "宝箱奖励", "道具说明",
               "BOSS 系统", "数值表（四难度）"]


def help_max_scroll(content_h):
    return max(0, content_h - HELP_CONTENT_H)


def help_scrollbar_track_rect():
    return pygame.Rect(SCROLLBAR_X, HELP_CONTENT_TOP, SCROLLBAR_W, HELP_CONTENT_H)


def help_slider_rect(scroll, content_h):
    """返回滚动条滑块 Rect；内容不溢出时返回 None。"""
    ms = help_max_scroll(content_h)
    if ms <= 0:
        return None
    slider_h = max(34, int(HELP_CONTENT_H * HELP_CONTENT_H / content_h))
    ratio = scroll / ms
    sy = HELP_CONTENT_TOP + int((HELP_CONTENT_H - slider_h) * ratio)
    return pygame.Rect(SCROLLBAR_X, sy, SCROLLBAR_W, slider_h)


def _draw_scrollbar(screen, scroll, content_h):
    track = help_scrollbar_track_rect()
    pygame.draw.rect(screen, (40, 44, 70), track, border_radius=3)
    ms = help_max_scroll(content_h)
    if ms <= 0:
        return
    sl = help_slider_rect(scroll, content_h)
    pygame.draw.rect(screen, (120, 160, 220), sl, border_radius=3)


def _draw_doc_footer(screen, page):
    mp = pygame.mouse.get_pos()
    info = get_font(14).render("%d / %d" % (page + 1, DOC_PAGE_COUNT),
                               True, C_TEXT_DIM)
    screen.blit(info, info.get_rect(center=(SCREEN_W // 2, DOC_BTN_Y - 22)))
    _draw_btn(screen, DOC_PREV_BTN, "上一页", DOC_PREV_BTN.collidepoint(mp),
              text_col=C_TEXT, font_size=16)
    _draw_btn(screen, DOC_BACK_BTN, "返回主菜单", DOC_BACK_BTN.collidepoint(mp),
              text_col=(180, 220, 255), font_size=16)
    _draw_btn(screen, DOC_NEXT_BTN, "下一页", DOC_NEXT_BTN.collidepoint(mp),
              text_col=C_TEXT, font_size=16)


def _wrap(text, font, max_w):
    """简单中文按字符宽度折行。"""
    lines = []
    cur = ""
    for ch in text:
        if font.size(cur + ch)[0] > max_w:
            lines.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines


def draw_help_page(screen, page, scroll):
    """绘制说明页，返回内容总高度（用于滚动条与事件处理）。"""
    overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    overlay.fill((10, 14, 34, 230))
    screen.blit(overlay, (0, 0))
    tf = get_font(34, bold=True)
    ts = tf.render(_DOC_TITLES[page], True, C_GOLD)
    screen.blit(ts, ts.get_rect(center=(SCREEN_W // 2, 46)))
    pygame.draw.line(screen, C_RESUME_BORDER, (60, 76), (SCREEN_W - 60, 76), 1)

    # 裁剪到可视区，内容随 scroll 上移
    old_clip = screen.get_clip()
    screen.set_clip(pygame.Rect(0, HELP_CONTENT_TOP, SCREEN_W, HELP_CONTENT_H))
    if page == 0:
        content_h = _draw_gameplay(screen, scroll)
    elif page == 1:
        content_h = _draw_controls(screen, scroll)
    elif page == 2:
        content_h = _draw_chests(screen, scroll)
    elif page == 3:
        content_h = _draw_items(screen, scroll)
    elif page == 4:
        content_h = _draw_boss_doc(screen, scroll)
    else:
        content_h = _draw_stats_doc(screen, scroll)
    screen.set_clip(old_clip)

    _draw_scrollbar(screen, scroll, content_h)
    _draw_doc_footer(screen, page)
    return content_h


# --- 各页内容：base = HELP_CONTENT_TOP - scroll，y 从 0 递增，返回内容总高 ---
def _draw_gameplay(screen, scroll):
    f = get_font(16)
    base = HELP_CONTENT_TOP - scroll
    y = 6
    for line in G.GAMEPLAY_LINES:
        if line == "":
            y += 12
            continue
        for sub in _wrap(line, f, HELP_CONTENT_W):
            screen.blit(f.render(sub, True, C_TEXT), (30, base + y))
            y += 26
    return y + 6


def _draw_controls(screen, scroll):
    fl = get_font(16)
    fv = get_font(16, bold=True)
    base = HELP_CONTENT_TOP - scroll
    y = 6
    for op, way in G.CONTROL_ROWS:
        screen.blit(fl.render(op, True, C_TEXT_DIM), (30, base + y))
        vs = fv.render(way, True, C_TEXT)
        screen.blit(vs, vs.get_rect(midright=(SCREEN_W - 36, base + y + 9)))
        pygame.draw.line(screen, (60, 60, 90),
                         (30, base + y + 26), (SCREEN_W - 36, base + y + 26), 1)
        y += 36
    return y


def _draw_table(screen, x, y0, rows, col_widths, headers=None,
                font_size=15, header_col=C_GOLD, wrap_last=False):
    f = get_font(font_size)
    fb = get_font(font_size, bold=True)
    y = y0
    if headers:
        for i, h in enumerate(headers):
            cx = x + sum(col_widths[:i]) + col_widths[i] // 2
            s = fb.render(h, True, header_col)
            screen.blit(s, s.get_rect(center=(cx, y)))
        y += 26
    last_x = x + sum(col_widths[:-1])
    wrap_w = col_widths[-1] - 10
    for row in rows:
        if wrap_last:
            last_lines = _wrap(str(row[-1]), f, wrap_w)
            row_h = max(24, len(last_lines) * (font_size + 7))
            for i in range(len(row) - 1):
                cx = x + sum(col_widths[:i]) + col_widths[i] // 2
                s = f.render(str(row[i]), True, C_TEXT)
                screen.blit(s, s.get_rect(center=(cx, y + row_h // 2)))
            ly = y + 3
            for sub in last_lines:
                screen.blit(f.render(sub, True, C_TEXT), (last_x + 5, ly))
                ly += font_size + 7
            y += row_h + 4
        else:
            for i, cell in enumerate(row):
                cx = x + sum(col_widths[:i]) + col_widths[i] // 2
                s = f.render(str(cell), True, C_TEXT)
                screen.blit(s, s.get_rect(center=(cx, y)))
            y += 24
    return y


def _draw_chests(screen, scroll):
    f = get_font(15)
    base = HELP_CONTENT_TOP - scroll
    y = 6
    screen.blit(get_font(18, bold=True).render(
        "小宝箱（左侧固定 10 个，击破后 5 秒重生）", True, (255, 205, 90)),
        (30, base + y))
    y += 30
    y = _draw_table(screen, 30, base + y, G.SMALL_CHEST_ROWS,
                    [70, 50, HELP_CONTENT_W - 120],
                    headers=["奖励", "概率", "效果"], font_size=14,
                    wrap_last=True) - base
    for sub in _wrap(G.SMALL_CHEST_NOTE, f, HELP_CONTENT_W):
        screen.blit(f.render(sub, True, C_TEXT_DIM), (30, base + y))
        y += 24
    y += 18
    screen.blit(get_font(18, bold=True).render(
        "大宝箱（每波 1 个，从顶部缓慢下落）", True, (255, 205, 90)),
        (30, base + y))
    y += 30
    y = _draw_table(screen, 30, base + y, G.BIG_CHEST_ROWS,
                    [70, 50, HELP_CONTENT_W - 120],
                    headers=["奖励", "权重", "效果"], font_size=14,
                    wrap_last=True) - base
    for sub in _wrap(G.BIG_CHEST_NOTE, f, HELP_CONTENT_W):
        screen.blit(f.render(sub, True, C_TEXT_DIM), (30, base + y))
        y += 24
    return y


def _draw_items(screen, scroll):
    base = HELP_CONTENT_TOP - scroll
    y = 6
    f = get_font(15)
    for name, lines in G.ITEM_SECTIONS:
        screen.blit(get_font(20, bold=True).render(name, True, (255, 205, 90)),
                    (30, base + y))
        y += 30
        for ln in lines:
            for sub in _wrap(ln, f, HELP_CONTENT_W - 20):
                screen.blit(f.render(sub, True, C_TEXT), (44, base + y))
                y += 24
        y += 14
    return y


def _draw_boss_doc(screen, scroll):
    base = HELP_CONTENT_TOP - scroll
    y = 6
    f = get_font(14)
    for line in G.BOSS_INTRO_LINES:
        if line == "":
            y += 8
            continue
        for sub in _wrap(line, f, HELP_CONTENT_W):
            screen.blit(f.render(sub, True, C_TEXT_DIM), (30, base + y))
            y += 20
    y += 12
    fn = get_font(15, bold=True)
    fd = get_font(13)
    for row in G.BOSS_TABLE_ROWS:
        wv, name, typ, p1, p2, p3 = row
        ns = fn.render("%d. %s" % (wv, name), True, C_GOLD)
        screen.blit(ns, (30, base + y))
        ts = fd.render("[%s]" % typ, True, C_TEXT_DIM)
        screen.blit(ts, (30 + ns.get_width() + 8, base + y + 2))
        y += 22
        for label, txt in (("①", p1), ("②", p2), ("③", p3)):
            screen.blit(fd.render(label, True, (180, 220, 255)), (46, base + y))
            for sub in _wrap(txt, fd, HELP_CONTENT_W - 40):
                screen.blit(fd.render(sub, True, C_TEXT), (66, base + y))
                y += 17
        y += 10
    return y


def _draw_stats_doc(screen, scroll):
    base = HELP_CONTENT_TOP - scroll
    y = 6
    f = get_font(13)
    note_text = ("HP=(2+d+d²)(1+LIN·d+QUAD·d²) d=波次-1  "
                 "小宝箱×5 大宝箱×12 BOSS随难度(100/140/170/200)  怪物数=12+(w-1)×2")
    for sub in _wrap(note_text, f, HELP_CONTENT_W):
        screen.blit(f.render(sub, True, C_TEXT_DIM), (30, base + y))
        y += 18
    y += 10
    headers = ["波", "简单", "普通", "困难", "噩梦"]
    rows = G.all_difficulty_hp_rows()
    table_rows = [[r[0]] + [str(v) if v is not None else "—" for v in r[1:]]
                  for r in rows]
    y = _draw_table(screen, 24, base + y, table_rows, [40, 92, 92, 92, 92],
                    headers=headers, font_size=14) - base
    y += 14
    for txt in [
        "怪物数量（四难度一致）：12, 14, 16, ..., 30（噩梦第 11 关 = 32）",
        "难度差异：血量曲线 LIN/QUAD（简单 0.45/0.15 · 普通 0.6/0.2 · 困难 0.75/0.25 · 噩梦 0.9/0.32）",
        "波数：简单/普通/困难=10 · 噩梦=11；阶段：简单/普通=二阶段(50%) · 困难/噩梦=三阶段(70%/40%)",
        "BOSS 血量倍率随难度：简单 ×100 · 普通 ×140 · 困难 ×170 · 噩梦 ×200",
        "其余参数四难度一致：怪物基础数量 12 / 步进 2 / 玩家射速 0.30s / BOSS 子弹 200·320",
    ]:
        for sub in _wrap(txt, f, HELP_CONTENT_W):
            screen.blit(f.render(sub, True, C_TEXT_DIM), (30, base + y))
            y += 18
        y += 4
    return y


# ======================================================================
# 结算界面（通关 / 失败共用统计面板）
# ======================================================================
RESTART_BTN = pygame.Rect(SCREEN_W // 2 - 230, SCREEN_H - 130, 220, 50)
MENU_BACK_BTN = pygame.Rect(SCREEN_W // 2 + 10, SCREEN_H - 130, 220, 50)


def _fmt_time(t):
    t = int(t)
    return "%d:%02d" % (t // 60, t % 60)


def _draw_stats_panel(screen, game):
    p = game.player
    total = S.WAVE_TOTAL
    acc = "%.1f%%" % (game.shots_hit / game.shots_fired * 100) if game.shots_fired else "0.0%"
    stats = [
        ("难度", S.difficulty_name(game.difficulty)),
        ("游戏时间", _fmt_time(game.game_time)),
        ("击杀怪物", game.kill_count),
        ("击败 BOSS", "%d / %d" % (game.bosses_defeated, total)),
        ("击破小宝箱", game.chests_broken),
        ("击破大宝箱", game.big_chests_broken),
        ("攻击力", p.attack),
        ("射速/秒", round(1.0 / p.fire_interval, 1)),
        ("存活单位", "%d / %d" % (p.alive_count(), MAX_UNITS)),
        ("宝箱等级", game.global_level),
        ("造成的伤害", int(game.damage_dealt)),
        ("丢失的伤害", int(game.damage_lost)),
        ("命中率", acc),
    ]
    # 双列布局：左列 7 项、右列 6 项，避免底部与按钮重叠溢出
    panel_y = 235
    row_h = 38
    flab = get_font(16)
    fval = get_font(22, bold=True)
    LX, LVX = 26, 226       # 左列：标签左对齐 x、数值右对齐 x
    RX, RVX = 254, 474      # 右列
    for gi, (k, v) in enumerate(stats):
        if gi < 7:
            x, vx, i = LX, LVX, gi
        else:
            x, vx, i = RX, RVX, gi - 7
        yy = panel_y + i * row_h
        screen.blit(flab.render(k, True, C_TEXT_DIM), (x, yy))
        vs = fval.render(_fmt_val(v), True, C_GOLD)
        screen.blit(vs, vs.get_rect(midright=(vx, yy + 14)))


def draw_victory(screen, game):
    mp = pygame.mouse.get_pos()
    overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    overlay.fill((10, 20, 40, 215))
    screen.blit(overlay, (0, 0))
    cx = SCREEN_W // 2
    font = get_font(50, bold=True)
    for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
        s = font.render("通关结算", True, (255, 180, 60))
        s.set_alpha(110)
        screen.blit(s, s.get_rect(center=(cx + dx, 118 + dy)))
    main = font.render("通关结算", True, (255, 240, 180))
    screen.blit(main, main.get_rect(center=(cx, 118)))
    sub = get_font(18).render("你击败了全部 %d 位 BOSS！" % game.bosses_defeated,
                              True, C_TEXT)
    screen.blit(sub, sub.get_rect(center=(cx, 162)))
    _draw_stats_panel(screen, game)
    _draw_btn(screen, RESTART_BTN, "再来一局", RESTART_BTN.collidepoint(mp),
              text_col=C_GOLD)
    _draw_btn(screen, MENU_BACK_BTN, "返回主菜单", MENU_BACK_BTN.collidepoint(mp),
              text_col=(180, 220, 255))


def draw_gameover(screen, game):
    mp = pygame.mouse.get_pos()
    overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    overlay.fill((*C_OVERLAY, 205))
    screen.blit(overlay, (0, 0))
    cx = SCREEN_W // 2
    font = get_font(54, bold=True)
    for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
        s = font.render("游戏失败", True, (220, 60, 80))
        s.set_alpha(110)
        screen.blit(s, s.get_rect(center=(cx + dx, 118 + dy)))
    main = font.render("游戏失败", True, (255, 100, 120))
    screen.blit(main, main.get_rect(center=(cx, 118)))
    sub = get_font(18).render("你坚持到了第 %d 波" % game.wave, True, C_TEXT)
    screen.blit(sub, sub.get_rect(center=(cx, 162)))
    _draw_stats_panel(screen, game)
    _draw_btn(screen, RESTART_BTN, "重新开始", RESTART_BTN.collidepoint(mp),
              text_col=C_GOLD)
    _draw_btn(screen, MENU_BACK_BTN, "返回主菜单", MENU_BACK_BTN.collidepoint(mp),
              text_col=(180, 220, 255))
