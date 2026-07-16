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
RESUME_BTN = pygame.Rect(SCREEN_W // 2 - 110, SCREEN_H // 2 - 30, 220, 60)

def draw_pause_overlay(screen):
    # 半透明黑色遮罩
    overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    overlay.fill((*C_OVERLAY, 180))
    screen.blit(overlay, (0, 0))

    # “继续游戏”按钮（圆角矩形 + 科幻边框）
    pygame.draw.rect(screen, (20, 24, 50, 230), RESUME_BTN, border_radius=14)
    pygame.draw.rect(screen, C_RESUME_BORDER, RESUME_BTN, 2, border_radius=14)
    pygame.draw.rect(screen, C_RESUME_BORDER, RESUME_BTN.inflate(-6, -6), 1, border_radius=10)

    # 白色播放三角（指向右）
    cx, cy = RESUME_BTN.center
    tri = [(cx - 14, cy - 16), (cx - 14, cy + 16), (cx + 20, cy)]
    pygame.draw.polygon(screen, C_PLAY_TRI, tri)

    # 提示文字
    font = get_font(20)
    txt = font.render("点击继续游戏", True, C_TEXT_DIM)
    rect = txt.get_rect(center=(SCREEN_W // 2, RESUME_BTN.bottom + 26))
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


# ---------- 游戏结束 ----------
RESTART_BTN = pygame.Rect(SCREEN_W // 2 - 110, SCREEN_H * 0.4 + 140, 220, 60)

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
    bg = (20, 24, 50, 230) if not hovered else (40, 46, 80, 245)
    pygame.draw.rect(screen, bg, RESTART_BTN, border_radius=14)
    pygame.draw.rect(screen, C_RESUME_BORDER, RESTART_BTN, 2, border_radius=14)
    pygame.draw.rect(screen, C_RESUME_BORDER, RESTART_BTN.inflate(-6, -6), 1, border_radius=10)
    bf = get_font(24, bold=True)
    bs = bf.render("重新开始", True, C_GOLD)
    brect = bs.get_rect(center=RESTART_BTN.center)
    screen.blit(bs, brect)
