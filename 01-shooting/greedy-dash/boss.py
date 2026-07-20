# -*- coding: utf-8 -*-
"""
BOSS 系统：5 关 5 个 BOSS，每个有二阶段（50% 血量触发）。
- BOSS 固定在屏幕顶部，不下落，发射子弹攻击玩家。
- BOSS 子弹命中玩家单位 = 一只普通怪物触底（消耗护盾或随机击杀一单位）。
- BOSS 死亡才算通过当前波。
- 出场时居中放大展示 + 名字，期间游戏暂停（见 main.py 的 boss_intro 状态）。
"""
import math
import random

import pygame

from settings import *
from player import _glow
from enemy import Monster
from ui import get_font


# ---------- BOSS 子弹 ----------
class BossBullet:
    """BOSS 发射的敌方子弹，可任意方向飞行。"""
    __slots__ = ("x", "y", "vx", "vy", "color", "radius", "dead")

    def __init__(self, x, y, vx, vy, color=None, radius=5):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color or C_BOSS_BULLET
        self.radius = radius
        self.dead = False

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt

    def off(self):
        return (self.y > SCREEN_H + 20 or self.y < -30
                or self.x < -30 or self.x > SCREEN_W + 30)

    def draw(self, screen, t):
        r = self.radius
        gr = int(r * 2.4)
        g = _glow(gr, self.color)
        screen.blit(g, (int(self.x - gr), int(self.y - gr)),
                    special_flags=pygame.BLEND_ADD)
        pygame.draw.circle(screen, (255, 255, 255), (int(self.x), int(self.y)),
                           max(1, r - 1))
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), r, 2)


# ---------- BOSS 基类 ----------
class Boss:
    name = "BOSS"

    def __init__(self, x, y, hp, wave):
        self.x = x
        self.y = y
        self.max_hp = hp
        self.hp = hp
        self.wave = wave
        self.phase = 1
        self.t = 0.0
        self.fire_timer = 0.0
        self.dead = False
        self.flash = 0.0
        self._p2 = False
        self.intro = False        # 出场展示中（暂停）
        self.hit_w = 44           # 命中半宽
        self.hit_h = 36           # 命中半高
        self.bullets = []         # 待移交主循环的子弹
        self.summons = []         # 待移交主循环的小怪

    # ---- 战斗 ----
    def hit(self, dmg):
        self.hp -= dmg
        self.flash = 0.08
        if not self._p2 and self.hp <= self.max_hp * 0.5:
            self._p2 = True
            self.phase = 2
            self.on_phase2()
        if self.hp <= 0:
            self.hp = 0
            self.dead = True

    def on_phase2(self):
        """子类覆盖：二阶段数值/外观调整。"""
        pass

    def hit_test(self, bx, by):
        return abs(bx - self.x) <= self.hit_w and abs(by - self.y) <= self.hit_h

    # ---- 共用发射辅助 ----
    def _fire_aimed(self, player, speed, color=None, ox=None, oy=None):
        fx = ox if ox is not None else self.x
        fy = oy if oy is not None else self.y + 12
        dx = player.x - fx
        dy = player.y - fy
        d = math.hypot(dx, dy) or 1.0
        self.bullets.append(BossBullet(fx, fy, dx / d * speed, dy / d * speed,
                                       color=color))

    def _fire_fan(self, player, n, spread, speed, color=None):
        dx = player.x - self.x
        dy = player.y - self.y
        base = math.atan2(dy, dx)
        for i in range(n):
            off = 0 if n == 1 else (i - (n - 1) / 2.0) * spread
            a = base + off
            self.bullets.append(BossBullet(self.x, self.y + 12,
                                           math.cos(a) * speed,
                                           math.sin(a) * speed, color=color))

    def _fire_ring(self, base_rot, n, speed, color=None, ox=None, oy=None):
        fx = ox if ox is not None else self.x
        fy = oy if oy is not None else self.y
        for i in range(n):
            a = base_rot + i / n * math.tau
            self.bullets.append(BossBullet(fx, fy,
                                           math.cos(a) * speed,
                                           math.sin(a) * speed, color=color))

    # ---- 更新 / 绘制 ----
    def update(self, dt, player):
        self.t += dt
        if self.flash > 0:
            self.flash -= dt

    def draw(self, screen, t):
        pass

    def draw_hp_bar(self, screen):
        w = SCREEN_W - 80
        bx, by = 40, 46
        pygame.draw.rect(screen, C_BOSS_HP_BG, (bx, by, w, 12), border_radius=4)
        ratio = max(0.0, self.hp / self.max_hp)
        col = C_BOSS_HP if self.phase == 1 else (255, 150, 70)
        pygame.draw.rect(screen, col, (bx, by, int(w * ratio), 12),
                         border_radius=4)
        pygame.draw.rect(screen, C_BOSS_EDGE, (bx, by, w, 12), 1,
                         border_radius=4)
        font = get_font(14, bold=True)
        label = "%s  ·  阶段 %d" % (self.name, self.phase)
        s = font.render(label, True, C_TEXT)
        screen.blit(s, (bx + 4, by - 2))


# ---------- BOSS 1：裂隙之眼（散射/瞄准型）----------
class RiftEye(Boss):
    name = "裂隙之眼"

    def __init__(self, x, y, hp, wave):
        super().__init__(x, y, hp, wave)
        self.interval = 1.6
        self.charge = 0.8
        self.fan = 3
        self.spread = math.radians(15)
        self.speed = BOSS_BULLET_SPEED
        self._last_aim = (0.0, 1.0)
        self.hit_w = 42
        self.hit_h = 34

    def on_phase2(self):
        self.interval = 1.2
        self.fan = 5
        self.spread = math.radians(30)

    def update(self, dt, player):
        super().update(dt, player)
        dx = player.x - self.x
        dy = player.y - self.y
        d = math.hypot(dx, dy) or 1.0
        self._last_aim = (dx / d, dy / d)
        self.fire_timer += dt
        if self.fire_timer >= self.interval:
            self.fire_timer = 0.0
            self._fire_fan(player, self.fan, self.spread, self.speed)
            if self.phase == 2:
                self._fire_aimed(player, BOSS_BULLET_FAST)

    def draw(self, screen, t):
        x, y = self.x, self.y
        charging = self.fire_timer > self.interval - self.charge
        glow_col = (255, 80, 80) if self.phase == 2 else C_BOSS_GLOW
        iris = (255, 70, 70) if self.phase == 2 else (180, 60, 160)
        amp = 0.28 if charging else 0.10
        gr = int(40 * (1 + amp * math.sin(t * 6)))
        g = _glow(gr, glow_col)
        screen.blit(g, (int(x - gr), int(y - gr)),
                    special_flags=pygame.BLEND_ADD)
        n_spikes = 10 if self.phase == 2 else 6
        pts = []
        for i in range(n_spikes * 2):
            ang = i / (n_spikes * 2) * math.tau + t * 0.3
            r = 34 if i % 2 == 0 else 18
            pts.append((x + math.cos(ang) * r, y + math.sin(ang) * r))
        body = (255, 255, 255) if self.flash > 0 else C_BOSS_BODY
        pygame.draw.polygon(screen, body, pts)
        pygame.draw.polygon(screen, C_BOSS_EDGE, pts, 2)
        pygame.draw.circle(screen, (240, 230, 210), (int(x), int(y)), 20)
        pygame.draw.circle(screen, iris, (int(x), int(y)), 13)
        ax, ay = self._last_aim
        pygame.draw.circle(screen, (20, 0, 10),
                           (int(x + ax * 5), int(y + ay * 5)), 7)
        if charging:
            cg = _glow(14, (255, 240, 150))
            screen.blit(cg, (int(x - 14), int(y - 14)),
                        special_flags=pygame.BLEND_ADD)


# ---------- BOSS 2：漩涡核心（环形弹幕型）----------
class VortexCore(Boss):
    name = "漩涡核心"

    def __init__(self, x, y, hp, wave):
        super().__init__(x, y, hp, wave)
        self.rot = 0.0
        self.interval = 1.4
        self.ring_speed = 150
        self.aim_timer = 0.0
        self.hit_w = 40
        self.hit_h = 36

    def update(self, dt, player):
        super().update(dt, player)
        self.rot += dt * (1.2 if self.phase == 2 else 0.8)
        self.fire_timer += dt
        if self.fire_timer >= self.interval:
            self.fire_timer = 0.0
            self._fire_ring(self.rot, 12, self.ring_speed, color=C_BOSS_BULLET2)
            if self.phase == 2:
                # 第二环反向旋转（反向交叉）+ 半步偏移，金红子弹穿叉交错
                self._fire_ring(-self.rot + math.pi / 12, 12, self.ring_speed,
                                color=C_BOSS_BULLET)
        if self.phase == 2:
            self.aim_timer += dt
            if self.aim_timer >= 3.0:
                self.aim_timer = 0.0
                self._fire_aimed(player, BOSS_BULLET_FAST)

    def draw(self, screen, t):
        x, y = self.x, self.y
        glow_col = (120, 180, 255) if self.phase == 2 else C_BOSS_GLOW
        gr = int(40 * (1 + 0.10 * math.sin(t * 4)))
        g = _glow(gr, glow_col)
        screen.blit(g, (int(x - gr), int(y - gr)),
                    special_flags=pygame.BLEND_ADD)
        pts = [(x + math.cos(i / 12 * math.tau + self.rot) * 22,
                y + math.sin(i / 12 * math.tau + self.rot) * 22)
               for i in range(12)]
        body = (255, 255, 255) if self.flash > 0 else C_BOSS_BODY
        pygame.draw.polygon(screen, body, pts)
        pygame.draw.polygon(screen, C_BOSS_EDGE, pts, 2)
        if self.phase == 2:
            pts2 = [(x + math.cos(i / 12 * math.tau - self.rot) * 12,
                     y + math.sin(i / 12 * math.tau - self.rot) * 12)
                    for i in range(12)]
            pygame.draw.polygon(screen, (120, 200, 255), pts2)
        else:
            pygame.draw.circle(screen, C_BOSS_EYE, (int(x), int(y)), 8)
        rings = ([(0, self.rot, C_BOSS_BULLET2)] if self.phase == 1
                 else [(0, self.rot, C_BOSS_BULLET2),
                       (1, -self.rot + math.pi / 12, C_BOSS_BULLET)])
        for ring, base_rot, col in rings:
            r = 36 + ring * 10
            for i in range(12):
                ang = i / 12 * math.tau + base_rot
                nx = x + math.cos(ang) * r
                ny = y + math.sin(ang) * r
                gg = _glow(8, col)
                screen.blit(gg, (int(nx - 8), int(ny - 8)),
                            special_flags=pygame.BLEND_ADD)
                pygame.draw.circle(screen, col, (int(nx), int(ny)), 4)


# ---------- BOSS 3：虫巢母体（召唤型）----------
class HiveMatriarch(Boss):
    name = "虫巢母体"

    def __init__(self, x, y, hp, wave):
        super().__init__(x, y, hp, wave)
        self.interval = 2.0
        self.aim_timer = 0.0
        self.hit_w = 46
        self.hit_h = 38

    def on_phase2(self):
        self.interval = 1.4

    def update(self, dt, player):
        super().update(dt, player)
        self.fire_timer += dt
        if self.fire_timer >= self.interval:
            self.fire_timer = 0.0
            count = random.randint(2, 3) if self.phase == 2 else random.randint(1, 2)
            for _ in range(count):
                mx = random.randint(DIVIDER_X + 30, SCREEN_W - 30)
                self.summons.append(Monster(mx, self.y + 30, 3))
            if self.phase == 2:
                self._fire_fan(player, 3, math.radians(15), BOSS_BULLET_SPEED,
                               color=C_BOSS_BULLET2)
        if self.phase == 1:
            self.aim_timer += dt
            if self.aim_timer >= 3.0:
                self.aim_timer = 0.0
                self._fire_aimed(player, BOSS_BULLET_SPEED)

    def draw(self, screen, t):
        x, y = self.x, self.y
        glow_col = (255, 120, 80) if self.phase == 2 else C_BOSS_GLOW
        gr = int(42 * (1 + 0.12 * math.sin(t * 3)))
        g = _glow(gr, glow_col)
        screen.blit(g, (int(x - gr), int(y - gr)),
                    special_flags=pygame.BLEND_ADD)
        n = 12
        pts = []
        for i in range(n):
            ang = i / n * math.tau + t * 0.2
            r = 34 + (6 if i % 2 == 0 else 0) + 3 * math.sin(t * 4 + i)
            pts.append((x + math.cos(ang) * r, y + math.sin(ang) * r))
        body = (255, 255, 255) if self.flash > 0 else C_BOSS_BODY
        pygame.draw.polygon(screen, body, pts)
        pygame.draw.polygon(screen, C_BOSS_EDGE, pts, 2)
        pores = 5 if self.phase == 2 else 3
        for i in range(pores):
            ang = i / pores * math.tau + t * 0.1
            px = x + math.cos(ang) * 16
            py = y + math.sin(ang) * 12
            pygame.draw.circle(screen, (255, 200, 120), (int(px), int(py)), 5)
            pygame.draw.circle(screen, (120, 40, 30), (int(px), int(py)), 5, 1)
        # 中央产卵腔
        core_col = (255, 180, 80) if self.phase == 2 else (180, 80, 120)
        pygame.draw.circle(screen, core_col, (int(x), int(y)), 10)
        pygame.draw.circle(screen, (255, 240, 200), (int(x), int(y)), 4)


# ---------- BOSS 4：棱镜哨卫（光柱/横扫型）----------
class PrismSentinel(Boss):
    name = "棱镜哨卫"

    def __init__(self, x, y, hp, wave):
        super().__init__(x, y, hp, wave)
        self.bstate = "warn"        # warn -> fire -> idle -> warn
        self.btimer = 1.0
        self.fire_segs = []         # 当前/下一轮发射的段索引列表
        self._beam_dealt = False
        self.hit_w = 40
        self.hit_h = 40
        # 时长
        self.warn_t = 1.0
        self.fire_t = 0.5
        self.idle_t = 0.5
        self._compute_fire_segs()   # 初始计算

    def on_phase2(self):
        self.warn_t = 0.7
        self.fire_t = 0.6
        # 二阶段段数变化（5→7），若不在发射中则立即重算
        if self.bstate != "fire":
            self._compute_fire_segs()

    def _seg_count(self):
        return 5 if self.phase == 1 else 7

    def _compute_fire_segs(self):
        """随机选择段：一阶段 5 选 3，二阶段 7 选 5。"""
        n = self._seg_count()
        k = 3 if self.phase == 1 else 5
        self.fire_segs = sorted(random.sample(range(n), k))

    def _seg_range(self, idx):
        n = self._seg_count()
        total = BEAM_SEG_END - BEAM_SEG_START
        w = total / n
        a = BEAM_SEG_START + idx * w
        b = BEAM_SEG_START + (idx + 1) * w
        return (a, b)

    def update(self, dt, player):
        super().update(dt, player)
        self.btimer -= dt
        if self.bstate == "warn":
            if self.btimer <= 0:
                self.bstate = "fire"
                self.btimer = self.fire_t
                self._beam_dealt = False
        elif self.bstate == "fire":
            # 命中检测：仅在本轮首次判定（避免连杀）；无敌时免疫光柱
            if not self._beam_dealt:
                if not player.is_invincible():
                    for ux in player.unit_positions():
                        if any(self._in_seg(ux, s) for s in self.fire_segs):
                            player.kill_random_unit()
                            break
                self._beam_dealt = True
            if self.btimer <= 0:
                self.bstate = "idle"
                self.btimer = self.idle_t
                self._compute_fire_segs()   # 随机预选下一轮段
        else:  # idle
            if self.btimer <= 0:
                self.bstate = "warn"
                self.btimer = self.warn_t

    def _in_seg(self, ux, seg_idx):
        a, b = self._seg_range(seg_idx)
        return a <= ux <= b

    def draw(self, screen, t):
        x, y = self.x, self.y
        glow_col = (255, 240, 120) if self.phase == 2 else C_BOSS_GLOW
        gr = int(40 * (1 + 0.10 * math.sin(t * 5)))
        g = _glow(gr, glow_col)
        screen.blit(g, (int(x - gr), int(y - gr)),
                    special_flags=pygame.BLEND_ADD)
        # 棱柱主体（竖立三棱）
        h = 38
        pts = [(x - 16, y - h), (x + 16, y - h),
               (x + 22, y + h), (x - 22, y + h)]
        body = (255, 255, 255) if self.flash > 0 else C_BOSS_BODY
        pygame.draw.polygon(screen, body, pts)
        pygame.draw.polygon(screen, C_BOSS_EDGE, pts, 2)
        # 顶部宝石（二阶段为双宝石）
        gems = [(-7, 0), (7, 0)] if self.phase == 2 else [(0,)]
        for gx in gems:
            pygame.draw.circle(screen, C_BEAM_FIRE,
                               (int(x + gx[0]), int(y - h + 6)), 6)
            pygame.draw.circle(screen, (255, 255, 255),
                               (int(x + gx[0]), int(y - h + 6)), 2)
        # 光柱绘制：warn 显示即将发射段（红色半透明），fire 为亮黄光柱
        if self.bstate == "warn":
            for s in self.fire_segs:
                a, b = self._seg_range(s)
                bar = pygame.Surface((int(b - a), SCREEN_H), pygame.SRCALPHA)
                bar.fill((*C_BEAM_WARN, 60))
                screen.blit(bar, (int(a), 0))
        elif self.bstate == "fire":
            for s in self.fire_segs:
                a, b = self._seg_range(s)
                bar = pygame.Surface((int(b - a), SCREEN_H), pygame.SRCALPHA)
                bar.fill((*C_BEAM_FIRE, 120))
                screen.blit(bar, (int(a), 0))
                # 亮边
                pygame.draw.line(screen, (255, 255, 200), (a, 0), (a, SCREEN_H), 2)
                pygame.draw.line(screen, (255, 255, 200), (b, 0), (b, SCREEN_H), 2)


# ---------- BOSS 5：双生幻影（移动 + 综合型）----------
class TwinMirage(Boss):
    name = "双生幻影"

    def __init__(self, x, y, hp, wave):
        super().__init__(x, y, hp, wave)
        self.swing = 0.0
        self.alt = 0       # 0=左核先射, 1=右核先射
        self.alt_timer = 0.0
        self.conv_timer = 0.0
        self.ring_rot = 0.0
        self.summon_timer = 0.0
        self.combo_timer = 0.0
        self.hit_w = 44
        self.hit_h = 38

    def _core_positions(self):
        off = 90
        return (self.x + self.swing - off, self.y), (self.x + self.swing + off, self.y)

    def hit_test(self, bx, by):
        """一阶段命中判定：检查两个核心各自的命中框（非中间间隙）。"""
        if self.phase == 1:
            hw, hh = 22, 24   # 单核命中半宽/半高（核心钻石半宽 18 / 半高 22，略放宽）
            (lx, ly), (rx, ry) = self._core_positions()
            return ((abs(bx - lx) <= hw and abs(by - ly) <= hh) or
                    (abs(bx - rx) <= hw and abs(by - ry) <= hh))
        return abs(bx - self.x) <= self.hit_w and abs(by - self.y) <= self.hit_h

    def on_phase2(self):
        # 合体：清空子弹节奏，进入综合模式
        self.alt = 0
        self.combo_timer = 0.0

    def update(self, dt, player):
        super().update(dt, player)
        self.ring_rot += dt * 1.2
        if self.phase == 1:
            self.swing = math.sin(self.t * 0.8) * 40
            (lx, ly), (rx, ry) = self._core_positions()
            self.alt_timer += dt
            if self.alt_timer >= 1.1:
                self.alt_timer = 0.0
                if self.alt == 0:
                    self._fire_aimed(player, BOSS_BULLET_SPEED, ox=lx, oy=ly)
                else:
                    self._fire_aimed(player, BOSS_BULLET_SPEED, ox=rx, oy=ry)
                self.alt ^= 1
            self.conv_timer += dt
            if self.conv_timer >= 4.0:
                self.conv_timer = 0.0
                self._fire_aimed(player, BOSS_BULLET_FAST, ox=lx, oy=ly)
                self._fire_aimed(player, BOSS_BULLET_FAST, ox=rx, oy=ry)
        else:
            # 合体综合：环形 + 扇形交替 + 偶尔召唤
            self.combo_timer += dt
            if self.combo_timer >= 1.3:
                self.combo_timer = 0.0
                self._fire_ring(self.ring_rot, 8, 140, color=C_BOSS_BULLET2)
                self._fire_fan(player, 3, math.radians(20), BOSS_BULLET_SPEED)
            self.summon_timer += dt
            if self.summon_timer >= 3.0:
                self.summon_timer = 0.0
                mx = random.randint(DIVIDER_X + 30, SCREEN_W - 30)
                self.summons.append(Monster(mx, self.y + 30, 3))

    def draw(self, screen, t):
        x, y = self.x, self.y
        glow_col = (255, 120, 200) if self.phase == 2 else C_BOSS_GLOW
        if self.phase == 1:
            (lx, ly), (rx, ry) = self._core_positions()
            # 能量链
            chain = pygame.Surface((SCREEN_W, 2), pygame.SRCALPHA)
            pygame.draw.line(chain, (*C_BOSS_GLOW, 120), (0, 0), (SCREEN_W, 0), 2)
            screen.blit(chain, (int(lx), int(ly)))
            for cx, cy in ((lx, ly), (rx, ry)):
                gr = int(30 * (1 + 0.12 * math.sin(t * 5 + cx)))
                g = _glow(gr, glow_col)
                screen.blit(g, (int(cx - gr), int(cy - gr)),
                            special_flags=pygame.BLEND_ADD)
                pts = [(cx, cy - 22), (cx + 18, cy),
                       (cx, cy + 22), (cx - 18, cy)]
                body = (255, 255, 255) if self.flash > 0 else C_BOSS_BODY
                pygame.draw.polygon(screen, body, pts)
                pygame.draw.polygon(screen, C_BOSS_EDGE, pts, 2)
                pygame.draw.circle(screen, C_BOSS_EYE, (int(cx), int(cy)), 6)
        else:
            # 合体单核，更大
            gr = int(46 * (1 + 0.12 * math.sin(t * 5)))
            g = _glow(gr, glow_col)
            screen.blit(g, (int(x - gr), int(y - gr)),
                        special_flags=pygame.BLEND_ADD)
            pts = [(x, y - 30), (x + 24, y),
                   (x, y + 30), (x - 24, y)]
            body = (255, 255, 255) if self.flash > 0 else C_BOSS_BODY
            pygame.draw.polygon(screen, body, pts)
            pygame.draw.polygon(screen, C_BOSS_EDGE, pts, 2)
            # 双宝石
            for gx in (-8, 8):
                pygame.draw.circle(screen, C_BOSS_EYE, (int(x + gx), int(y)), 7)
                pygame.draw.circle(screen, (255, 255, 255), (int(x + gx), int(y)), 3)


# ---------- 工厂 ----------
_BOSS_CLASSES = [None, RiftEye, VortexCore, HiveMatriarch,
                 PrismSentinel, TwinMirage]


def make_boss(wave):
    """根据波数生成对应 BOSS（血量 = BOSS_HP_MULT × 该波怪物血量）。"""
    hp = BOSS_HP_MULT * monster_hp(wave)
    cls = _BOSS_CLASSES[wave]
    return cls(SCREEN_W // 2, BOSS_Y, hp, wave)
