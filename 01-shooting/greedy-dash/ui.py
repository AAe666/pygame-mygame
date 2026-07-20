# -*- coding: utf-8 -*-
"""
UI 绘制：暂停按钮、暂停遮罩、波次提示、HUD（数值弹跳）、游戏结束、浮动文字
"""
import math

import pygame

from settings import *

# ---------- 字体 ----------
_font_cache = {}

def get_font(size, bold=False):
    """尝试使用支持中文的系统字体，回退到默认。"""
    names = ["Microsoft YaHei", "SimHei", "SimSun", "Arial"]
    for n in names:
        try:
            f = pygame.font.SysFont(n, size, bold=bold)
            if f:
                return f
        except Exception:
            continue
    return pygame.font.Font(None, size)


# ---------- 暂停按钮 ----------
PAUSE_BTN = pygame.Rect(10, 10, 30, 30)

def draw_pause_button(screen, hovered=False):
    surf = pygame.Surface((PAUSE_BTN.w, PAUSE_BTN.h), pygame.SRCALPHA)
    bg = (30, 30, 55, 200) if not hovered else (50, 50, 85, 220)
    pygame.draw.rect(surf, bg, (0, 0, PAUSE_BTN.w, PAUSE_BTN.h), border_radius=6)
    pygame.draw.rect(surf, C_RESUME_BORDER, (0, 0, PAUSE_BTN.w, PAUSE_BTN.h),
                     1, border_radius=6)
    # 两个白色竖条：宽 4，高 16，间距 6，居中
    bw, bh, gap = 4, 16, 6
    total = bw * 2 + gap
    start_x = (PAUSE_BTN.w - total) / 2
    cy = (PAUSE_BTN.h - bh) / 2
    pygame.draw.rect(surf, C_PAUSE_ICON, (start_x, cy, bw, bh))
    pygame.draw.rect(surf, C_PAUSE_ICON, (start_x + bw + gap, cy, bw, bh))
    screen.blit(surf, PAUSE_BTN.topleft)


# ---------- 暂停遮罩 ----------
RESUME_BTN = pygame.Rect(SCREEN_W // 2 - 110, SCREEN_H // 2 - 60, 220, 56)
PAUSE_RESTART_BTN = pygame.Rect(SCREEN_W // 2 - 110, SCREEN_H // 2 + 20, 220, 50)


def _draw_btn(screen, rect, text, hovered, text_col=C_GOLD):
    bg = (40, 46, 80, 245) if hovered else (20, 24, 50, 230)
    pygame.draw.rect(screen, bg, rect, border_radius=12)
    pygame.draw.rect(screen, C_RESUME_BORDER, rect, 2, border_radius=12)
    pygame.draw.rect(screen, C_RESUME_BORDER, rect.inflate(-6, -6), 1, border_radius=8)
    bs = get_font(22, bold=True).render(text, True, text_col)
    screen.blit(bs, bs.get_rect(center=rect.center))


def draw_pause_overlay(screen, restart_hovered=False):
    # 半透明黑色遮罩
    overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    overlay.fill((*C_OVERLAY, 180))
    screen.blit(overlay, (0, 0))

    # 标题
    tf = get_font(40, bold=True)
    ts = tf.render("已暂停", True, C_TEXT)
    screen.blit(ts, ts.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - 130)))

    # “继续游戏”按钮（圆角矩形 + 科幻边框）
    pygame.draw.rect(screen, (20, 24, 50, 230), RESUME_BTN, border_radius=12)
    pygame.draw.rect(screen, C_RESUME_BORDER, RESUME_BTN, 2, border_radius=12)
    pygame.draw.rect(screen, C_RESUME_BORDER, RESUME_BTN.inflate(-6, -6), 1, border_radius=8)
    # 白色播放三角（指向右）
    cx, cy = RESUME_BTN.center
    tri = [(cx - 14, cy - 13), (cx - 14, cy + 13), (cx + 18, cy)]
    pygame.draw.polygon(screen, C_PLAY_TRI, tri)
    rl = get_font(18).render("继续游戏", True, C_TEXT_DIM)
    screen.blit(rl, rl.get_rect(midleft=(cx + 26, cy)))

    # “重新开始”按钮
    _draw_btn(screen, PAUSE_RESTART_BTN, "重新开始", restart_hovered, text_col=(255, 120, 130))

    # 提示文字
    font = get_font(14)
    txt = font.render("ESC 继续    点击按钮选择", True, C_TEXT_DIM)
    rect = txt.get_rect(center=(SCREEN_W // 2, PAUSE_RESTART_BTN.bottom + 24))
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
    # 副标题
    sub = get_font(18).render("WAVE %d" % wave, True, C_TEXT_DIM)
    sub.set_alpha(int(alpha * 0.8))
    srect = sub.get_rect(center=(SCREEN_W // 2, SCREEN_H * 0.32 + 44))
    screen.blit(sub, srect)


# ---------- HUD（数值弹跳） ----------
class HUD:
    def __init__(self):
        self.prev = {}
        self.pop = {}  # 数值变化时的弹跳缩放
        self.big_font = get_font(40, bold=True)  # 大宝箱奖励提示用大号字

    def _push(self, key, value):
        if key not in self.prev:
            self.prev[key] = value
            self.pop[key] = 0.0
        elif value != self.prev[key]:
            self.prev[key] = value
            self.pop[key] = 1.0  # 触发弹跳

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
        # 标签
        lf = get_font(14)
        ls = lf.render(label, True, C_TEXT_DIM)
        screen.blit(ls, (x, y))
        # 数值（弹跳缩放）
        scale = 1.0 + 0.35 * self.pop.get(key, 0.0)
        vf = get_font(int(22 * scale), bold=True)
        vs = vf.render(str(value), True, color)
        vsr = vs.get_rect(topleft=(x, y + 18))
        screen.blit(vs, vsr)

    def draw(self, screen, player, wave, level):
        # 左上角信息（避开暂停按钮）
        self._draw_stat(screen, 50, 8, "攻击", player.attack, "atk", C_GOLD)
        self._draw_stat(screen, 130, 8, "攻速/秒", round(1.0 / player.fire_interval, 1), "spd", C_SHIP_CORE2)
        self._draw_stat(screen, 230, 8, "单位", "%d/%d" % (player.alive_count(), MAX_UNITS), "units", C_CLONE_GLOW)
        # 右上角
        self._draw_stat(screen, SCREEN_W - 150, 8, "波次", wave, "wave", C_GOLD)
        self._draw_stat(screen, SCREEN_W - 70, 8, "宝箱等级", level, "level", C_CHEST_LID)

        # 底部提示
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


# ---------- BOSS 出场展示（暂停游戏）----------
def draw_boss_intro(screen, t):
    """暗色遮罩 + 中央大光晕，BOSS 由主循环在遮罩之上绘制。"""
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
    """BOSS 名字（大号、霓虹描边），显示在 BOSS 上方。"""
    cx = SCREEN_W // 2
    cy = SCREEN_H // 2 - 130
    # 顶部小标签
    tag_f = get_font(20, bold=True)
    tag = tag_f.render("- BOSS -", True, (255, 120, 160))
    tag.set_alpha(int(180 + 60 * math.sin(t * 5)))
    screen.blit(tag, tag.get_rect(center=(cx, cy - 50)))
    # 名字：双层描边制造霓虹感
    name_f = get_font(52, bold=True)
    glow_col = (255, 70, 130) if phase == 2 else (255, 150, 200)
    for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
        s = name_f.render(name, True, glow_col)
        s.set_alpha(120)
        screen.blit(s, s.get_rect(center=(cx + dx, cy + dy)))
    main = name_f.render(name, True, (255, 240, 245))
    screen.blit(main, main.get_rect(center=(cx, cy)))
    # 副标题：波数
    sub_f = get_font(16)
    sub = sub_f.render("准备战斗 ...", True, C_TEXT_DIM)
    sub.set_alpha(int(150 + 80 * math.sin(t * 3)))
    screen.blit(sub, sub.get_rect(center=(cx, cy + 46)))


# ---------- 金身道具槽 / 无敌金边 ----------
def draw_invuln_slot(screen, has_item, t):
    """底部中央的道具槽：空槽暗淡，持有时显示金身图标（五角星）。"""
    cx, cy = INVULN_SLOT_POS
    r = INVULN_SLOT_R
    # 槽底圆
    slot_col = C_INVULN_GOLD if has_item else C_INVULN_SLOT
    pygame.draw.circle(screen, (20, 18, 30), (cx, cy), r + 2)
    pygame.draw.circle(screen, slot_col, (cx, cy), r, 2)
    if has_item:
        # 脉动金色光晕
        pulse = 1 + 0.18 * math.sin(t * 6)
        gr = int(r * 1.4 * pulse)
        g = pygame.Surface((gr * 2, gr * 2), pygame.SRCALPHA)
        for rr in range(gr, 0, -2):
            a = int(60 * (1 - rr / gr))
            pygame.draw.circle(g, (*C_INVULN_GOLD, a), (gr, gr), rr)
        screen.blit(g, (cx - gr, cy - gr), special_flags=pygame.BLEND_ADD)
        # 五角星图标
        pts = []
        for i in range(10):
            ang = -math.pi / 2 + i / 10 * math.tau + t * 0.5
            rr = r * 0.62 if i % 2 == 0 else r * 0.28
            pts.append((cx + math.cos(ang) * rr, cy + math.sin(ang) * rr))
        pygame.draw.polygon(screen, C_INVULN_GOLD, pts)
        pygame.draw.polygon(screen, (255, 255, 255), pts, 1)


def draw_invuln_border(screen, t):
    """无敌期间屏幕四周的金色边框（脉动），直观提示处于无敌。"""
    pulse = 0.7 + 0.3 * math.sin(t * 10)
    col = (int(255 * pulse), int(215 * pulse), int(90 * pulse))
    thick = 5
    pygame.draw.rect(screen, col, (0, 0, SCREEN_W, thick))                  # 上
    pygame.draw.rect(screen, col, (0, SCREEN_H - thick, SCREEN_W, thick))   # 下
    pygame.draw.rect(screen, col, (0, 0, thick, SCREEN_H))                  # 左
    pygame.draw.rect(screen, col, (SCREEN_W - thick, 0, thick, SCREEN_H))   # 右


# ---------- 游戏结束 ----------
RESTART_BTN = pygame.Rect(SCREEN_W // 2 - 110, SCREEN_H - 96, 220, 56)


def _fmt_time(t):
    t = int(t)
    return "%d:%02d" % (t // 60, t % 60)


def draw_gameover(screen, wave, hovered=False):
    overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    overlay.fill((*C_OVERLAY, 200))
    screen.blit(overlay, (0, 0))

    font = get_font(64, bold=True)
    surf = font.render("游戏结束", True, (255, 90, 110))
    rect = surf.get_rect(center=(SCREEN_W // 2, SCREEN_H * 0.4))
    screen.blit(surf, rect)

    sub = get_font(22).render("你坚持到了第 %d 波" % wave, True, C_TEXT)
    srect = sub.get_rect(center=(SCREEN_W // 2, SCREEN_H * 0.4 + 60))
    screen.blit(sub, srect)

    # “重新开始”按钮（圆角矩形 + 科幻边框，点击重开）
    _draw_btn(screen, RESTART_BTN, "重新开始", hovered, text_col=C_GOLD)


# ---------- 通关结算 ----------
def draw_victory(screen, game, hovered=False):
    overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    overlay.fill((10, 20, 40, 215))
    screen.blit(overlay, (0, 0))

    # 主标题（霓虹金）
    cx = SCREEN_W // 2
    font = get_font(54, bold=True)
    for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
        s = font.render("通关结算", True, (255, 180, 60))
        s.set_alpha(110)
        screen.blit(s, s.get_rect(center=(cx + dx, 118 + dy)))
    main = font.render("通关结算", True, (255, 240, 180))
    screen.blit(main, main.get_rect(center=(cx, 118)))

    sub = get_font(18).render("你击败了全部 %d 位 BOSS！" % game.bosses_defeated,
                              True, C_TEXT)
    screen.blit(sub, sub.get_rect(center=(cx, 162)))

    # 战绩面板
    p = game.player
    stats = [
        ("游戏时间", _fmt_time(game.game_time)),
        ("击杀怪物", game.kill_count),
        ("击败 BOSS", "%d / %d" % (game.bosses_defeated, WAVE_TOTAL)),
        ("击破小宝箱", game.chests_broken),
        ("击破大宝箱", game.big_chests_broken),
        ("攻击力", p.attack),
        ("射速/秒", round(1.0 / p.fire_interval, 1)),
        ("存活单位", "%d / %d" % (p.alive_count(), MAX_UNITS)),
        ("宝箱等级", game.global_level),
    ]
    panel_y = 200
    flab = get_font(17)
    fval = get_font(24, bold=True)
    for i, (k, v) in enumerate(stats):
        yy = panel_y + i * 36
        ls = flab.render(k, True, C_TEXT_DIM)
        screen.blit(ls, (cx - 120, yy))
        vs = fval.render(str(v), True, C_GOLD)
        screen.blit(vs, vs.get_rect(midright=(cx + 120, yy + 13)))

    # 重新开始按钮
    _draw_btn(screen, RESTART_BTN, "再来一局", hovered, text_col=C_GOLD)
