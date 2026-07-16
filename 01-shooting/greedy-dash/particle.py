# -*- coding: utf-8 -*-
"""
粒子系统：背景星光、玩家尾焰、子弹拖尾、爆炸与击破特效
"""
import math
import random

import pygame

from settings import *
from player import _glow_alpha


class Particle:
    def __init__(self, x, y, vx, vy, life, color, size, additive=False, gravity=0):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = life
        self.color = color
        self.size = size
        self.additive = additive
        self.gravity = gravity

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += self.gravity * dt
        self.life -= dt

    def draw(self, screen):
        if self.life <= 0:
            return
        ratio = self.life / self.max_life
        if self.additive:
            r = max(1, int(self.size * (0.4 + 0.6 * ratio)))
            gsurf = _glow_alpha(r, self.color, int(220 * ratio))
            screen.blit(gsurf, (int(self.x - r), int(self.y - r)),
                        special_flags=pygame.BLEND_ADD)
        else:
            alpha = int(255 * ratio)
            pygame.draw.circle(screen, (*self.color, alpha), (int(self.x), int(self.y)),
                               max(1, int(self.size * ratio)))


class ParticleSystem:
    def __init__(self):
        self.particles = []

    def spawn(self, x, y, vx, vy, life, color, size, additive=False, gravity=0):
        self.particles.append(Particle(x, y, vx, vy, life, color, size, additive, gravity))

    def burst(self, x, y, color, count=14, speed=120, life=0.5, size=3, additive=True):
        """爆炸/击破特效：向四周喷射粒子。"""
        for _ in range(count):
            ang = random.uniform(0, math.tau)
            sp = random.uniform(speed * 0.4, speed)
            vx = math.cos(ang) * sp
            vy = math.sin(ang) * sp
            self.spawn(x, y, vx, vy, life * random.uniform(0.6, 1.2),
                       color, size * random.uniform(0.6, 1.2), additive)

    def update(self, dt):
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.life > 0]

    def draw(self, screen):
        for p in self.particles:
            p.draw(screen)


class StarField:
    """背景缓慢下落的星光粒子。"""
    def __init__(self, count=STAR_COUNT):
        self.stars = []
        for _ in range(count):
            self.stars.append(self._new_star(top=random.randint(0, SCREEN_H)))

    def _new_star(self, top=None):
        y = top if top is not None else -5
        return {
            "x": random.randint(0, SCREEN_W),
            "y": y,
            "speed": random.uniform(8, 28),
            "size": random.uniform(0.6, 1.8),
            "alpha": random.randint(60, 200),
            "tw": random.uniform(0, math.tau),  # 闪烁相位
        }

    def update(self, dt):
        for s in self.stars:
            s["y"] += s["speed"] * dt
            s["tw"] += dt * 3
            if s["y"] > SCREEN_H + 5:
                s.update(self._new_star(top=-5))

    def draw(self, screen):
        for s in self.stars:
            a = int(s["alpha"] * (0.6 + 0.4 * math.sin(s["tw"])))
            pygame.draw.circle(screen, (200, 210, 255, a), (int(s["x"]), int(s["y"])),
                               int(s["size"]))
