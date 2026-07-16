# -*- coding: utf-8 -*-
"""
Treasure Dash - 竖屏射击小游戏（主程序）
运行：python main.py
打包：venv/Scripts/python.exe -m PyInstaller GreedyDash.spec

玩法：
- 移动鼠标控制单位队列左右平移（仅横向，Y 固定在底部）
- 自动向上射击：左侧打宝箱拿奖励，右侧打怪物求生存
- ESC 暂停 / 继续，结束点按钮重开
"""
import math
import random
import sys

import pygame

import settings as S
from player import Player, _glow, _glow_alpha
from enemy import Chest, Monster, BigChest
from particle import ParticleSystem, StarField
import ui


# ---------- 预生成静态表面 ----------
def make_background():
    """深紫 -> 深蓝 垂直渐变背景。"""
    surf = pygame.Surface((S.SCREEN_W, S.SCREEN_H))
    top, bot = S.C_BG_TOP, S.C_BG_BOTTOM
    for y in range(S.SCREEN_H):
        t = y / S.SCREEN_H
        r = int(top[0] + (bot[0] - top[0]) * t)
        g = int(top[1] + (bot[1] - top[1]) * t)
        b = int(top[2] + (bot[2] - top[2]) * t)
        pygame.draw.line(surf, (r, g, b), (0, y), (S.SCREEN_W, y))
    return surf


def make_divider():
    """中央半透明垂直分割线：透明 -> 亮紫 -> 透明。"""
    surf = pygame.Surface((2, S.SCREEN_H), pygame.SRCALPHA)
    for y in range(S.SCREEN_H):
        a = int(255 * math.sin(math.pi * y / S.SCREEN_H))
        pygame.draw.line(surf, (*S.C_DIVIDER, a), (0, y), (1, y))
    return surf


# ---------- 子弹 ----------
class Bullet:
    def __init__(self, x, y, damage):
        self.x = x
        self.y = y
        self.damage = damage
        self.trail = [(x, y)]

    def update(self, dt):
        self.y -= S.BULLET_SPEED * dt
        self.trail.append((self.x, self.y))
        if len(self.trail) > S.BULLET_TRAIL:
            self.trail.pop(0)

    def off(self):
        return self.y < -12

    def draw(self, screen, glow_out, glow_mid):
        # 5 帧拖尾残影（青色，叠加发光）——使用 alpha 量化缓存，避免每帧创建 Surface
        n = len(self.trail)
        for i, pos in enumerate(self.trail[:-1]):
            ratio = (i + 1) / n
            a = int(110 * ratio)
            r = max(1, int(3 * ratio))
            gs = _glow_alpha(r + 1, S.C_BULLET_OUT, a)
            screen.blit(gs, (int(pos[0] - r - 1), int(pos[1] - r - 1)),
                        special_flags=pygame.BLEND_ADD)
        # 三层光球：外层青 / 中层白 / 核心纯白（BLEND_ADD）
        screen.blit(glow_out, (int(self.x - 7), int(self.y - 7)),
                    special_flags=pygame.BLEND_ADD)
        screen.blit(glow_mid, (int(self.x - 4), int(self.y - 4)),
                    special_flags=pygame.BLEND_ADD)
        pygame.draw.circle(screen, S.C_BULLET_CORE, (int(self.x), int(self.y)), 2)


# ---------- 游戏 ----------
class Game:
    def __init__(self, screen):
        self.screen = screen
        self.bg = make_background()
        self.divider = make_divider()
        self.glow_out = _glow(7, S.C_BULLET_OUT)
        self.glow_mid = _glow(4, S.C_BULLET_MID)
        self.stars = StarField()
        self.hud = ui.HUD()
        self.reset()

    def reset(self):
        """重置全部游戏状态（用于开局 / 重开）。"""
        self.player = Player()
        self.chests = self._make_chests()
        self.monsters = []
        self.bullets = []
        self.particles = ParticleSystem()
        self.floats = []
        self.global_level = 0
        self.wave = 1
        # 第一波直接出怪：进入 active 并立即生成首只怪物
        self.wave_state = "active"
        self.spawned_count = 0
        self.spawn_timer = S.WAVE_SPAWN_INTERVAL  # 让第一只怪物在第 1 帧就生成
        self.wave_banner_timer = S.WAVE_BANNER_TIME  # 波次提示（非阻塞，3s 淡退）
        self.wave_banner_wave = self.wave
        self.state = "playing"       # playing / paused / gameover
        self.big_chest = None          # 当前大宝箱（最多 1 个）
        self.flash = 0.0                  # 击破大宝箱时的屏幕闪白计时
        self.big_reward = None             # (文字, 颜色, 剩余时间) 大宝箱奖励提示
        self._spawn_big_chest()   # 初始即有一个大宝箱（wave 已确定，放最后）

    def _make_chests(self):
        """左侧 10 个宝箱，固定位置，避开底部 120px。"""
        chests = []
        top = S.CHEST_TOP_MARGIN
        bottom = S.SCREEN_H - S.CHEST_BOTTOM_AVOID
        step = (bottom - top) / S.CHEST_COUNT
        for i in range(S.CHEST_COUNT):
            y = top + step * (i + 0.5)
            chests.append(Chest(S.CHEST_X, y, wave=1))
        return chests

    # ---------- 大宝箱 ----------
    def _spawn_big_chest(self):
        """在分割线左边的右半部分（x ∈ 120~240）生成 1 个大宝箱。
        血量 = 当前波怪物血量 * BIG_CHEST_HP_MULT（现 12）。"""
        x = random.randint(S.DIVIDER_X // 2 + 12, S.DIVIDER_X - 12)
        y = -S.BIG_CHEST_SIZE
        hp = S.BIG_CHEST_HP_MULT * S.monster_hp(self.wave)
        self.big_chest = BigChest(x, y, hp)

    # ---------- 波次 ----------
    def _spawn_monster(self, max_count=1):
        """生成一批并排怪物，返回实际生成数量。
        概率：5% 三个并排 / 10% 两个并排 / 85% 单个；
        受本波剩余名额 max_count 与屏幕横向空间双重限制（放不下自动降级）。
        """
        left = S.DIVIDER_X + S.MONSTER_SPAWN_MARGIN
        right = S.SCREEN_W - S.MONSTER_SPAWN_MARGIN
        # 掷骰决定并排数量
        roll = random.random()
        if roll < S.MONSTER_P_TRIPLE:
            count = 3
        elif roll < S.MONSTER_P_TRIPLE + S.MONSTER_P_DOUBLE:
            count = 2
        else:
            count = 1
        count = min(count, max_count)
        # 屏幕空间检查：放不下就逐级降级
        spacing = S.MONSTER_GROUP_SPACING
        while count > 1 and (count - 1) * spacing > (right - left):
            count -= 1

        y = -S.MONSTER_H
        hp = S.monster_hp(self.wave)
        span = (count - 1) * spacing
        cx = random.randint(int(left + span / 2), int(right - span / 2))
        start = cx - span / 2
        for i in range(count):
            x = int(start + i * spacing)
            self.monsters.append(Monster(x, y, hp))
            self.particles.burst(x, y + 10, S.C_MON_GLOW, 8, 80, 0.4, 2)
        return count

    def _update_wave(self, dt):
        # 仅 active 状态：生成怪物；清空后立即进入下一波（见下方判定）
        if self.wave_state == "active":
            target = S.monster_count(self.wave)
            # 全部生成且场上无怪物 -> 立即进入下一波（不等待）
            if self.spawned_count >= target and not self.monsters:
                self.wave += 1
                self.big_chest = None
                self._spawn_big_chest()   # 进入下一波重置大宝箱
                self.wave_state = "active"
                self.spawned_count = 0
                self.spawn_timer = S.WAVE_SPAWN_INTERVAL  # 下一波首只立即生成
                # 显示下一波提示（非阻塞，3 秒淡退）
                self.wave_banner_timer = S.WAVE_BANNER_TIME
                self.wave_banner_wave = self.wave
                target = S.monster_count(self.wave)  # 切换为新波目标
            # 按间隔生成怪物（剩余名额限制，保证本波总数精确）
            if self.spawned_count < target:
                self.spawn_timer += dt
                if self.spawn_timer >= S.WAVE_SPAWN_INTERVAL:
                    self.spawn_timer = 0.0
                    self.spawned_count += self._spawn_monster(target - self.spawned_count)

    # ---------- 奖励 ----------
    def _break_chest(self, chest):
        chest.break_()
        self.global_level += 1
        r = random.random()
        if r < S.P_ATK:
            amt = S.attack_bonus(self.wave // 4)
            self.player.apply_attack(amt)
            msg, col = "攻击力 +%d" % amt, S.C_GOLD
        else:
            self.player.apply_speed(self.global_level)
            msg, col = "攻速提升!", S.C_SHIP_CORE2
        self.floats.append(ui.FloatingText(chest.x, chest.y - 22, msg, col))
        self.particles.burst(chest.x, chest.y, S.C_CHEST_GLOW, 18, 150, 0.6, 3)

    # ---------- 大宝箱奖励 ----------
    def _break_big_chest(self, chest):
        """大宝箱击破奖励（加权概率）：
        护盾可用：攻击增幅 40 / 超载火力 25 / 护盾 15 / 分身 20
        护盾已满：护盾的 15% 并入攻击增幅 -> 攻击增幅 55 / 超载火力 25 / 分身 20
        """
        if self.player.all_shielded():
            # 护盾满：其 15% 并入攻击增幅
            weights = [("atk", S.BIG_P_ATK + S.BIG_P_SHIELD),
                       ("spd", S.BIG_P_SPD),
                       ("unit", S.BIG_P_UNIT)]
        else:
            weights = [("atk", S.BIG_P_ATK),
                       ("spd", S.BIG_P_SPD),
                       ("shield", S.BIG_P_SHIELD),
                       ("unit", S.BIG_P_UNIT)]
        kinds = [k for k, _ in weights]
        ws = [w for _, w in weights]
        kind = random.choices(kinds, ws)[0]
        if kind == "atk":
            amt = 2 * S.attack_bonus(self.wave // 4)      # 小宝箱规则 ×2
            self.player.apply_attack(amt)
            msg, col = "攻击增幅! +%d" % amt, S.C_GOLD
        elif kind == "spd":
            self.player.apply_speed(self.global_level, mult=2)  # 普通规则 ×2
            msg, col = "超载火力!", S.C_SHIP_CORE2
        elif kind == "shield":
            self.player.add_shield_random()
            msg, col = "获得护盾!", S.C_SHIELD
        else:  # unit 分身
            if self.player.add_unit():
                msg, col = "新增单位!", S.C_CLONE_GLOW
            else:
                # 单位已满，回退为攻击增幅
                amt = 2 * S.attack_bonus(self.wave // 4)
                self.player.apply_attack(amt)
                msg, col = "攻击增幅! +%d" % amt, S.C_GOLD
        # 特效：大量金色粒子 + 屏幕短暂闪白
        self.particles.burst(chest.x, chest.y, S.C_BIGCHEST_GLOW, 40, 220, 0.7, 4)
        self.flash = 0.18
        # 界面提示获得的奖励（居中显示 2.2 秒）
        self.big_reward = (msg, col, 2.2)

    # ---------- 碰撞 ----------
    def _collisions(self):
        # 子弹 vs 大宝箱（屏幕内才可被击中；击破给特殊奖励）
        if self.big_chest is not None:
            c = self.big_chest
            if c.y + S.BIG_CHEST_SIZE // 2 > 0:   # 已部分进入屏幕
                for b in self.bullets:
                    if abs(b.x - c.x) <= S.BIG_CHEST_HIT_X \
                            and abs(b.y - c.y) <= S.BIG_CHEST_HIT_Y:
                        c.hit(b.damage)
                        b.y = -999
                        if c.hp <= 0:
                            self._break_big_chest(c)
                            self.big_chest = None
                        break
        # 子弹 vs 宝箱（带容差的矩形判定，让多单位时偏离中心的子弹也能命中）
        for b in self.bullets:
            for c in self.chests:
                if c.alive and abs(b.x - c.x) <= S.CHEST_HIT_X \
                        and abs(b.y - c.y) <= S.CHEST_HIT_Y:
                    c.hit(b.damage)
                    if c.hp <= 0:
                        self._break_chest(c)
                    b.y = -999  # 标记移除
                    break
        # 子弹 vs 怪物
        for b in self.bullets:
            if b.y < -100:
                continue
            for m in self.monsters:
                if m.rect().collidepoint(b.x, b.y):
                    m.hit(b.damage)
                    if m.dead:
                        self.particles.burst(m.x, m.y, S.C_MON_GLOW, 16, 160, 0.5, 3)
                    b.y = -999
                    break
        # 怪物 vs 玩家单位：只要怪物纵向抵达玩家所在行（无论横向位置），
        # 就随机击杀一个存活单位——玩家无法靠躲到角落无限苟活。
        py = self.player.y
        for m in list(self.monsters):
            if not m.dead and m.reached_player_line(py):
                self.player.kill_random_unit()
                m.flash = 0.12
                m.dead = True
                self.particles.burst(self.player.x, py, S.C_SHIP_GLOW, 14, 150, 0.5, 3)
                self.particles.burst(m.x, m.y, S.C_MON_GLOW, 14, 150, 0.5, 3)
                self.monsters.remove(m)

    # ---------- 更新 ----------
    def update(self, dt):
        if self.state != "playing":
            # 暂停：完全冻结；游戏结束：仅让粒子/星光继续衰减作为氛围
            if self.state == "gameover":
                self.particles.update(dt)
                self.stars.update(dt)
                for f in self.floats:
                    f.update(dt)
                self.floats = [f for f in self.floats if f.life > 0]
            return

        # 玩家移动：队列中心 x 跟随鼠标（y 固定在底部，不跟随鼠标）
        mx, _ = pygame.mouse.get_pos()
        self.player.follow_mouse(mx, dt)
        self.player.update(dt)

        # 自动射击（全队共享射速，每个单位独立发射）
        if self.player.should_fire():
            for ux in self.player.unit_positions():
                self.bullets.append(Bullet(ux, self.player.y - 10, self.player.attack))
                self.particles.spawn(ux, self.player.y + 6,
                                     random.uniform(-15, 15), random.uniform(40, 90),
                                     0.22, S.C_FLAME, 2, additive=True)

        # 更新实体
        for b in self.bullets:
            b.update(dt)
        self.bullets = [b for b in self.bullets if not b.off()]
        for m in self.monsters:
            m.update(dt)
        # 移除已死亡（血量归零）或移出屏幕的怪物——死亡怪物必须清除，
        # 否则会继续下落并撞死玩家单位，波次也无法判定清空。
        self.monsters = [m for m in self.monsters
                         if not m.dead and not m.off_screen()]
        for c in self.chests:
            c.update(dt, self.wave)
        # 大宝箱：缓慢下落；到达底部边界后消失（不给奖励）
        if self.big_chest is not None:
            self.big_chest.update(dt)
            if self.big_chest.off_bottom():
                self.big_chest = None
        self.particles.update(dt)
        self.stars.update(dt)
        for f in self.floats:
            f.update(dt)
        self.floats = [f for f in self.floats if f.life > 0]
        # 波次提示计时（非阻塞，3 秒淡退）
        if self.wave_banner_timer > 0:
            self.wave_banner_timer = max(0.0, self.wave_banner_timer - dt)
        # 闪白与奖励提示计时
        if self.flash > 0:
            self.flash = max(0.0, self.flash - dt)
        if self.big_reward is not None:
            msg, col, t = self.big_reward
            t -= dt
            if t <= 0:
                self.big_reward = None
            else:
                self.big_reward = (msg, col, t)

        self._update_wave(dt)
        self._collisions()

        # HUD 数值弹跳
        self.hud.update(dt, self.player, self.wave, self.global_level)

        # 游戏结束判定
        if self.player.is_dead():
            self.state = "gameover"

    # ---------- 绘制 ----------
    def draw(self):
        self.screen.blit(self.bg, (0, 0))
        self.stars.draw(self.screen)
        self.screen.blit(self.divider, (S.DIVIDER_X - 1, 0))

        for c in self.chests:
            c.draw(self.screen, self.player.t)
        if self.big_chest is not None:
            self.big_chest.draw(self.screen, self.player.t)
        for m in self.monsters:
            m.draw(self.screen)
        for b in self.bullets:
            b.draw(self.screen, self.glow_out, self.glow_mid)
        self.player.draw(self.screen)
        self.particles.draw(self.screen)
        for f in self.floats:
            f.draw(self.screen)

        self.hud.draw(self.screen, self.player, self.wave, self.global_level)
        ui.draw_pause_button(self.screen,
                             ui.PAUSE_BTN.collidepoint(pygame.mouse.get_pos()))

        # 波次提示（非阻塞，3 秒淡退）；不影响出怪
        if self.wave_banner_timer > 0:
            a = 255 * (self.wave_banner_timer / S.WAVE_BANNER_TIME)
            ui.draw_wave_intro(self.screen, self.wave_banner_wave, a)
        if self.state == "paused":
            ui.draw_pause_overlay(self.screen)
        if self.state == "gameover":
            ui.draw_gameover(self.screen, self.wave,
                             ui.RESTART_BTN.collidepoint(pygame.mouse.get_pos()))

        # 大宝箱击破：屏幕短暂闪白
        if self.flash > 0:
            a = int(200 * (self.flash / 0.18))
            f = pygame.Surface((S.SCREEN_W, S.SCREEN_H), pygame.SRCALPHA)
            f.fill((255, 255, 255, a))
            self.screen.blit(f, (0, 0))

        # 大宝箱奖励提示（居中、大号）
        if self.big_reward is not None:
            msg, col, _ = self.big_reward
            font = self.hud.big_font
            surf = font.render(msg, True, col)
            rect = surf.get_rect(center=(S.SCREEN_W // 2, S.SCREEN_H // 2 - 120))
            self.screen.blit(surf, rect)

    # ---------- 输入 ----------
    def toggle_pause(self):
        if self.state == "playing":
            self.state = "paused"
        elif self.state == "paused":
            self.state = "playing"

    def pause_if_playing(self):
        """窗口失去焦点时自动暂停（仅 playing -> paused，不反向）。"""
        if self.state == "playing":
            self.state = "paused"


def main():
    pygame.init()
    # 开启双缓冲 + 垂直同步，消除帧时间抖动与画面撕裂（卡顿主观感受的主因之一）；
    # 部分驱动不支持时自动回退到普通窗口。
    try:
        screen = pygame.display.set_mode(
            (S.SCREEN_W, S.SCREEN_H),
            pygame.DOUBLEBUF | pygame.SCALED, vsync=1)
    except pygame.error:
        screen = pygame.display.set_mode((S.SCREEN_W, S.SCREEN_H))
    pygame.display.set_caption(S.TITLE)
    clock = pygame.time.Clock()
    game = Game(screen)
    fps_timer = 0.0

    while True:
        dt = min(clock.tick(S.FPS) / 1000.0, 0.05)

        # 标题栏显示实时 FPS（每 0.5s 刷新一次），便于确认帧率是否达标
        fps_timer += dt
        if fps_timer >= 0.5:
            fps_timer = 0.0
            pygame.display.set_caption("%s  FPS:%.0f" % (S.TITLE, clock.get_fps()))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.ACTIVEEVENT:
                # 仅当：点击了其他窗口（键盘焦点丢失，state&2）或
                # 最小化 / 隐藏（state&4）时才自动暂停。
                # 鼠标单纯移出窗口（仅 state&1 丢失）不暂停。
                if event.gain == 0 and (event.state & 2 or event.state & 4):
                    game.pause_if_playing()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    game.toggle_pause()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                if game.state == "gameover":
                    if ui.RESTART_BTN.collidepoint(mx, my):
                        game.reset()
                elif game.state == "paused":
                    if ui.RESUME_BTN.collidepoint(mx, my):
                        game.toggle_pause()
                else:
                    if ui.PAUSE_BTN.collidepoint(mx, my):
                        game.toggle_pause()

        game.update(dt)
        game.draw()
        pygame.display.flip()


if __name__ == "__main__":
    main()
