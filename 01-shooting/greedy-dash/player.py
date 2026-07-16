# -*- coding: utf-8 -*-
"""
玩家单位组机制：本体 + 分身
- 初始 1 个单位（本体），水平排列成队列，位于屏幕底部中央。
- 移动鼠标控制整个队列左右平移（仅横向跟随，Y 固定），严格限制在屏幕内。
- 每个单位独立且自动向上发射子弹，伤害与射速全队共享。
- 怪物碰到任一单位，该单位立即消失；只要还有单位存活，游戏继续。
"""
import math
import random

import pygame

from settings import *


class Player:
    def __init__(self):
        self.reset()

    def reset(self):
        self.x = SCREEN_W // 2          # 队列中心 x
        self.y = PLAYER_Y
        self.units = 1                   # 当前单位数量
        self.alive_units = [True]        # 每个单位存活状态
        self.shields = [False]           # 每个单位的护盾状态（与 alive_units 对齐）
        self.attack = ATTACK_BASE        # 攻击力（共享）
        self.fire_interval = FIRE_INTERVAL_BASE  # 射击间隔（共享）
        self.speed_bonus = 0.0           # 攻速加成累计
        self.fire_timer = 0.0            # 射击计时
        self.t = 0.0                     # 动画时间

    # ---------- 单位管理 ----------
    def add_unit(self):
        """新增一个单位（分身）。达到上限返回 False。"""
        if self.units < MAX_UNITS:
            self.units += 1
            self.alive_units.append(True)
            self.shields.append(False)
            return True
        return False

    def alive_count(self):
        return sum(1 for a in self.alive_units if a)

    def is_dead(self):
        return self.alive_count() == 0

    def unit_positions(self):
        """返回当前存活单位的中心 x 坐标列表。"""
        positions = []
        n = self.units
        for i in range(n):
            if self.alive_units[i]:
                offset = (i - (n - 1) / 2.0) * UNIT_SPACING
                positions.append(self.x + offset)
        return positions

    # ---------- 护盾 ----------
    def add_shield_random(self):
        """随机给一个无护盾的存活单位加护盾。全部已有护盾返回 False。"""
        cand = [i for i in range(self.units)
                if self.alive_units[i] and not self.shields[i]]
        if cand:
            self.shields[random.choice(cand)] = True
            return True
        return False

    def all_shielded(self):
        """是否所有存活单位都已有护盾（用于隐藏护盾奖励选项）。"""
        alive = [i for i in range(self.units) if self.alive_units[i]]
        return len(alive) > 0 and all(self.shields[i] for i in alive)

    def kill_random_unit(self):
        """怪物抵达玩家行时调用：优先用护盾抵消（护盾单位优先被撞），
        无护盾则随机击杀一个存活单位。"""
        alive_idx = [i for i in range(self.units) if self.alive_units[i]]
        if not alive_idx:
            return
        # 优先抵消有护盾的单位
        shielded = [i for i in alive_idx if self.shields[i]]
        if shielded:
            i = random.choice(shielded)
            self.shields[i] = False      # 消耗护盾，单位存活
        else:
            i = random.choice(alive_idx)
            self.alive_units[i] = False
            self.shields[i] = False

    # ---------- 属性成长 ----------
    def apply_attack(self, amount):
        self.attack += amount

    def apply_speed(self, level, mult=1):
        """攻速永久提升（10% + 全局等级*1%）* mult，间隔缩短，效果叠加。"""
        self.speed_bonus += (0.10 + 0.01 * level) * mult
        self.fire_interval = FIRE_INTERVAL_BASE / (1.0 + self.speed_bonus)

    # ---------- 移动与更新 ----------
    def follow_mouse(self, mx, dt=None):
        """队列中心 x 实时贴合鼠标 x（无延迟）；y 固定，不跟随鼠标垂直移动。"""
        self.x = mx
        # 严格限制在屏幕内（整个队列不能越界）
        half_span = (self.units - 1) / 2.0 * UNIT_SPACING + UNIT_W / 2
        left_limit = half_span
        right_limit = SCREEN_W - half_span
        if left_limit > right_limit:
            self.x = SCREEN_W / 2
        else:
            self.x = max(left_limit, min(right_limit, self.x))

    def update(self, dt):
        self.t += dt
        self.fire_timer += dt

    def should_fire(self):
        if self.fire_timer >= self.fire_interval:
            self.fire_timer = 0.0
            return True
        return False

    # ---------- 绘制 ----------
    def draw(self, screen):
        for idx, px in enumerate(self.unit_positions()):
            self._draw_unit(screen, px, idx == 0, self.shields[idx])

    def _draw_unit(self, screen, cx, is_body, has_shield):
        y = self.y
        t = self.t
        glow = C_SHIP_GLOW if is_body else C_CLONE_GLOW
        # 脉动光晕
        pulse = 1 + 0.12 * math.sin(t * 4 + cx * 0.05)
        glow_r = (24 if is_body else 22) * pulse
        gsurf = _glow(glow_r, glow)
        screen.blit(gsurf, (int(cx - glow_r), int(y - glow_r)),
                    special_flags=pygame.BLEND_ADD)

        # 飞船多边形（菱形/六边形）
        pts = [
            (cx, y - 10),
            (cx + 14, y - 4),
            (cx + 16, y + 8),
            (cx - 16, y + 8),
            (cx - 14, y - 4),
        ]
        # 主体填充
        pygame.draw.polygon(screen, C_SHIP_CORE, pts)
        # 内层高光
        inner = [(cx, y - 5), (cx + 8, y - 2), (cx + 9, y + 5),
                 (cx - 9, y + 5), (cx - 8, y - 2)]
        pygame.draw.polygon(screen, C_SHIP_CORE2, inner)
        # 白色描边
        pygame.draw.polygon(screen, C_SHIP_EDGE, pts, 2)
        # 驾驶舱亮点
        pygame.draw.circle(screen, C_SHIP_EDGE, (cx, y - 1), 3)

        # 护盾：淡蓝保护罩（有辨识度）
        if has_shield:
            dome = _glow(20, C_SHIELD)
            screen.blit(dome, (int(cx - 20), int(y - 20)),
                        special_flags=pygame.BLEND_ADD)
            pygame.draw.circle(screen, C_SHIELD, (cx, y), 18, 2)


# 简单缓存的发光表面（按半径+颜色缓存，避免重复创建）
_GLOW_CACHE = {}

def _glow(radius, color):
    key = (int(radius), color)
    if key in _GLOW_CACHE:
        return _GLOW_CACHE[key]
    r = int(radius)
    surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
    for rr in range(r, 0, -1):
        alpha = int(180 * (1 - rr / r))
        pygame.draw.circle(surf, (*color, alpha), (r, r), rr)
    _GLOW_CACHE[key] = surf
    return surf


# 预先 set_alpha 的发光表面缓存（按半径+颜色+量化 alpha）。
# 关键优化：子弹拖尾/发光粒子原本每帧都 .copy()+.set_alpha() 创建新 Surface，
# 是主要卡顿来源。这里把 alpha 量化成有限档并缓存，彻底消除每帧的 Surface 分配。
_GLOW_ALPHA_CACHE = {}

def _glow_alpha(radius, color, alpha):
    r = int(radius)
    a = max(0, min(255, int(alpha)))
    a = (a // 16) * 16          # 量化到 16 档，提升缓存命中率
    key = (r, color, a)
    surf = _GLOW_ALPHA_CACHE.get(key)
    if surf is None:
        surf = _glow(r, color).copy()
        surf.set_alpha(a)
        _GLOW_ALPHA_CACHE[key] = surf
    return surf
