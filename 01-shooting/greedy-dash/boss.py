# -*- coding: utf-8 -*-
"""
BOSS 系统：11 关 11 个 BOSS。
- 阶段：简单/普通=2阶段(50%触发)；困难/噩梦=3阶段(70%/40%触发)。
- 第 11 关「终焉之主」仅噩梦模式出现，护盾卫星存在时本体免伤且缓慢回血。
- 顺序按机制难度从简到难。
"""
import math
import random

import pygame

from settings import *
import settings as S
from player import _glow
from enemy import Monster
from ui import get_font


# ---------- 横扫激光（棱镜哨卫三阶段 / 终焉之主二阶段共用）----------
class SweepBeam:
    """一道垂直光柱从一侧扫向另一侧，亮 SWEEP_BEAM_ON / 熄 SWEEP_BEAM_OFF 交替。"""
    def __init__(self):
        self.active = False
        self.x = 0.0
        self.dir = 1
        self.timer = 0.0
        self.on = False
        self.dealt = False       # 当前亮期是否已命中

    def start(self, from_left=True):
        self.active = True
        self.x = 30.0 if from_left else float(SCREEN_W - 30)
        self.dir = 1 if from_left else -1
        self.timer = SWEEP_BEAM_ON
        self.on = True
        self.dealt = False

    def update(self, dt, player):
        if not self.active:
            return
        self.x += self.dir * SWEEP_BEAM_SPEED * dt
        self.timer -= dt
        if self.timer <= 0:
            self.on = not self.on
            self.timer = SWEEP_BEAM_ON if self.on else SWEEP_BEAM_OFF
            self.dealt = False
        if self.on and not self.dealt:
            if not player.is_invincible():
                for ux in player.unit_positions():
                    if abs(ux - self.x) <= SWEEP_BEAM_WIDTH / 2:
                        player.kill_random_unit()
                        self.dealt = True
                        break
        if self.x < -20 or self.x > SCREEN_W + 20:
            self.active = False

    _bar_cache = None

    @classmethod
    def _get_bar(cls, on):
        # 缓存光柱贴图：避免横扫激光每帧创建整屏 Surface（手机 GC 抖动主因）
        if cls._bar_cache is None:
            cls._bar_cache = {}
        s = cls._bar_cache.get(on)
        if s is None:
            col = (*C_BEAM_FIRE, 130) if on else (*C_BEAM_WARN, 35)
            s = pygame.Surface((SWEEP_BEAM_WIDTH, S.SCREEN_H), pygame.SRCALPHA)
            s.fill(col)
            cls._bar_cache[on] = s
        return s

    def draw(self, screen):
        if not self.active:
            return
        screen.blit(self._get_bar(self.on),
                    (int(self.x - SWEEP_BEAM_WIDTH / 2), 0))
        if self.on:
            pygame.draw.line(screen, (255, 255, 200), (self.x, 0),
                             (self.x, S.SCREEN_H), 2)


# ---------- BOSS 子弹 ----------
class BossBullet:
    """BOSS 发射的敌方子弹，支持追踪 / 反弹。"""
    def __init__(self, x, y, vx, vy, color=None, radius=5,
                 tracking=False, turn_speed=0.0, bounce=False, life=None):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color or C_BOSS_BULLET
        self.radius = radius
        self.dead = False
        self.tracking = tracking
        self.turn_speed = turn_speed
        self.bounce = bounce
        self.life = life               # 生命周期（秒），None=无限（靠 off）

    def update(self, dt, player=None):
        if self.tracking and player is not None and self.turn_speed > 0:
            dx = player.x - self.x
            dy = player.y - self.y
            target = math.atan2(dy, dx)
            cur = math.atan2(self.vy, self.vx)
            diff = (target - cur + math.pi) % math.tau - math.pi
            turn = max(-self.turn_speed * dt, min(self.turn_speed * dt, diff))
            new_ang = cur + turn
            spd = math.hypot(self.vx, self.vy)
            self.vx = math.cos(new_ang) * spd
            self.vy = math.sin(new_ang) * spd
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.bounce:
            if self.x < self.radius:
                self.x = self.radius
                self.vx = -self.vx
            elif self.x > SCREEN_W - self.radius:
                self.x = SCREEN_W - self.radius
                self.vx = -self.vx
        if self.life is not None:
            self.life -= dt
            if self.life <= 0:
                self.dead = True

    def off(self):
        return (self.y > S.SCREEN_H + 20 or self.y < -30
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
        self._p3 = False
        self.intro = False        # 出场展示中（暂停）
        self.hit_w = 44           # 命中半宽
        self.hit_h = 36           # 命中半高
        self.bullets = []         # 待移交主循环的子弹
        self.summons = []         # 待移交主循环的小怪

    # ---- 战斗 ----
    def hit(self, dmg):
        self.hp -= dmg
        self.flash = 0.08
        ratio = self.hp / self.max_hp
        if S.BOSS_PHASES >= 3:
            if not self._p2 and ratio <= PHASE2_THRESHOLD_3P:
                self._p2 = True
                self.phase = 2
                self.on_phase2()
            if not self._p3 and ratio <= PHASE3_THRESHOLD:
                self._p3 = True
                self.phase = 3
                self.on_phase3()
        else:
            if not self._p2 and ratio <= PHASE2_THRESHOLD_2P:
                self._p2 = True
                self.phase = 2
                self.on_phase2()
        if self.hp <= 0:
            self.hp = 0
            self.dead = True

    def on_phase2(self):
        """子类覆盖：二阶段数值/外观调整。"""
        pass

    def on_phase3(self):
        """子类覆盖：三阶段数值/外观调整（仅困难/噩梦）。"""
        pass

    def hit_test(self, bx, by):
        return abs(bx - self.x) <= self.hit_w and abs(by - self.y) <= self.hit_h

    def has_shield(self):
        """是否有护盾（终焉之主卫星）。默认无。"""
        return False

    def hit_satellite(self, bx, by, dmg):
        """命中护盾卫星，返回是否命中。默认无卫星。"""
        return False

    # ---- 共用发射辅助 ----
    def _fire_aimed(self, player, speed, color=None, ox=None, oy=None):
        fx = ox if ox is not None else self.x
        fy = oy if oy is not None else self.y + 12
        dx = player.x - fx
        dy = player.y - fy
        d = math.hypot(dx, dy) or 1.0
        self.bullets.append(BossBullet(fx, fy, dx / d * speed, dy / d * speed,
                                       color=color))

    def _fire_fan(self, player, n, spread, speed, color=None, ox=None, oy=None):
        fx = ox if ox is not None else self.x
        fy = oy if oy is not None else self.y + 12
        dx = player.x - fx
        dy = player.y - fy
        base = math.atan2(dy, dx)
        for i in range(n):
            off = 0 if n == 1 else (i - (n - 1) / 2.0) * spread
            a = base + off
            self.bullets.append(BossBullet(fx, fy,
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

    def _fire_tracking(self, player, n, speed, color=None):
        """发射 n 枚追踪导弹，横向分散发射位置。"""
        for i in range(n):
            ox = (i - (n - 1) / 2.0) * 26   # 横向分散 26px 间距
            ang = math.pi / 2 + (i - (n - 1) / 2.0) * math.radians(15)
            self.bullets.append(BossBullet(
                self.x + ox, self.y + 12,
                math.cos(ang) * speed, math.sin(ang) * speed,
                color=color or C_BOSS_BULLET, radius=6,
                tracking=True, turn_speed=TRACKING_TURN_SPEED, life=8.0))

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
        if self.phase == 1:
            col = C_BOSS_HP
        elif self.phase == 2:
            col = (255, 150, 70)
        else:
            col = (255, 90, 90)
        pygame.draw.rect(screen, col, (bx, by, int(w * ratio), 12),
                         border_radius=4)
        pygame.draw.rect(screen, C_BOSS_EDGE, (bx, by, w, 12), 1,
                         border_radius=4)
        font = get_font(14, bold=True)
        label = "%s  ·  阶段 %d" % (self.name, self.phase)
        s = font.render(label, True, C_TEXT)
        screen.blit(s, (bx + 4, by - 2))


# ======================================================================
# 第 1 关：裂隙之眼（扇形散射 / 瞄准）
# ======================================================================
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

    def on_phase3(self):
        self.interval = 0.9
        self.fan = 8
        self.spread = math.radians(22)

    def update(self, dt, player):
        super().update(dt, player)
        dx = player.x - self.x
        dy = player.y - self.y
        d = math.hypot(dx, dy) or 1.0
        self._last_aim = (dx / d, dy / d)
        self.fire_timer += dt
        if self.fire_timer >= self.interval:
            self.fire_timer = 0.0
            if self.phase == 3:
                # 8 发全向散射 + 连续 3 发预测直瞄
                self._fire_ring(self.t * 2, 8, self.speed, color=C_BOSS_BULLET2)
                for _ in range(3):
                    self._fire_aimed(player, BOSS_BULLET_FAST)
            else:
                self._fire_fan(player, self.fan, self.spread, self.speed)
                if self.phase == 2:
                    self._fire_aimed(player, BOSS_BULLET_FAST)

    def draw(self, screen, t):
        x, y = self.x, self.y
        charging = self.fire_timer > self.interval - self.charge
        if self.phase == 3:
            glow_col, iris = (255, 60, 60), (255, 50, 50)
            n_spikes = 12
        elif self.phase == 2:
            glow_col, iris = (255, 80, 80), (255, 70, 70)
            n_spikes = 10
        else:
            glow_col, iris = C_BOSS_GLOW, (180, 60, 160)
            n_spikes = 6
        amp = 0.28 if charging else 0.10
        gr = int(40 * (1 + amp * math.sin(t * 6)))
        g = _glow(gr, glow_col)
        screen.blit(g, (int(x - gr), int(y - gr)),
                    special_flags=pygame.BLEND_ADD)
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
        # 三阶段多瞳孔
        if self.phase == 3:
            for ang in (0, math.tau / 3, math.tau * 2 / 3):
                px = x + math.cos(ang + t) * 26
                py = y + math.sin(ang + t) * 26
                pygame.draw.circle(screen, (255, 60, 60), (int(px), int(py)), 5)
                pygame.draw.circle(screen, (20, 0, 0), (int(px), int(py)), 2)
        if charging:
            cg = _glow(14, (255, 240, 150))
            screen.blit(cg, (int(x - 14), int(y - 14)),
                        special_flags=pygame.BLEND_ADD)


# ======================================================================
# 第 2 关：漩涡核心（环形弹幕）—— 修复双环反向交叉
# ======================================================================
class VortexCore(Boss):
    name = "漩涡核心"

    def __init__(self, x, y, hp, wave):
        super().__init__(x, y, hp, wave)
        self.rot = 0.0
        self.interval = 1.4
        self.aim_timer = 0.0
        self.hit_w = 40
        self.hit_h = 36
        # 三阶段螺旋喷流计时
        self.spiral_timer = 0.0
        self.spiral_ang = 0.0

    def on_phase2(self):
        self.interval = 1.3

    def on_phase3(self):
        self.interval = 1.1

    def update(self, dt, player):
        super().update(dt, player)
        self.rot += dt * (1.6 if self.phase == 3 else 1.2 if self.phase == 2 else 0.8)
        self.fire_timer += dt
        if self.fire_timer >= self.interval:
            self.fire_timer = 0.0
            if self.phase == 1:
                self._fire_ring(self.rot, 12, 150, color=C_BOSS_BULLET2)
            elif self.phase == 2:
                # 修复：两环速度不同（径向分离）+ 反向角度，真正反向交叉
                self._fire_ring(self.rot, 12, 150, color=C_BOSS_BULLET2)
                self._fire_ring(-self.rot, 12, 200, color=C_BOSS_BULLET)
            else:
                # 三阶段：三环 120° 相位差不同速度反向旋转
                self._fire_ring(self.rot, 12, 140, color=C_BOSS_BULLET2)
                self._fire_ring(-self.rot + math.tau / 3, 12, 180, color=C_BOSS_BULLET)
                self._fire_ring(self.rot * 1.3 + math.tau * 2 / 3, 12, 220,
                                color=(200, 120, 255))
        if self.phase >= 2:
            self.aim_timer += dt
            if self.aim_timer >= 3.0:
                self.aim_timer = 0.0
                self._fire_aimed(player, BOSS_BULLET_FAST)
        if self.phase == 3:
            # 持续螺旋喷流
            self.spiral_timer += dt
            if self.spiral_timer >= 0.18:
                self.spiral_timer = 0.0
                self.spiral_ang += 0.34
                self.bullets.append(BossBullet(
                    self.x, self.y, math.cos(self.spiral_ang) * 170,
                    math.sin(self.spiral_ang) * 170, color=(200, 120, 255),
                    radius=4))

    def draw(self, screen, t):
        x, y = self.x, self.y
        if self.phase == 3:
            glow_col = (160, 120, 255)
        elif self.phase == 2:
            glow_col = (120, 180, 255)
        else:
            glow_col = C_BOSS_GLOW
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
        if self.phase == 3:
            # 三层嵌套反向环
            for k, (rr, rot_dir) in enumerate([(12, -1), (8, 1), (5, -1.3)]):
                pts2 = [(x + math.cos(i / 10 * math.tau + self.rot * rot_dir
                                     + k) * rr,
                         y + math.sin(i / 10 * math.tau + self.rot * rot_dir
                                      + k) * rr) for i in range(10)]
                pygame.draw.polygon(screen, (160, 120, 255), pts2, 1)
        elif self.phase == 2:
            pts2 = [(x + math.cos(i / 12 * math.tau - self.rot) * 12,
                     y + math.sin(i / 12 * math.tau - self.rot) * 12)
                    for i in range(12)]
            pygame.draw.polygon(screen, (120, 200, 255), pts2)
        else:
            pygame.draw.circle(screen, C_BOSS_EYE, (int(x), int(y)), 8)


# ======================================================================
# 第 3 关：虫巢母体（召唤）
# ======================================================================
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

    def on_phase3(self):
        self.interval = 1.0

    def update(self, dt, player):
        super().update(dt, player)
        self.fire_timer += dt
        if self.fire_timer >= self.interval:
            self.fire_timer = 0.0
            if self.phase == 3:
                count = random.randint(3, 4)
                # 召唤物加速（更高初始 y 速度通过 hp 标记无法做，改用更多数量）
            elif self.phase == 2:
                count = random.randint(2, 3)
            else:
                count = random.randint(1, 2)
            for _ in range(count):
                mx = random.randint(DIVIDER_X + 30, SCREEN_W - 30)
                self.summons.append(Monster(mx, self.y + 30, 3))
            if self.phase == 2:
                self._fire_fan(player, 3, math.radians(15), BOSS_BULLET_SPEED,
                               color=C_BOSS_BULLET2)
            elif self.phase == 3:
                self._fire_ring(self.t, 10, 150, color=C_BOSS_BULLET)
        if self.phase == 1:
            self.aim_timer += dt
            if self.aim_timer >= 3.0:
                self.aim_timer = 0.0
                self._fire_aimed(player, BOSS_BULLET_SPEED)

    def draw(self, screen, t):
        x, y = self.x, self.y
        glow_col = (255, 100, 60) if self.phase == 3 else (
            (255, 120, 80) if self.phase == 2 else C_BOSS_GLOW)
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
        pores = 6 if self.phase == 3 else (5 if self.phase == 2 else 3)
        for i in range(pores):
            ang = i / pores * math.tau + t * 0.1
            px = x + math.cos(ang) * 16
            py = y + math.sin(ang) * 12
            pygame.draw.circle(screen, (255, 200, 120), (int(px), int(py)), 5)
            pygame.draw.circle(screen, (120, 40, 30), (int(px), int(py)), 5, 1)
        core_col = (255, 160, 60) if self.phase == 3 else (
            (255, 180, 80) if self.phase == 2 else (180, 80, 120))
        pygame.draw.circle(screen, core_col, (int(x), int(y)), 10)
        pygame.draw.circle(screen, (255, 240, 200), (int(x), int(y)), 4)


# ======================================================================
# 第 4 关：螺旋深渊（螺旋弹幕）
# ======================================================================
class SpiralAbyss(Boss):
    name = "螺旋深渊"

    def __init__(self, x, y, hp, wave):
        super().__init__(x, y, hp, wave)
        self.arms = 2
        self.interval = 0.25
        self.spiral_ang = 0.0
        self.aim_timer = 0.0
        self.ring_timer = 0.0
        self.hit_w = 40
        self.hit_h = 38

    def on_phase2(self):
        self.arms = 4
        self.interval = 0.22

    def on_phase3(self):
        self.arms = 6
        self.interval = 0.18

    def update(self, dt, player):
        super().update(dt, player)
        self.fire_timer += dt
        if self.fire_timer >= self.interval:
            self.fire_timer = 0.0
            self.spiral_ang += 0.32
            for i in range(self.arms):
                a = self.spiral_ang + i / self.arms * math.tau
                self.bullets.append(BossBullet(
                    self.x, self.y, math.cos(a) * 170, math.sin(a) * 170,
                    color=C_BOSS_BULLET2 if i % 2 == 0 else C_BOSS_BULLET,
                    radius=4))
        if self.phase >= 2:
            self.aim_timer += dt
            if self.aim_timer >= 2.2:
                self.aim_timer = 0.0
                self._fire_aimed(player, BOSS_BULLET_FAST)
        if self.phase == 3:
            # 反向收束弹幕：周期发射快速全向环
            self.ring_timer += dt
            if self.ring_timer >= 2.5:
                self.ring_timer = 0.0
                self._fire_ring(-self.spiral_ang, 10, 240,
                                color=(180, 120, 255))

    def draw(self, screen, t):
        x, y = self.x, self.y
        glow_col = (120, 200, 255) if self.phase == 3 else (
            (140, 180, 255) if self.phase == 2 else C_BOSS_GLOW)
        gr = int(42 * (1 + 0.10 * math.sin(t * 4)))
        g = _glow(gr, glow_col)
        screen.blit(g, (int(x - gr), int(y - gr)),
                    special_flags=pygame.BLEND_ADD)
        # 螺旋臂
        for arm in range(self.arms):
            base = arm / self.arms * math.tau + t * 1.5
            pts = []
            for k in range(8):
                rr = 8 + k * 4
                ang = base + k * 0.4
                pts.append((x + math.cos(ang) * rr, y + math.sin(ang) * rr))
            if len(pts) >= 2:
                pygame.draw.lines(screen, glow_col, False, pts, 3)
        body = (255, 255, 255) if self.flash > 0 else C_BOSS_BODY
        pygame.draw.circle(screen, body, (int(x), int(y)), 18)
        pygame.draw.circle(screen, C_BOSS_EDGE, (int(x), int(y)), 18, 2)
        pygame.draw.circle(screen, C_BOSS_EYE, (int(x), int(y)), 8)


# ======================================================================
# 第 5 关：棱镜哨卫（光柱 / 横扫激光）
# ======================================================================
class PrismSentinel(Boss):
    name = "棱镜哨卫"

    def __init__(self, x, y, hp, wave):
        super().__init__(x, y, hp, wave)
        self.bstate = "warn"        # warn -> fire -> idle -> warn
        self.btimer = 1.0
        self.fire_segs = []
        self._beam_dealt = False
        self.hit_w = 40
        self.hit_h = 40
        self.warn_t = 1.0
        self.fire_t = 0.5
        self.idle_t = 0.5
        self.phase_cd = 0.0          # 转阶段冷却：期间不发起攻击，但保留已有攻击
        self._compute_fire_segs()
        # 三阶段横扫激光
        self.sweep = SweepBeam()
        self.sweep_timer = 0.0
        self.use_sweep = False

    def on_phase2(self):
        self.warn_t = 0.7
        self.fire_t = 0.6
        self.phase_cd = 0.5          # 转阶段 0.5s 内不发起攻击
        self._compute_fire_segs()
        # 转阶段强制回到预警起始：先显示新段位置，phase_cd 阻止立即 fire，
        # 避免用新位置瞬间打中玩家（v3.1.0 修复）
        self.bstate = "warn"
        self._beam_dealt = False
        self.btimer = self.warn_t

    def on_phase3(self):
        self.warn_t = 0.6
        self.fire_t = 0.55
        self.idle_t = 0.4
        self.use_sweep = True
        self.phase_cd = 0.5
        self._compute_fire_segs()
        # 转阶段强制回到预警起始：先显示新段位置，phase_cd 阻止立即 fire，
        # 避免用新位置瞬间打中玩家（v3.1.0 修复）
        self.bstate = "warn"
        self._beam_dealt = False
        self.btimer = self.warn_t

    _beam_cache = None

    @classmethod
    def _beam_strip(cls, on, n):
        # 缓存落点光柱贴图（按 预警/开火 × 段数），避免每帧建 3~7 个整屏 Surface
        if cls._beam_cache is None:
            cls._beam_cache = {}
        key = (on, n)
        s = cls._beam_cache.get(key)
        if s is None:
            total = BEAM_SEG_END - BEAM_SEG_START
            w = max(1, int(total / n))
            col = (*C_BEAM_FIRE, 120) if on else (*C_BEAM_WARN, 60)
            s = pygame.Surface((w, S.SCREEN_H), pygame.SRCALPHA)
            s.fill(col)
            cls._beam_cache[key] = s
        return s

    def _seg_count(self):
        return 5 if self.phase == 1 else 7

    def _compute_fire_segs(self):
        """随机选择段：一阶段 5 选 3，二/三阶段 7 选 5。"""
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
        self.sweep.update(dt, player)
        if self.phase_cd > 0:
            self.phase_cd -= dt
        self.btimer -= dt
        if self.bstate == "warn":
            if self.btimer <= 0:
                if self.phase_cd > 0:
                    # 转阶段冷却中，不发起攻击，继续预警等待
                    self.btimer = 0.15
                else:
                    self.bstate = "fire"
                    self.btimer = self.fire_t
                    self._beam_dealt = False
        elif self.bstate == "fire":
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
                self._compute_fire_segs()
                # 三阶段：idle 结束后启动横扫激光（错时，不与光柱同时）
                if self.phase == 3 and not self.sweep.active:
                    self.sweep.start(from_left=random.random() < 0.5)
        else:  # idle
            if self.btimer <= 0:
                self.bstate = "warn"
                self.btimer = self.warn_t

    def _in_seg(self, ux, seg_idx):
        a, b = self._seg_range(seg_idx)
        return a <= ux <= b

    def draw(self, screen, t):
        x, y = self.x, self.y
        glow_col = (255, 240, 120) if self.phase == 3 else (
            (255, 240, 120) if self.phase == 2 else C_BOSS_GLOW)
        gr = int(40 * (1 + 0.10 * math.sin(t * 5)))
        g = _glow(gr, glow_col)
        screen.blit(g, (int(x - gr), int(y - gr)),
                    special_flags=pygame.BLEND_ADD)
        h = 38
        pts = [(x - 16, y - h), (x + 16, y - h),
               (x + 22, y + h), (x - 22, y + h)]
        body = (255, 255, 255) if self.flash > 0 else C_BOSS_BODY
        pygame.draw.polygon(screen, body, pts)
        pygame.draw.polygon(screen, C_BOSS_EDGE, pts, 2)
        # 顶部宝石（三阶段三宝石，二阶段双宝石）
        if self.phase == 3:
            gems = [-10, 0, 10]
            gem_col = (255, 120, 120)
        elif self.phase == 2:
            gems = [-7, 7]
            gem_col = C_BEAM_FIRE
        else:
            gems = [0]
            gem_col = C_BEAM_FIRE
        for gx in gems:
            pygame.draw.circle(screen, gem_col,
                               (int(x + gx), int(y - h + 6)), 6)
            pygame.draw.circle(screen, (255, 255, 255),
                               (int(x + gx), int(y - h + 6)), 2)
        # 光柱（复用缓存贴图，杜绝每帧整屏 Surface 分配）
        if self.bstate in ("warn", "fire"):
            on = (self.bstate == "fire")
            strip = PrismSentinel._beam_strip(on, self._seg_count())
            for s in self.fire_segs:
                a, b = self._seg_range(s)
                screen.blit(strip, (int(a), 0))
                if on:
                    pygame.draw.line(screen, (255, 255, 200), (a, 0), (a, S.SCREEN_H), 2)
                    pygame.draw.line(screen, (255, 255, 200), (b, 0), (b, S.SCREEN_H), 2)
        # 横扫激光
        self.sweep.draw(screen)


# ======================================================================
# 第 6 关：回音壁垒（反弹弹幕）
# ======================================================================
class EchoBastion(Boss):
    name = "回音壁垒"

    def __init__(self, x, y, hp, wave):
        super().__init__(x, y, hp, wave)
        self.interval = 1.5
        self.ring_timer = 0.0
        self.hit_w = 42
        self.hit_h = 38

    def on_phase2(self):
        self.interval = 1.1

    def on_phase3(self):
        self.interval = 0.85

    def update(self, dt, player):
        super().update(dt, player)
        self.fire_timer += dt
        if self.fire_timer >= self.interval:
            self.fire_timer = 0.0
            if self.phase == 1:
                # 3 发反弹弹
                for i in range(3):
                    a = math.pi / 2 + (i - 1) * math.radians(25)
                    self.bullets.append(BossBullet(
                        self.x, self.y + 10, math.cos(a) * 160,
                        math.sin(a) * 160, color=C_BOSS_BULLET2, radius=6,
                        bounce=True, life=7.0))
            elif self.phase == 2:
                for i in range(5):
                    a = math.pi / 2 + (i - 2) * math.radians(22)
                    self.bullets.append(BossBullet(
                        self.x, self.y + 10, math.cos(a) * 170,
                        math.sin(a) * 170, color=C_BOSS_BULLET, radius=6,
                        bounce=True, life=7.0))
                self._fire_aimed(player, BOSS_BULLET_SPEED)
            else:
                # 多向反弹弹（向下扇形，确保都向下飞不会中途消失）+ 声波环形
                for i in range(6):
                    a = math.pi / 2 + (i - 2.5) * math.radians(20)
                    self.bullets.append(BossBullet(
                        self.x, self.y + 10, math.cos(a) * 180,
                        math.sin(a) * 180, color=C_BOSS_BULLET2, radius=6,
                        bounce=True, life=8.0))
                self._fire_ring(self.t, 8, 150, color=C_BOSS_BULLET)

    def draw(self, screen, t):
        x, y = self.x, self.y
        glow_col = (120, 220, 255) if self.phase == 3 else (
            (140, 200, 255) if self.phase == 2 else C_BOSS_GLOW)
        gr = int(40 * (1 + 0.10 * math.sin(t * 4)))
        g = _glow(gr, glow_col)
        screen.blit(g, (int(x - gr), int(y - gr)),
                    special_flags=pygame.BLEND_ADD)
        # 多层晶体壁垒
        layers = 3 if self.phase == 3 else (2 if self.phase == 2 else 1)
        for layer in range(layers):
            n = 6
            rot = t * (0.6 - layer * 0.2) + layer * 0.5
            pts = []
            for i in range(n * 2):
                ang = i / (n * 2) * math.tau + rot
                r = 30 - layer * 8 if i % 2 == 0 else 18 - layer * 5
                pts.append((x + math.cos(ang) * r, y + math.sin(ang) * r))
            body = (255, 255, 255) if self.flash > 0 else (
                (90, 30, 80) if layer == 0 else (60, 80, 120))
            pygame.draw.polygon(screen, body, pts, 0 if layer == 0 else 2)
        pygame.draw.circle(screen, C_BOSS_EYE, (int(x), int(y)), 7)


# ======================================================================
# 第 7 关：天罚核心（落点轰炸）
# ======================================================================
class JudgementCore(Boss):
    name = "天罚核心"

    def __init__(self, x, y, hp, wave):
        super().__init__(x, y, hp, wave)
        self.interval = 2.0
        self.markers = []   # [{x,y,timer,exploded}]
        self.hit_w = 40
        self.hit_h = 38
        self.phase_cd = 0.0          # 转阶段冷却：期间不发射新圈，已有圈保留

    def on_phase2(self):
        self.interval = 1.5
        self.phase_cd = 0.5

    def on_phase3(self):
        self.interval = 1.1
        self.phase_cd = 0.5

    def _add_marker(self, x, warn_time):
        """在 x 处生成一个爆炸圈，warn_time 秒后爆炸。"""
        self.markers.append({"x": x, "y": S.SCREEN_H - S.PLAYER_BOTTOM_GAP,
                             "timer": warn_time, "warn": warn_time,
                             "exploded": False, "explode_t": 0.0})

    def update(self, dt, player):
        super().update(dt, player)
        if self.phase_cd > 0:
            self.phase_cd -= dt
        self.fire_timer += dt
        if self.fire_timer >= self.interval and self.phase_cd <= 0:
            self.fire_timer = 0.0
            if self.phase == 1:
                # 玩家位置 1 个，1.2s 预警
                self._add_marker(player.x, 1.2)
            elif self.phase == 2:
                # 玩家位置 1 个 + 随机横轴 1 个，0.8s 预警
                self._add_marker(player.x, 0.8)
                self._add_marker(random.randint(60, SCREEN_W - 60), 0.8)
            else:
                # 玩家位置 1 个 + 随机横轴 2 个，0.5s 预警
                self._add_marker(player.x, 0.5)
                for _ in range(2):
                    self._add_marker(random.randint(60, SCREEN_W - 60), 0.5)
        # 更新标记
        for m in self.markers:
            if m["exploded"]:
                m["explode_t"] += dt
                continue
            m["timer"] -= dt
            if m["timer"] <= 0:
                m["exploded"] = True
                # 爆炸命中判定
                if not player.is_invincible():
                    for ux in player.unit_positions():
                        if math.hypot(ux - m["x"],
                                      (S.SCREEN_H - S.PLAYER_BOTTOM_GAP) - m["y"]) <= BOMB_RADIUS:
                            player.kill_random_unit()
                            break
        # 爆炸后 BOMB_LINGER 秒清除
        self.markers = [m for m in self.markers
                        if not (m["exploded"] and m["explode_t"] >= BOMB_LINGER)]

    def draw(self, screen, t):
        x, y = self.x, self.y
        glow_col = (255, 240, 180) if self.phase == 3 else (
            (255, 220, 120) if self.phase == 2 else C_BOSS_GLOW)
        gr = int(40 * (1 + 0.12 * math.sin(t * 5)))
        g = _glow(gr, glow_col)
        screen.blit(g, (int(x - gr), int(y - gr)),
                    special_flags=pygame.BLEND_ADD)
        # 雷霆核心（多角星）
        n = 8
        pts = []
        for i in range(n * 2):
            ang = i / (n * 2) * math.tau + t * 0.4
            r = 32 if i % 2 == 0 else 16
            pts.append((x + math.cos(ang) * r, y + math.sin(ang) * r))
        body = (255, 255, 255) if self.flash > 0 else C_BOSS_BODY
        pygame.draw.polygon(screen, body, pts)
        pygame.draw.polygon(screen, C_BOSS_EDGE, pts, 2)
        pygame.draw.circle(screen, (255, 240, 150), (int(x), int(y)), 10)
        pygame.draw.circle(screen, (255, 255, 255), (int(x), int(y)), 4)
        # 落点标记
        for m in self.markers:
            if m["exploded"]:
                # 爆炸扩散圈
                prog = min(1.0, m["explode_t"] / BOMB_LINGER)
                r = int(BOMB_RADIUS * (0.6 + 0.4 * prog))
                pygame.draw.circle(screen, (255, 200, 100),
                                   (int(m["x"]), int(m["y"])), r, 3)
            else:
                prog = 1 - m["timer"] / m["warn"]
                r = int(BOMB_RADIUS * (1 - prog * 0.6))
                pygame.draw.circle(screen, (255, 80, 80),
                                   (int(m["x"]), int(m["y"])), r, 2)
                pygame.draw.circle(screen, (255, 240, 120),
                                   (int(m["x"]), int(m["y"])),
                                   max(2, r - 6), 1)


# ======================================================================
# 第 8 关：追猎之眼（追踪导弹）
# ======================================================================
class HunterEye(Boss):
    name = "追猎之眼"

    def __init__(self, x, y, hp, wave):
        super().__init__(x, y, hp, wave)
        self.interval = 2.2
        self.ring_timer = 0.0
        self.aim_timer = 0.0
        self._last_aim = (0.0, 1.0)
        self.hit_w = 40
        self.hit_h = 36

    def on_phase2(self):
        self.interval = 1.8

    def on_phase3(self):
        self.interval = 1.3

    def update(self, dt, player):
        super().update(dt, player)
        dx = player.x - self.x
        dy = player.y - self.y
        d = math.hypot(dx, dy) or 1.0
        self._last_aim = (dx / d, dy / d)
        self.fire_timer += dt
        if self.fire_timer >= self.interval:
            self.fire_timer = 0.0
            if self.phase == 1:
                self._fire_tracking(player, 3, 130)
            elif self.phase == 2:
                self._fire_tracking(player, 5, 140)
                self._fire_ring(self.t, 8, 140, color=C_BOSS_BULLET2)
            else:
                self._fire_tracking(player, 4, 150, color=(255, 120, 120))
                # 周期全向瞄准
                for i in range(8):
                    a = i / 8 * math.tau
                    self.bullets.append(BossBullet(
                        self.x, self.y, math.cos(a) * 180,
                        math.sin(a) * 180, color=C_BOSS_BULLET2, radius=4))
        if self.phase == 3:
            self.aim_timer += dt
            if self.aim_timer >= 1.5:
                self.aim_timer = 0.0
                self._fire_aimed(player, BOSS_BULLET_FAST)

    def draw(self, screen, t):
        x, y = self.x, self.y
        glow_col = (255, 120, 60) if self.phase == 3 else (
            (255, 150, 80) if self.phase == 2 else C_BOSS_GLOW)
        gr = int(40 * (1 + 0.12 * math.sin(t * 5)))
        g = _glow(gr, glow_col)
        screen.blit(g, (int(x - gr), int(y - gr)),
                    special_flags=pygame.BLEND_ADD)
        # 多瞳追猎眼
        n_spikes = 10
        pts = []
        for i in range(n_spikes * 2):
            ang = i / (n_spikes * 2) * math.tau + t * 0.3
            r = 32 if i % 2 == 0 else 16
            pts.append((x + math.cos(ang) * r, y + math.sin(ang) * r))
        body = (255, 255, 255) if self.flash > 0 else C_BOSS_BODY
        pygame.draw.polygon(screen, body, pts)
        pygame.draw.polygon(screen, C_BOSS_EDGE, pts, 2)
        pygame.draw.circle(screen, (240, 230, 210), (int(x), int(y)), 18)
        pygame.draw.circle(screen, (255, 100, 60), (int(x), int(y)), 11)
        ax, ay = self._last_aim
        pygame.draw.circle(screen, (20, 0, 0),
                           (int(x + ax * 5), int(y + ay * 5)), 6)
        # 三阶段多瞳
        if self.phase == 3:
            for ang in (math.tau / 3, math.tau * 2 / 3):
                px = x + math.cos(ang + t * 0.8) * 22
                py = y + math.sin(ang + t * 0.8) * 22
                pygame.draw.circle(screen, (255, 100, 60), (int(px), int(py)), 4)


# ======================================================================
# 第 9 关：双生幻影（移动 + 综合）
# ======================================================================
class TwinMirage(Boss):
    name = "双生幻影"

    def __init__(self, x, y, hp, wave):
        super().__init__(x, y, hp, wave)
        self.swing = 0.0
        self.alt = 0
        self.alt_timer = 0.0
        self.conv_timer = 0.0
        self.ring_rot = 0.0
        self.summon_timer = 0.0
        self.combo_timer = 0.0
        # 三阶段四核
        self.quad_rot = 0.0
        self.quad_timer = 0.0
        self.merge_timer = 0.0
        self.hit_w = 44
        self.hit_h = 38

    def _core_positions(self):
        off = 90
        return (self.x + self.swing - off, self.y), (self.x + self.swing + off, self.y)

    def _quad_positions(self):
        """三阶段四核位置（环绕）。"""
        pts = []
        for i in range(4):
            a = self.quad_rot + i / 4 * math.tau
            pts.append((self.x + math.cos(a) * 60, self.y + math.sin(a) * 30))
        return pts

    def hit_test(self, bx, by):
        if self.phase == 1:
            hw, hh = 22, 24
            (lx, ly), (rx, ry) = self._core_positions()
            return ((abs(bx - lx) <= hw and abs(by - ly) <= hh) or
                    (abs(bx - rx) <= hw and abs(by - ry) <= hh))
        elif self.phase == 3:
            hw, hh = 18, 20
            return any(abs(bx - cx) <= hw and abs(by - cy) <= hh
                       for cx, cy in self._quad_positions())
        return abs(bx - self.x) <= self.hit_w and abs(by - self.y) <= self.hit_h

    def on_phase2(self):
        self.alt = 0
        self.combo_timer = 0.0

    def on_phase3(self):
        self.quad_rot = 0.0
        self.quad_timer = 0.0

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
        elif self.phase == 2:
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
        else:
            # 三阶段：四核环绕各自瞄准 + 周期合体爆裂环形
            self.quad_rot += dt * 1.0
            self.quad_timer += dt
            if self.quad_timer >= 0.9:
                self.quad_timer = 0.0
                qps = self._quad_positions()
                cx, cy = random.choice(qps)
                self._fire_aimed(player, BOSS_BULLET_SPEED, ox=cx, oy=cy)
            self.merge_timer += dt
            if self.merge_timer >= 3.5:
                self.merge_timer = 0.0
                self._fire_ring(self.ring_rot, 12, 180, color=(200, 120, 255))
                self._fire_ring(-self.ring_rot, 12, 220, color=C_BOSS_BULLET)

    def draw(self, screen, t):
        x, y = self.x, self.y
        if self.phase == 3:
            glow_col = (220, 140, 255)
        elif self.phase == 2:
            glow_col = (255, 120, 200)
        else:
            glow_col = C_BOSS_GLOW
        if self.phase == 1:
            (lx, ly), (rx, ry) = self._core_positions()
            chain = pygame.Surface((SCREEN_W, 2), pygame.SRCALPHA)
            pygame.draw.line(chain, (*C_BOSS_GLOW, 120), (0, 0), (SCREEN_W, 0), 2)
            screen.blit(chain, (int(lx), int(ly)))
            for cx, cy in ((lx, ly), (rx, ry)):
                self._draw_diamond(screen, cx, cy, 22, 18, glow_col, t)
        elif self.phase == 2:
            gr = int(46 * (1 + 0.12 * math.sin(t * 5)))
            g = _glow(gr, glow_col)
            screen.blit(g, (int(x - gr), int(y - gr)),
                        special_flags=pygame.BLEND_ADD)
            self._draw_diamond(screen, x, y, 30, 24, glow_col, t)
            for gx in (-8, 8):
                pygame.draw.circle(screen, C_BOSS_EYE, (int(x + gx), int(y)), 7)
                pygame.draw.circle(screen, (255, 255, 255), (int(x + gx), int(y)), 3)
        else:
            for cx, cy in self._quad_positions():
                gr = int(26 * (1 + 0.15 * math.sin(t * 6 + cx)))
                g = _glow(gr, glow_col)
                screen.blit(g, (int(cx - gr), int(cy - gr)),
                            special_flags=pygame.BLEND_ADD)
                self._draw_diamond(screen, cx, cy, 18, 14, glow_col, t)

    def _draw_diamond(self, screen, cx, cy, hw, hh, glow_col, t):
        pts = [(cx, cy - hh), (cx + hw, cy), (cx, cy + hh), (cx - hw, cy)]
        body = (255, 255, 255) if self.flash > 0 else C_BOSS_BODY
        pygame.draw.polygon(screen, body, pts)
        pygame.draw.polygon(screen, C_BOSS_EDGE, pts, 2)
        pygame.draw.circle(screen, C_BOSS_EYE, (int(cx), int(cy)), 5)


# ======================================================================
# 第 10 关：虚空行者（空间位移）
# ======================================================================
class VoidWalker(Boss):
    name = "虚空行者"
    _warn_flash = None

    def __init__(self, x, y, hp, wave):
        super().__init__(x, y, hp, wave)
        self.invisible = False
        self.teleport_timer = 1.5
        self.vanish_timer = 0.0
        self.after_warn = False
        self.warn_timer = 0.0
        self.hit_w = 40
        self.hit_h = 38

    def on_phase2(self):
        self.teleport_timer = 1.2

    def on_phase3(self):
        self.teleport_timer = 0.8

    def hit_test(self, bx, by):
        if self.invisible:
            return False
        return super().hit_test(bx, by)

    def update(self, dt, player):
        super().update(dt, player)
        if self.invisible:
            self.vanish_timer -= dt
            if self.vanish_timer <= 0:
                # 现身
                self.invisible = False
                self.x = random.randint(120, SCREEN_W - 120)
                self.y = BOSS_Y
                self._on_reappear(player)
        else:
            self.teleport_timer -= dt
            if self.teleport_timer <= 0:
                # 传送（消失）
                self.invisible = True
                self.vanish_timer = 0.5 if self.phase < 3 else 0.35
                self.teleport_timer = (1.5 if self.phase == 1
                                       else (1.2 if self.phase == 2 else 0.8))
                # 三阶段：全屏预警闪
                if self.phase == 3:
                    self.after_warn = True
                    self.warn_timer = 0.3
        if self.after_warn:
            self.warn_timer -= dt
            if self.warn_timer <= 0:
                self.after_warn = False

    def _on_reappear(self, player):
        if self.phase == 1:
            self._fire_fan(player, 2, math.radians(15), BOSS_BULLET_SPEED)
        elif self.phase == 2:
            self._fire_ring(self.t, 12, 160, color=C_BOSS_BULLET2)
            # 残影弹（旧位置散射）
            self._fire_fan(player, 5, math.radians(25), BOSS_BULLET_SPEED)
        else:
            # 现身散射 + 全屏预警后多发
            self._fire_ring(self.t, 16, 180, color=(180, 120, 255))
            self._fire_fan(player, 7, math.radians(25), BOSS_BULLET_FAST)

    def draw(self, screen, t):
        if self.invisible:
            # 仅画虚影
            x = self.x
            for i in range(3):
                a = (t * 3 + i) % math.tau
                rx = x + math.cos(a) * 10
                pygame.draw.circle(screen, (120, 60, 160),
                                   (int(rx), int(self.y)), 6, 1)
            return
        x, y = self.x, self.y
        glow_col = (160, 80, 220) if self.phase == 3 else (
            (140, 80, 200) if self.phase == 2 else C_BOSS_GLOW)
        gr = int(42 * (1 + 0.14 * math.sin(t * 6)))
        g = _glow(gr, glow_col)
        screen.blit(g, (int(x - gr), int(y - gr)),
                    special_flags=pygame.BLEND_ADD)
        # 裂缝体（不规则多边形 + 裂纹）
        n = 10
        pts = []
        for i in range(n):
            ang = i / n * math.tau + t * 0.3
            r = 30 + 4 * math.sin(t * 4 + i * 1.3)
            pts.append((x + math.cos(ang) * r, y + math.sin(ang) * r))
        body = (255, 255, 255) if self.flash > 0 else (50, 20, 60)
        pygame.draw.polygon(screen, body, pts)
        pygame.draw.polygon(screen, glow_col, pts, 2)
        # 裂纹
        for i in range(4):
            a = i / 4 * math.tau + t * 0.5
            pygame.draw.line(screen, (200, 120, 255),
                             (x, y),
                             (x + math.cos(a) * 26, y + math.sin(a) * 26), 2)
        pygame.draw.circle(screen, (200, 120, 255), (int(x), int(y)), 8)
        # 三阶段预警闪（缓存全屏闪光贴图）
        if self.after_warn:
            if VoidWalker._warn_flash is None:
                f = pygame.Surface((S.SCREEN_W, S.SCREEN_H), pygame.SRCALPHA)
                f.fill((180, 80, 220, 40))
                VoidWalker._warn_flash = f
            screen.blit(VoidWalker._warn_flash, (0, 0))


# ======================================================================
# 第 11 关：终焉之主（压轴综合，噩梦专属）
# ======================================================================
class FinalLord(Boss):
    name = "终焉之主"

    def __init__(self, x, y, hp, wave):
        super().__init__(x, y, hp, wave)
        self.combo_timer = 0.0
        self.combo_step = 0
        self.summon_timer = 0.0
        self.sweep = SweepBeam()
        self.sweep_timer = 0.0
        # 三阶段护盾卫星
        self.satellites = []     # [{angle, hp, max_hp, alive}]
        self.sat_respawn = 0.0
        self.bomb_timer = 0.0
        self.ring_rot = 0.0
        self.tracking_timer = 0.0
        self.hit_w = 46
        self.hit_h = 42

    # ---- 护盾卫星 ----
    def has_shield(self):
        return any(s["alive"] for s in self.satellites)

    def hit_test(self, bx, by):
        if self.has_shield():
            return False
        return super().hit_test(bx, by)

    def _sat_positions(self):
        pts = []
        for s in self.satellites:
            if s["alive"]:
                sx = self.x + math.cos(s["angle"]) * FINAL_SATELLITE_DIST
                sy = self.y + math.sin(s["angle"]) * FINAL_SATELLITE_DIST
                pts.append((s, sx, sy))
        return pts

    def hit_satellite(self, bx, by, dmg):
        for s, sx, sy in self._sat_positions():
            if math.hypot(bx - sx, by - sy) <= 18:
                s["hp"] -= dmg
                if s["hp"] <= 0:
                    s["alive"] = False
                return True
        return False

    def _spawn_satellites(self):
        self.satellites = []
        for i in range(FINAL_SATELLITE_COUNT):
            self.satellites.append({
                "angle": i / FINAL_SATELLITE_COUNT * math.tau,
                "hp": FINAL_SATELLITE_HP,
                "max_hp": FINAL_SATELLITE_HP,
                "alive": True,
            })

    def on_phase2(self):
        self.combo_timer = 0.0
        self.combo_step = 0

    def on_phase3(self):
        self._spawn_satellites()
        self.combo_timer = 0.0
        self.combo_step = 0

    def update(self, dt, player):
        super().update(dt, player)
        self.ring_rot += dt * 1.0
        # 卫星旋转 + 护盾回血
        for s in self.satellites:
            if s["alive"]:
                s["angle"] += dt * 1.2
        if self.has_shield():
            # 护盾存在时本体每秒回 1% 最大血量
            self.hp = min(self.max_hp, self.hp + self.max_hp * FINAL_SATELLITE_REGEN_PCT * dt)
        # 护盾只生效一次：卫星全灭后不再再生
        # 横扫激光（二阶段起）
        self.sweep.update(dt, player)

        if self.phase == 1:
            # 混沌降临：环形 / 扇形 / 瞄准 周期交替
            self.combo_timer += dt
            if self.combo_timer >= 1.4:
                self.combo_timer = 0.0
                if self.combo_step % 3 == 0:
                    self._fire_ring(self.ring_rot, 10, 150, color=C_BOSS_BULLET2)
                elif self.combo_step % 3 == 1:
                    self._fire_fan(player, 5, math.radians(25), BOSS_BULLET_SPEED)
                else:
                    self._fire_aimed(player, BOSS_BULLET_FAST)
                self.combo_step += 1
        elif self.phase == 2:
            # 维度崩塌：召唤精英怪 + 螺旋弹幕 + 横扫激光
            self.combo_timer += dt
            if self.combo_timer >= 0.4:
                self.combo_timer = 0.0
                a = self.ring_rot * 2
                self.bullets.append(BossBullet(
                    self.x, self.y, math.cos(a) * 170, math.sin(a) * 170,
                    color=C_BOSS_BULLET2, radius=4))
                self.bullets.append(BossBullet(
                    self.x, self.y, math.cos(a + math.pi) * 170,
                    math.sin(a + math.pi) * 170, color=C_BOSS_BULLET, radius=4))
            self.summon_timer += dt
            if self.summon_timer >= 4.0:
                self.summon_timer = 0.0
                mx = random.randint(DIVIDER_X + 30, SCREEN_W - 30)
                self.summons.append(Monster(mx, self.y + 30, 6))
            self.sweep_timer += dt
            if self.sweep_timer >= 5.0 and not self.sweep.active:
                self.sweep_timer = 0.0
                self.sweep.start(from_left=random.random() < 0.5)
        else:
            # 终焉审判：多重反向旋转环 + 追踪弹 + 落点轰炸 + 召唤精英怪 + 横扫激光
            self.combo_timer += dt
            if self.combo_timer >= 1.6:
                self.combo_timer = 0.0
                self._fire_ring(self.ring_rot, 12, 160, color=C_BOSS_BULLET2)
                self._fire_ring(-self.ring_rot, 12, 200, color=(200, 120, 255))
            self.tracking_timer += dt
            if self.tracking_timer >= 2.8:
                self.tracking_timer = 0.0
                self._fire_tracking(player, 3, 140, color=(255, 120, 120))
            self.bomb_timer += dt
            if self.bomb_timer >= 3.5:
                self.bomb_timer = 0.0
                # 落点轰炸：向玩家位置发射一枚大型慢速弹（命中即爆炸感）
                px = player.x
                self.bullets.append(BossBullet(
                    px, self.y + 20, 0, 200, color=(255, 240, 120),
                    radius=8, life=3.0))
            # 召唤精英怪
            self.summon_timer += dt
            if self.summon_timer >= 5.0:
                self.summon_timer = 0.0
                mx = random.randint(DIVIDER_X + 30, SCREEN_W - 30)
                self.summons.append(Monster(mx, self.y + 30, 6))
            # 横扫激光
            self.sweep_timer += dt
            if self.sweep_timer >= 6.0 and not self.sweep.active:
                self.sweep_timer = 0.0
                self.sweep.start(from_left=random.random() < 0.5)

    def draw(self, screen, t):
        x, y = self.x, self.y
        if self.phase == 3:
            glow_col = (200, 60, 60)
        elif self.phase == 2:
            glow_col = (180, 60, 120)
        else:
            glow_col = (160, 60, 180)
        gr = int(50 * (1 + 0.12 * math.sin(t * 4)))
        g = _glow(gr, glow_col)
        screen.blit(g, (int(x - gr), int(y - gr)),
                    special_flags=pygame.BLEND_ADD)
        # 巨大核心（多角）
        n = 12
        pts = []
        for i in range(n * 2):
            ang = i / (n * 2) * math.tau + t * 0.3
            r = 38 if i % 2 == 0 else 24
            pts.append((x + math.cos(ang) * r, y + math.sin(ang) * r))
        body = (255, 255, 255) if self.flash > 0 else (60, 20, 40)
        pygame.draw.polygon(screen, body, pts)
        pygame.draw.polygon(screen, glow_col, pts, 2)
        pygame.draw.circle(screen, (255, 200, 100), (int(x), int(y)), 14)
        pygame.draw.circle(screen, (255, 255, 255), (int(x), int(y)), 6)
        # 护盾卫星
        for s, sx, sy in self._sat_positions():
            sg = _glow(16, (120, 200, 255))
            screen.blit(sg, (int(sx - 16), int(sy - 16)),
                        special_flags=pygame.BLEND_ADD)
            pygame.draw.circle(screen, (90, 160, 220), (int(sx), int(sy)), 14)
            pygame.draw.circle(screen, (180, 230, 255), (int(sx), int(sy)), 14, 2)
            pygame.draw.circle(screen, (255, 255, 255), (int(sx), int(sy)), 5)
            # 卫星血条
            ratio = s["hp"] / s["max_hp"]
            pygame.draw.rect(screen, (40, 20, 30),
                             (int(sx - 14), int(sy - 22), 28, 3))
            pygame.draw.rect(screen, (120, 200, 255),
                             (int(sx - 14), int(sy - 22), int(28 * ratio), 3))
        # 护盾光环
        if self.has_shield():
            pulse = 1 + 0.08 * math.sin(t * 8)
            pygame.draw.circle(screen, (120, 200, 255), (int(x), int(y)),
                               int(56 * pulse), 2)
        # 横扫激光
        self.sweep.draw(screen)


# ======================================================================
# 工厂（按关卡顺序：1~11，难度由 settings.BOSS_PHASES 控制阶段数）
# ======================================================================
_BOSS_CLASSES = [None,
                 RiftEye,        # 1
                 TwinMirage,     # 2
                 HiveMatriarch,  # 3
                 VortexCore,     # 4
                 VoidWalker,     # 5
                 SpiralAbyss,    # 6
                 JudgementCore,  # 7
                 EchoBastion,    # 8
                 HunterEye,      # 9
                 PrismSentinel,  # 10
                 FinalLord]      # 11（噩梦专属）


def make_boss(wave, difficulty=None):
    """根据波数生成对应 BOSS（血量 = BOSS_HP_MULT × 该波怪物血量；
    倍率随难度：简单100/普通140/困难170/噩梦200）。"""
    hp = S.BOSS_HP_MULT * monster_hp(wave)
    cls = _BOSS_CLASSES[wave]
    return cls(SCREEN_W // 2, BOSS_Y, hp, wave)
