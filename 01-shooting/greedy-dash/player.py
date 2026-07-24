# -*- coding: utf-8 -*-
"""
玩家单位组机制：本体 + 分身
- 初始 1 个单位（本体），水平排列成队列，位于屏幕底部中央。
- 移动鼠标控制整个队列左右平移（仅横向跟随，Y 固定），严格限制在屏幕内。
- 每个单位独立且自动向上发射子弹，伤害与射速全队共享。
- 怪物碰到任一单位，该单位立即消失；只要还有单位存活，游戏继续。
"""
import math
import os
import random

import pygame

from settings import *
import settings as S


class Player:
    def __init__(self):
        self.reset()

    def reset(self):
        self.x = SCREEN_W // 2          # 队列中心 x
        # 玩家固定在底部：跟随 SCREEN_H，使手机端按设备比例拉高后玩家依旧贴底
        self.y = S.SCREEN_H - PLAYER_BOTTOM_GAP
        self.units = 1                   # 当前单位数量
        self.alive_units = [True]        # 每个单位存活状态
        self.shields = [False]           # 每个单位的护盾状态（与 alive_units 对齐）
        self.attack = ATTACK_BASE        # 攻击力（共享）
        self.fire_interval = FIRE_INTERVAL_BASE  # 射击间隔（共享）
        self.speed_bonus = 0.0           # 攻速加成累计
        self.fire_timer = 0.0            # 射击计时
        self.t = 0.0                     # 动画时间
        # 临时分身（大宝箱"新增单位"奖励，持续 TEMP_CLONE_TIME 秒）
        self.temp_clones = []            # [{"timer":float,"alive":bool}, ...]
        # 金身（无敌道具）：拾取后存入道具槽，左键使用进入 INVULN_TIME 秒无敌
        self.invuln_item = False         # 是否持有无敌道具
        self.invuln_timer = 0.0          # 无敌剩余时间
        # 分身道具：拾取后存入道具槽，右键释放召唤临时分身
        self.clone_item = False          # 是否持有分身道具

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

    # ---------- 临时分身 ----------
    def add_temp_clone(self):
        """召唤一个持续 TEMP_CLONE_TIME 秒的临时分身（最多 TEMP_CLONE_MAX 个）。"""
        if len(self.temp_clones) >= TEMP_CLONE_MAX:
            return False
        self.temp_clones.append({"timer": TEMP_CLONE_TIME, "alive": True})
        return True

    def clone_positions(self):
        """存活临时分身的中心 x 坐标（排布在主队列两侧外侧）。"""
        pos = []
        half_span = (self.units - 1) / 2.0 * UNIT_SPACING + UNIT_W / 2
        base = half_span + UNIT_SPACING * 0.7
        alive = [c for c in self.temp_clones if c["alive"]]
        for i in range(len(alive)):
            side = -1 if i % 2 == 0 else 1
            k = (i // 2) + 1
            pos.append(self.x + side * (base + (k - 1) * UNIT_SPACING))
        return pos

    def destroy_clone(self):
        """销毁一个存活临时分身（被 BOSS 子弹命中时）。成功返回 True。"""
        for c in self.temp_clones:
            if c["alive"]:
                c["alive"] = False
                self.temp_clones = [c for c in self.temp_clones if c["alive"]]
                return True
        return False

    # ---------- 金身（无敌道具）----------
    def add_invuln_item(self):
        """获得无敌道具（仅持有一个）。已有则返回 False。"""
        if self.invuln_item:
            return False
        self.invuln_item = True
        return True

    def use_invuln(self):
        """使用金身：进入 INVULN_TIME 秒无敌。无道具返回 False。"""
        if not self.invuln_item:
            return False
        self.invuln_item = False
        self.invuln_timer = INVULN_TIME
        return True

    def is_invincible(self):
        return self.invuln_timer > 0

    # ---------- 分身道具 ----------
    def add_clone_item(self):
        """获得分身道具（仅持有一个）。已有则返回 False。"""
        if self.clone_item:
            return False
        self.clone_item = True
        return True

    def use_clone(self):
        """使用分身道具：召唤一个临时分身。无道具返回 False。"""
        if not self.clone_item:
            return False
        self.clone_item = False
        return self.add_temp_clone()

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
        # 无敌计时
        if self.invuln_timer > 0:
            self.invuln_timer = max(0.0, self.invuln_timer - dt)
        # 临时分身计时：到期即消失
        for c in self.temp_clones:
            c["timer"] -= dt
            if c["timer"] <= 0:
                c["alive"] = False
        self.temp_clones = [c for c in self.temp_clones if c["alive"]]

    def should_fire(self):
        if self.fire_timer >= self.fire_interval:
            self.fire_timer = 0.0
            return True
        return False

    # ---------- 绘制 ----------
    def draw(self, screen):
        # 无敌闪烁（约 9Hz 亮灭），代表无敌状态
        if self.is_invincible() and int(self.t * 18) % 2 == 0:
            return
        for idx, px in enumerate(self.unit_positions()):
            self._draw_unit(screen, px, idx == 0, self.shields[idx])
        # 临时分身（用分身配色，无护盾）
        for cx in self.clone_positions():
            self._draw_unit(screen, cx, False, False)

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
    r = int(radius)
    key = (r, color)
    if key in _GLOW_CACHE:
        return _GLOW_CACHE[key]
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
