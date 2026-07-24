# -*- coding: utf-8 -*-
"""
宝箱系统（左侧，固定 10 个）与怪物系统（右侧，波次生成）
"""
import math
import random

import pygame

from settings import *
import settings as S
from player import _glow  # 复用发光表面缓存


class Chest:
    """左侧宝箱：固定位置、不移动不攻击，被击破后延迟重生。"""
    def __init__(self, x, y, wave=1):
        self.x = x            # 中心 x
        self.y = y            # 中心 y
        self.alive = True
        self.max_hp = chest_hp(wave)
        self.hp = self.max_hp
        self.respawn_timer = 0.0
        self.phase = random.uniform(0, math.tau)  # 脉动相位

    def rect(self):
        h = CHEST_SIZE // 2
        return pygame.Rect(self.x - h, self.y - h, CHEST_SIZE, CHEST_SIZE)

    def hit(self, dmg):
        self.hp -= dmg

    def break_(self):
        """被击破：进入重生倒计时。"""
        self.alive = False
        self.respawn_timer = CHEST_RESPAWN

    def update(self, dt, wave):
        if not self.alive:
            self.respawn_timer -= dt
            if self.respawn_timer <= 0:
                # 重生时血量随当前波数提升（递归连乘）
                self.max_hp = chest_hp(wave)
                self.hp = self.max_hp
                self.alive = True

    def draw(self, screen, t):
        h = CHEST_SIZE // 2
        x, y = self.x, self.y
        if not self.alive:
            # 重生倒计时：绘制暗淡轮廓提示
            remain = max(0.0, self.respawn_timer)
            a = int(60 * (1 - remain / CHEST_RESPAWN))
            surf = pygame.Surface((CHEST_SIZE, CHEST_SIZE), pygame.SRCALPHA)
            pygame.draw.rect(surf, (*C_CHEST_EDGE, 40 + a), (0, 0, CHEST_SIZE, CHEST_SIZE), 2)
            screen.blit(surf, (x - h, y - h))
            return

        # 脉动金色光晕
        pulse = 1 + 0.18 * math.sin(t * 3 + self.phase)
        glow_r = (CHEST_SIZE * 0.9) * pulse
        gsurf = _glow(glow_r, C_CHEST_GLOW)
        screen.blit(gsurf, (int(x - glow_r), int(y - glow_r)),
                    special_flags=pygame.BLEND_ADD)

        # 箱体（圆角）
        body = pygame.Rect(x - h, y - h + 5, CHEST_SIZE, CHEST_SIZE - 5)
        pygame.draw.rect(screen, C_CHEST_BODY, body, border_radius=4)
        pygame.draw.rect(screen, C_CHEST_EDGE, body, 2, border_radius=4)
        # 箱盖（亮金）
        lid = pygame.Rect(x - h, y - h, CHEST_SIZE, 9)
        pygame.draw.rect(screen, C_CHEST_LID, lid, border_radius=4)
        pygame.draw.rect(screen, C_CHEST_EDGE, lid, 2, border_radius=4)
        # 宝石锁扣
        pygame.draw.circle(screen, C_CHEST_GEM, (x, y - h + 4), 3)
        pygame.draw.circle(screen, (255, 255, 255), (x, y - h + 4), 1)

        # 血条（上方 4px 处，长 20 高 2）
        bar_w, bar_h = 20, 2
        bx, by = x - bar_w // 2, y - h - 4 - bar_h
        pygame.draw.rect(screen, C_CHEST_HP_BG, (bx, by, bar_w, bar_h))
        ratio = max(0, self.hp / self.max_hp)
        pygame.draw.rect(screen, C_CHEST_HP, (bx, by, int(bar_w * ratio), bar_h))


class Monster:
    """右侧怪物：从顶部外生成，向下移动，波次机制。"""
    def __init__(self, x, y, hp):
        self.x = x
        self.y = y
        self.max_hp = hp
        self.hp = hp
        self.t = random.uniform(0, math.tau)
        self.dead = False
        self.flash = 0.0          # 死亡闪白计时
        # 生成固定的不规则多刺形状
        self.spikes = []
        n = random.randint(8, 11)
        for i in range(n):
            ang = i / n * math.tau
            rad = random.uniform(13, 18)
            if i % 3 == 0:
                rad += random.uniform(2, 5)   # 偶尔更长的刺
            self.spikes.append((ang, rad))
        self.eye_off = random.uniform(0, math.tau)

    def rect(self):
        return pygame.Rect(self.x - MONSTER_W // 2, self.y - MONSTER_H // 2,
                           MONSTER_W, MONSTER_H)

    def update(self, dt):
        self.y += MONSTER_SPEED * dt
        self.t += dt
        if self.flash > 0:
            self.flash -= dt

    def hit(self, dmg):
        self.hp -= dmg
        if self.hp <= 0:
            self.dead = True

    def off_screen(self):
        return self.y > S.SCREEN_H + MONSTER_H

    def reached_player_line(self, py):
        """怪物纵向已抵达玩家所在行（无论横向位置）。

        用于新的平衡规则：怪物一旦落到玩家这一行，就随机击杀一个单位，
        使玩家无法靠躲到最左/最右宝箱区来无限苟活。
        """
        return self.y + MONSTER_H // 2 >= py - UNIT_H // 2

    def draw(self, screen):
        x, y = self.x, self.y
        # 红色边缘光晕
        glow_r = 22 + 2 * math.sin(self.t * 5)
        gsurf = _glow(glow_r, C_MON_GLOW)
        screen.blit(gsurf, (int(x - glow_r), int(y - glow_r)),
                    special_flags=pygame.BLEND_ADD)

        # 多刺身体
        pts = [(x + math.cos(a) * r, y + math.sin(a) * r) for a, r in self.spikes]
        body_color = C_MON_BODY if self.flash <= 0 else (255, 255, 255)
        pygame.draw.polygon(screen, body_color, pts)
        pygame.draw.polygon(screen, C_MON_EDGE, pts, 2)

        if self.flash <= 0:
            # 发光摆动眼睛
            sway = math.sin(self.t * 4 + self.eye_off) * 3
            for ex in (-5, 5):
                pygame.draw.circle(screen, (40, 10, 20), (x + ex, y - 2), 4)
                pygame.draw.circle(screen, C_MON_EYE, (x + ex + sway * 0.2, y - 2), 2)

        # 血条（头顶 6px，长 28 高 3）
        bar_w, bar_h = 28, 3
        bx, by = x - bar_w // 2, y - MONSTER_H // 2 - 6 - bar_h
        pygame.draw.rect(screen, C_MON_HP_BG, (bx, by, bar_w, bar_h))
        ratio = max(0, self.hp / self.max_hp)
        pygame.draw.rect(screen, C_MON_HP, (bx, by, int(bar_w * ratio), bar_h))


class BigChest:
    """大宝箱：分割线左边右半部分生成，最多 1 个。
    - 从屏幕顶部外缓慢下落（40px/s），到达底部边界后消失（不给奖励）。
    - 血量 = 当前波怪物血量 * BIG_CHEST_HP_MULT（现 12）；包围盒 46×46，豪华金红配色 + 旋转光环。
    - 击破给特殊奖励（攻击增幅 / 超载火力 / 护盾 / 分身，加权概率）。
    """
    def __init__(self, x, y, hp):
        self.x = x
        self.y = y
        self.max_hp = hp
        self.hp = hp
        self.t = random.uniform(0, math.tau)
        self.ring = [random.uniform(0, math.tau) for _ in range(8)]  # 旋转光环相位

    def rect(self):
        h = BIG_CHEST_SIZE // 2
        return pygame.Rect(self.x - h, self.y - h, BIG_CHEST_SIZE, BIG_CHEST_SIZE)

    def hit(self, dmg):
        self.hp -= dmg

    def update(self, dt):
        self.y += BIG_CHEST_SPEED * dt
        self.t += dt

    def off_bottom(self):
        """到达底部边界（完全离开屏幕下沿）后消失。"""
        return self.y - BIG_CHEST_SIZE // 2 > S.SCREEN_H

    def draw(self, screen, t):
        x, y = self.x, self.y
        h = BIG_CHEST_SIZE // 2
        # 旋转光环
        for ph in self.ring:
            ang = ph + self.t * 1.5
            rx = x + math.cos(ang) * (h + 8)
            ry = y + math.sin(ang) * (h + 8)
            g = _glow(6, C_BIGCHEST_RING)
            screen.blit(g, (int(rx - 6), int(ry - 6)),
                        special_flags=pygame.BLEND_ADD)
        # 脉动金红光晕
        pulse = 1 + 0.15 * math.sin(self.t * 3)
        gsurf = _glow((h + 6) * pulse, C_BIGCHEST_GLOW)
        screen.blit(gsurf, (int(x - (h + 6) * pulse), int(y - (h + 6) * pulse)),
                    special_flags=pygame.BLEND_ADD)
        # 箱体（圆角，豪华金红）
        body = pygame.Rect(x - h, y - h + 8, BIG_CHEST_SIZE, BIG_CHEST_SIZE - 8)
        pygame.draw.rect(screen, C_BIGCHEST_BODY, body, border_radius=6)
        pygame.draw.rect(screen, C_BIGCHEST_EDGE, body, 3, border_radius=6)
        # 箱盖（亮金）
        lid = pygame.Rect(x - h, y - h, BIG_CHEST_SIZE, 14)
        pygame.draw.rect(screen, C_BIGCHEST_LID, lid, border_radius=6)
        pygame.draw.rect(screen, C_BIGCHEST_EDGE, lid, 3, border_radius=6)
        # 宝石锁扣
        pygame.draw.circle(screen, C_BIGCHEST_GEM, (x, y - h + 7), 5)
        pygame.draw.circle(screen, (255, 255, 255), (x, y - h + 7), 2)
        # 粗血条（头顶，长 40 高 4）
        bar_w, bar_h = 40, 4
        bx, by = x - bar_w // 2, y - h - 6 - bar_h
        pygame.draw.rect(screen, C_CHEST_HP_BG, (bx, by, bar_w, bar_h))
        ratio = max(0, self.hp / self.max_hp)
        pygame.draw.rect(screen, C_CHEST_HP, (bx, by, int(bar_w * ratio), bar_h))
