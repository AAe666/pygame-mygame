# -*- coding: utf-8 -*-
"""
Treasure Dash - 竖屏射击小游戏（主程序）
运行：python main.py
打包：venv/Scripts/python.exe -m PyInstaller GreedyDash.spec

玩法：
- 移动鼠标控制单位队列左右平移（仅横向，Y 固定在底部）
- 自动向上射击：左侧打宝箱拿奖励，右侧打怪物求生存
- ESC 暂停 / 继续，结束点按钮重开
- 主菜单选择难度：简单 / 普通 / 困难 / 噩梦
"""
import math
import random
import sys

import pygame

import settings as S
from player import Player, _glow, _glow_alpha
from enemy import Chest, Monster, BigChest
from boss import make_boss
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
        self.consumed = False       # 是否已被命中逻辑处理（用于区分"命中移除"与"飞出屏幕"）

    def update(self, dt):
        self.y -= S.BULLET_SPEED * dt
        self.trail.append((self.x, self.y))
        if len(self.trail) > S.BULLET_TRAIL:
            self.trail.pop(0)

    def off(self):
        return self.y < -12

    def draw(self, screen, glow_out, glow_mid):
        n = len(self.trail)
        for i, pos in enumerate(self.trail[:-1]):
            ratio = (i + 1) / n
            a = int(110 * ratio)
            r = max(1, int(3 * ratio))
            gs = _glow_alpha(r + 1, S.C_BULLET_OUT, a)
            screen.blit(gs, (int(pos[0] - r - 1), int(pos[1] - r - 1)),
                        special_flags=pygame.BLEND_ADD)
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
        self.difficulty = "normal"
        self.state = "menu"       # menu / help / playing / paused / gameover / victory
        self.help_page = 0
        self.help_scroll = 0          # 说明页滚动偏移
        self.help_content_h = 0       # 说明页内容总高度
        self.help_dragging = False    # 是否正在拖动滚动条
        self.help_drag_offset = 0     # 拖动偏移
        self.ui_t = 0.0           # 菜单/界面动画时间
        # 调试模式：连续按 ` 键 6 次（2 秒内）切换，默认关闭，避免误触
        self.debug_mode = False
        self.debug_count = 0
        self.debug_timer = 0.0
        self.cheat_buf = ""         # 作弊码输入缓冲（累积字母键）
        self.reset()

    def reset(self, difficulty=None):
        """重置全部游戏状态（用于开局 / 重开）。difficulty=None 时保留当前难度。"""
        if difficulty is not None:
            self.difficulty = difficulty
        S.set_difficulty(self.difficulty)
        self.player = Player()
        self.chests = self._make_chests()
        self.monsters = []
        self.bullets = []
        self.particles = ParticleSystem()
        self.floats = []
        self.global_level = 0
        self.wave = 1
        self.wave_state = "active"
        self.spawned_count = 0
        self.spawn_timer = S.WAVE_SPAWN_INTERVAL
        self.wave_banner_timer = S.WAVE_BANNER_TIME
        self.wave_banner_wave = self.wave
        self.big_chest = None
        self.flash = 0.0
        self.big_reward = None
        self.boss = None
        self.boss_bullets = []
        self.boss_intro_timer = 0.0
        self.kill_count = 0
        self.bosses_defeated = 0
        self.game_time = 0.0
        self.chests_broken = 0
        self.big_chests_broken = 0
        # 伤害统计 / 命中率（v3.1.0）
        self.shots_fired = 0        # 发射子弹数
        self.shots_hit = 0          # 命中目标子弹数
        self.damage_dealt = 0       # 造成的伤害（实际扣血）
        self.damage_lost = 0        # 丢失的伤害（飞出屏幕未命中）
        self._spawn_big_chest()

    def start_game(self, difficulty):
        """从主菜单开始游戏（指定难度）。"""
        self.reset(difficulty)
        self.state = "playing"

    def jump_to_wave(self, wave):
        """调试用：直接跳到指定波并进入 BOSS 战（跳过清怪与出场动画）。"""
        wave = max(1, min(wave, S.WAVE_TOTAL))
        self.wave = wave
        self.monsters = []
        self.bullets = []
        self.boss_bullets = []
        self.big_chest = None
        self.boss = make_boss(wave, self.difficulty)
        self.boss.x = S.SCREEN_W // 2
        self.boss.y = S.BOSS_Y
        self.boss.intro = False
        self.boss.fire_timer = 0.0
        self.wave_state = "boss"

    def _make_chests(self):
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
        x = random.randint(S.DIVIDER_X // 2 + 12, S.DIVIDER_X - 12)
        y = -S.BIG_CHEST_SIZE
        hp = S.BIG_CHEST_HP_MULT * S.monster_hp(self.wave)
        self.big_chest = BigChest(x, y, hp)

    # ---------- 波次 ----------
    def _spawn_monster(self, max_count=1):
        left = S.DIVIDER_X + S.MONSTER_SPAWN_MARGIN
        right = S.SCREEN_W - S.MONSTER_SPAWN_MARGIN
        roll = random.random()
        if roll < S.MONSTER_P_TRIPLE:
            count = 3
        elif roll < S.MONSTER_P_TRIPLE + S.MONSTER_P_DOUBLE:
            count = 2
        else:
            count = 1
        count = min(count, max_count)
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
        if self.wave_state == "active":
            target = S.monster_count(self.wave)
            if self.spawned_count >= target and not self.monsters:
                self._spawn_boss()
                return
            if self.spawned_count < target:
                self.spawn_timer += dt
                if self.spawn_timer >= S.WAVE_SPAWN_INTERVAL:
                    self.spawn_timer = 0.0
                    self.spawned_count += self._spawn_monster(target - self.spawned_count)
        elif self.wave_state == "boss":
            self.boss.update(dt, self.player)
            if self.boss.bullets:
                self.boss_bullets.extend(self.boss.bullets)
                self.boss.bullets = []
            if self.boss.summons:
                self.monsters.extend(self.boss.summons)
                self.boss.summons = []
            if self.boss.dead:
                self._on_boss_dead()

    # ---------- BOSS ----------
    def _spawn_boss(self):
        self.boss = make_boss(self.wave, self.difficulty)
        self.boss.intro = True
        self.boss.x = S.SCREEN_W // 2
        self.boss.y = S.SCREEN_H // 2 - 20
        self.big_chest = None
        self.bullets = []
        self.boss_bullets = []
        self.wave_state = "boss_intro"
        self.boss_intro_timer = S.BOSS_INTRO_TIME

    def _start_boss_fight(self):
        self.boss.intro = False
        self.boss.x = S.SCREEN_W // 2
        self.boss.y = S.BOSS_Y
        self.boss.fire_timer = 0.0
        self.wave_state = "boss"

    def _on_boss_dead(self):
        self.bosses_defeated += 1
        bx, by = self.boss.x, self.boss.y
        self.particles.burst(bx, by, S.C_BOSS_GLOW, 40, 220, 0.8, 4)
        self.particles.burst(bx, by, (255, 240, 180), 30, 280, 0.6, 3)
        self.flash = 0.25
        self.boss = None
        self.boss_bullets = []
        self.monsters = []
        if self.wave >= S.WAVE_TOTAL:
            self.wave_state = "done"
            self.state = "victory"
        else:
            self.wave += 1
            self.big_chest = None
            self._spawn_big_chest()
            self.wave_state = "active"
            self.spawned_count = 0
            self.spawn_timer = S.WAVE_SPAWN_INTERVAL
            self.wave_banner_timer = S.WAVE_BANNER_TIME
            self.wave_banner_wave = self.wave

    # ---------- 奖励 ----------
    def _break_chest(self, chest):
        chest.break_()
        self.global_level += 1
        self.chests_broken += 1
        r = random.random()
        if r < S.P_ATK:
            amt = S.attack_bonus(self.wave - 1)
            self.player.apply_attack(amt)
            msg, col = "攻击力 +%s" % ui._fmt_val(amt), S.C_GOLD
        else:
            self.player.apply_speed(self.global_level)
            msg, col = "攻速提升!", S.C_SHIP_CORE2
        self.floats.append(ui.FloatingText(chest.x, chest.y - 22, msg, col))
        self.particles.burst(chest.x, chest.y, S.C_CHEST_GLOW, 18, 150, 0.6, 3)

    def _break_big_chest(self, chest):
        self.big_chests_broken += 1
        atk_w = S.BIG_P_ATK
        spd_w = S.BIG_P_SPD
        shield_w = S.BIG_P_SHIELD if not self.player.all_shielded() else 0
        unit_w = S.BIG_P_UNIT
        invuln_w = S.BIG_P_INVULN if not self.player.invuln_item else 0
        atk_w += (S.BIG_P_SHIELD - shield_w) + (S.BIG_P_INVULN - invuln_w)
        weights = [("atk", atk_w), ("spd", spd_w)]
        if shield_w:
            weights.append(("shield", shield_w))
        weights.append(("unit", unit_w))
        if invuln_w:
            weights.append(("invuln", invuln_w))
        kinds = [k for k, _ in weights]
        ws = [w for _, w in weights]
        kind = random.choices(kinds, ws)[0]
        if kind == "atk":
            amt = 2 * S.attack_bonus(self.wave - 1)
            self.player.apply_attack(amt)
            msg, col = "攻击增幅! +%s" % ui._fmt_val(amt), S.C_GOLD
        elif kind == "spd":
            self.player.apply_speed(self.global_level, mult=2)
            msg, col = "超载火力!", S.C_SHIP_CORE2
        elif kind == "shield":
            self.player.add_shield_random()
            msg, col = "获得护盾!", S.C_SHIELD
        elif kind == "invuln":
            self.player.add_invuln_item()
            msg, col = "获得无敌!", S.C_INVULN_GOLD
        else:  # unit 分身道具（存入槽，右键释放）
            if self.player.add_clone_item():
                msg, col = "获得分身!", S.C_CLONE_GLOW
            else:
                amt = 2 * S.attack_bonus(self.wave - 1)
                self.player.apply_attack(amt)
                msg, col = "攻击增幅! +%s" % ui._fmt_val(amt), S.C_GOLD
        self.particles.burst(chest.x, chest.y, S.C_BIGCHEST_GLOW, 40, 220, 0.7, 4)
        self.flash = 0.18
        self.big_reward = (msg, col, 2.2)

    # ---------- 碰撞 ----------
    def _collisions(self):
        # 玩家子弹 vs BOSS（战斗中，含护盾卫星）
        if self.wave_state == "boss" and self.boss is not None and not self.boss.dead:
            for b in self.bullets:
                if b.y < -100:
                    continue
                # 先检测护盾卫星（终焉之主）
                if self.boss.has_shield() and self.boss.hit_satellite(b.x, b.y, b.damage):
                    self.particles.burst(b.x, b.y, (120, 200, 255), 6, 120, 0.3, 2)
                    self.shots_hit += 1
                    self.damage_dealt += b.damage
                    b.consumed = True
                    b.y = -999
                    continue
                if self.boss.hit_test(b.x, b.y):
                    deal = min(b.damage, self.boss.hp)
                    self.boss.hit(b.damage)
                    self.particles.burst(b.x, b.y, S.C_BOSS_GLOW, 6, 120, 0.3, 2)
                    self.shots_hit += 1
                    self.damage_dealt += deal
                    b.consumed = True
                    b.y = -999
                    if self.boss.dead:
                        break
        # 子弹 vs 大宝箱
        if self.big_chest is not None:
            c = self.big_chest
            if c.y + S.BIG_CHEST_SIZE // 2 > 0:
                for b in self.bullets:
                    if abs(b.x - c.x) <= S.BIG_CHEST_HIT_X \
                            and abs(b.y - c.y) <= S.BIG_CHEST_HIT_Y:
                        c.hit(b.damage)
                        self.shots_hit += 1
                        self.damage_dealt += min(b.damage, c.hp)
                        b.consumed = True
                        b.y = -999
                        if c.hp <= 0:
                            self._break_big_chest(c)
                            self.big_chest = None
                        break
        # 子弹 vs 宝箱（仅 active）
        if self.wave_state == "active":
            for b in self.bullets:
                for c in self.chests:
                    if c.alive and abs(b.x - c.x) <= S.CHEST_HIT_X \
                            and abs(b.y - c.y) <= S.CHEST_HIT_Y:
                        c.hit(b.damage)
                        self.shots_hit += 1
                        self.damage_dealt += min(b.damage, c.hp)
                        b.consumed = True
                        if c.hp <= 0:
                            self._break_chest(c)
                        b.y = -999
                        break
        # 子弹 vs 怪物
        for b in self.bullets:
            if b.y < -100:
                continue
            for m in self.monsters:
                if m.dead:
                    continue
                if m.rect().collidepoint(b.x, b.y):
                    m.hit(b.damage)
                    self.shots_hit += 1
                    self.damage_dealt += min(b.damage, m.hp)
                    b.consumed = True
                    if m.dead:
                        self.particles.burst(m.x, m.y, S.C_MON_GLOW, 16, 160, 0.5, 3)
                        self.kill_count += 1
                    b.y = -999
                    break
        # BOSS 子弹 vs 玩家
        if self.boss_bullets:
            py = self.player.y
            invuln = self.player.is_invincible()
            hit_any = False
            for b in self.boss_bullets:
                if b.dead:
                    continue
                if abs(b.y - py) <= 14:
                    hit_clone = False
                    if not invuln:
                        for cx in self.player.clone_positions():
                            if abs(b.x - cx) <= 16:
                                self.player.destroy_clone()
                                self.particles.burst(b.x, b.y, S.C_CLONE_GLOW,
                                                     14, 150, 0.5, 3)
                                b.dead = True
                                hit_clone = True
                                break
                    if hit_clone:
                        hit_any = True
                        continue
                    if not invuln:
                        for ux in self.player.unit_positions():
                            if abs(b.x - ux) <= 16:
                                self.player.kill_random_unit()
                                self.particles.burst(b.x, b.y, S.C_BOSS_BULLET,
                                                     14, 150, 0.5, 3)
                                b.dead = True
                                hit_any = True
                                break
            if hit_any:
                self.boss_bullets = [b for b in self.boss_bullets if not b.dead]
        # 怪物 vs 玩家单位
        py = self.player.y
        invuln = self.player.is_invincible()
        for m in list(self.monsters):
            if not m.dead and m.reached_player_line(py):
                if not invuln:
                    self.player.kill_random_unit()
                m.flash = 0.12
                m.dead = True
                self.particles.burst(self.player.x, py, S.C_SHIP_GLOW, 14, 150, 0.5, 3)
                self.particles.burst(m.x, m.y, S.C_MON_GLOW, 14, 150, 0.5, 3)
                self.monsters.remove(m)

    # ---------- 更新 ----------
    def update(self, dt):
        self.ui_t += dt
        # 调试按键计数窗口衰减
        if self.debug_timer > 0:
            self.debug_timer -= dt
            if self.debug_timer <= 0:
                self.debug_count = 0
        self.stars.update(dt)
        if self.state in ("menu", "help"):
            return
        if self.state != "playing":
            if self.state in ("gameover", "victory"):
                self.particles.update(dt)
                for f in self.floats:
                    f.update(dt)
                self.floats = [f for f in self.floats if f.life > 0]
                if self.flash > 0:
                    self.flash = max(0.0, self.flash - dt)
            return

        if self.wave_state == "boss_intro":
            self.boss_intro_timer -= dt
            self.boss.t += dt
            if self.boss_intro_timer <= 0:
                self._start_boss_fight()
            self.particles.update(dt)
            for f in self.floats:
                f.update(dt)
            self.floats = [f for f in self.floats if f.life > 0]
            return

        self.game_time += dt
        mx, _ = pygame.mouse.get_pos()
        self.player.follow_mouse(mx, dt)
        self.player.update(dt)

        if self.player.should_fire():
            for ux in self.player.unit_positions() + self.player.clone_positions():
                self.bullets.append(Bullet(ux, self.player.y - 10, self.player.attack))
                self.shots_fired += 1
                self.particles.spawn(ux, self.player.y + 6,
                                     random.uniform(-15, 15), random.uniform(40, 90),
                                     0.22, S.C_FLAME, 2, additive=True)

        for b in self.bullets:
            b.update(dt)
        # 统计自然飞出屏幕、未命中的子弹（丢失的伤害）
        for b in self.bullets:
            if b.off() and not b.consumed:
                self.damage_lost += b.damage
        self.bullets = [b for b in self.bullets if not b.off()]
        # BOSS 子弹（追踪弹需 player）
        for b in self.boss_bullets:
            b.update(dt, self.player)
        self.boss_bullets = [b for b in self.boss_bullets
                             if not b.off() and not b.dead]
        for m in self.monsters:
            m.update(dt)
        self.monsters = [m for m in self.monsters
                         if not m.dead and not m.off_screen()]
        if self.wave_state == "active":
            for c in self.chests:
                c.update(dt, self.wave)
        if self.big_chest is not None:
            self.big_chest.update(dt)
            if self.big_chest.off_bottom():
                self.big_chest = None
        self.particles.update(dt)
        for f in self.floats:
            f.update(dt)
        self.floats = [f for f in self.floats if f.life > 0]
        if self.wave_banner_timer > 0:
            self.wave_banner_timer = max(0.0, self.wave_banner_timer - dt)
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
        self.hud.update(dt, self.player, self.wave, self.global_level)

        if self.player.is_dead():
            self.state = "gameover"

    # ---------- 绘制 ----------
    def draw(self):
        self.screen.blit(self.bg, (0, 0))
        self.stars.draw(self.screen)

        if self.state == "menu":
            ui.draw_main_menu(self.screen, self.ui_t)
            return
        if self.state == "help":
            self.help_content_h = ui.draw_help_page(
                self.screen, self.help_page, self.help_scroll)
            return

        self.screen.blit(self.divider, (S.DIVIDER_X - 1, 0))
        if self.wave_state == "active":
            for c in self.chests:
                c.draw(self.screen, self.player.t)
        if self.big_chest is not None:
            self.big_chest.draw(self.screen, self.player.t)
        for m in self.monsters:
            m.draw(self.screen)
        for b in self.bullets:
            b.draw(self.screen, self.glow_out, self.glow_mid)
        if self.wave_state == "boss" and self.boss is not None:
            self.boss.draw(self.screen, self.boss.t)
        for b in self.boss_bullets:
            b.draw(self.screen, self.player.t)
        self.player.draw(self.screen)
        self.particles.draw(self.screen)
        for f in self.floats:
            f.draw(self.screen)

        if self.state == "playing" or self.state == "paused":
            self.hud.draw(self.screen, self.player, self.wave, self.global_level)
            ui.draw_pause_button(self.screen,
                                 ui.PAUSE_BTN.collidepoint(pygame.mouse.get_pos()))

        if self.wave_state == "boss_intro" and self.boss is not None:
            ui.draw_boss_intro(self.screen, self.boss.t)
            self.boss.draw(self.screen, self.boss.t)
            ui.draw_boss_intro_name(self.screen, self.boss.name, self.boss.phase,
                                    self.boss.t)
        elif self.wave_state == "boss" and self.boss is not None:
            self.boss.draw_hp_bar(self.screen)

        if self.wave_banner_timer > 0:
            a = 255 * (self.wave_banner_timer / S.WAVE_BANNER_TIME)
            ui.draw_wave_intro(self.screen, self.wave_banner_wave, a)
        if self.state == "paused":
            ui.draw_pause_overlay(self.screen)
        if self.state == "gameover":
            ui.draw_gameover(self.screen, self)
        if self.state == "victory":
            ui.draw_victory(self.screen, self)

        if self.flash > 0:
            a = min(255, int(200 * (self.flash / 0.18)))
            f = pygame.Surface((S.SCREEN_W, S.SCREEN_H), pygame.SRCALPHA)
            f.fill((255, 255, 255, a))
            self.screen.blit(f, (0, 0))

        if self.big_reward is not None and self.state == "playing":
            msg, col, _ = self.big_reward
            font = self.hud.big_font
            surf = font.render(msg, True, col)
            rect = surf.get_rect(center=(S.SCREEN_W // 2, S.SCREEN_H // 2 - 120))
            self.screen.blit(surf, rect)

        if self.state == "playing":
            ui.draw_item_slots(self.screen, self.player.invuln_item,
                               self.player.clone_item, self.player.t)
        if self.player.is_invincible() and self.state == "playing":
            ui.draw_invuln_border(self.screen, self.player.t)
        # 调试模式提示
        if self.debug_mode and self.state == "playing":
            tip = ui.get_font(14, bold=True).render(
                "调试模式  1-9/0/-跳关  P下一阶段  D(x6)退出", True, (255, 200, 80))
            self.screen.blit(tip, (10, S.SCREEN_H - 60))


def main():
    # 强制 print 实时输出（避免缓冲导致看不到调试日志）
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass
    pygame.init()
    try:
        screen = pygame.display.set_mode(
            (S.SCREEN_W, S.SCREEN_H),
            pygame.DOUBLEBUF | pygame.SCALED, vsync=1)
    except pygame.error:
        screen = pygame.display.set_mode((S.SCREEN_W, S.SCREEN_H))
    pygame.display.set_caption("%s  作者：%s" % (S.TITLE, S.AUTHOR))
    clock = pygame.time.Clock()
    game = Game(screen)
    fps_timer = 0.0

    while True:
        dt = min(clock.tick(S.FPS) / 1000.0, 0.05)

        fps_timer += dt
        if fps_timer >= 0.5:
            fps_timer = 0.0
            pygame.display.set_caption(
                "%s  作者：%s  FPS:%.0f" % (S.TITLE, S.AUTHOR, clock.get_fps()))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.ACTIVEEVENT:
                if game.state == "playing":
                    if event.gain == 0 and (event.state & 2 or event.state & 4):
                        game.state = "paused"
            elif event.type == pygame.KEYDOWN:
                print("[KEY] %d (%s) state=%s" % (event.key, pygame.key.name(event.key), game.state), flush=True)
                # 作弊码检测：累积字母输入，匹配 bosijiemao 触发 9999 秒无敌（v3.1.0）
                # 复用现有无敌机制（is_invincible 立即为真）；新一局 Player 重建即自动复位。
                if event.unicode and event.unicode.isalpha():
                    game.cheat_buf = (game.cheat_buf + event.unicode.lower())[-32:]
                    if game.cheat_buf.endswith("bosijiemao"):
                        game.player.invuln_timer = 9999
                        game.cheat_buf = ""
                # 调试模式：3 秒内连按 D 6 次（menu/playing/paused 可触发；help 下 D 用于翻页）
                if event.key == pygame.K_d and game.state != "help":
                    game.debug_count += 1
                    game.debug_timer = 3.0
                    print("[DEBUG] D pressed, count=%d/6, state=%s" % (game.debug_count, game.state))
                    if game.debug_count >= 6:
                        game.debug_mode = not game.debug_mode
                        game.debug_count = 0
                        print("[DEBUG] >>> debug_mode =", game.debug_mode)
                if event.key == pygame.K_ESCAPE:
                    if game.state == "playing":
                        game.state = "paused"
                    elif game.state == "paused":
                        game.state = "playing"
                # 调试模式生效：数字 1~9 跳对应波，0 跳第 10 波，
                # 减号跳第 11 波（噩梦），P 进入下一阶段
                if game.state == "playing" and game.debug_mode:
                    if pygame.K_1 <= event.key <= pygame.K_9:
                        game.jump_to_wave(event.key - pygame.K_0)
                        print("[DEBUG] jump to wave", game.wave)
                    elif event.key == pygame.K_0:
                        game.jump_to_wave(min(10, S.WAVE_TOTAL))
                        print("[DEBUG] jump to wave", game.wave)
                    elif event.key == pygame.K_MINUS and S.WAVE_TOTAL >= 11:
                        game.jump_to_wave(11)
                        print("[DEBUG] jump to wave 11")
                    elif event.key == pygame.K_p and game.boss is not None:
                        b = game.boss
                        if b.phase == 1:
                            b._p2 = False
                            b.hp = b.max_hp * (0.68 if S.BOSS_PHASES >= 3 else 0.48)
                            b.hit(0)
                            print("[DEBUG] boss %s -> phase 2" % b.name)
                        elif b.phase == 2 and S.BOSS_PHASES >= 3:
                            b._p3 = False
                            b.hp = b.max_hp * 0.38
                            b.hit(0)
                            print("[DEBUG] boss %s -> phase 3" % b.name)
                if game.state == "help":
                    if event.key in (pygame.K_LEFT, pygame.K_a):
                        game.help_page = (game.help_page - 1) % ui.DOC_PAGE_COUNT
                        game.help_scroll = 0
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        game.help_page = (game.help_page + 1) % ui.DOC_PAGE_COUNT
                        game.help_scroll = 0
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                if game.state == "menu":
                    for i, (key, name, desc, col) in enumerate(ui.MENU_ITEMS):
                        if ui.menu_btn_rect(i).collidepoint(mx, my):
                            if key == "help":
                                game.state = "help"
                                game.help_page = 0
                            else:
                                game.start_game(key)
                            break
                elif game.state == "help":
                    if ui.DOC_PREV_BTN.collidepoint(mx, my):
                        game.help_page = (game.help_page - 1) % ui.DOC_PAGE_COUNT
                        game.help_scroll = 0
                    elif ui.DOC_NEXT_BTN.collidepoint(mx, my):
                        game.help_page = (game.help_page + 1) % ui.DOC_PAGE_COUNT
                        game.help_scroll = 0
                    elif ui.DOC_BACK_BTN.collidepoint(mx, my):
                        game.state = "menu"
                    else:
                        # 滚动条拖动 / 点击轨道跳转
                        sl = ui.help_slider_rect(game.help_scroll, game.help_content_h)
                        track = ui.help_scrollbar_track_rect()
                        if sl and sl.collidepoint(mx, my):
                            game.help_dragging = True
                            game.help_drag_offset = my - sl.y
                        elif track.collidepoint(mx, my):
                            ms = ui.help_max_scroll(game.help_content_h)
                            if ms > 0:
                                sl_h = sl.h if sl else 34
                                usable = track.h - sl_h
                                if usable > 0:
                                    ratio = (my - track.y - sl_h / 2) / usable
                                    game.help_scroll = max(0, min(ms, int(ratio * ms)))
                                new_sl = ui.help_slider_rect(game.help_scroll,
                                                             game.help_content_h)
                                game.help_dragging = True
                                game.help_drag_offset = my - (new_sl.y if new_sl else 0)
                elif game.state in ("gameover", "victory"):
                    if ui.RESTART_BTN.collidepoint(mx, my):
                        game.start_game(game.difficulty)
                    elif ui.MENU_BACK_BTN.collidepoint(mx, my):
                        game.state = "menu"
                elif game.state == "paused":
                    if ui.RESUME_BTN.collidepoint(mx, my):
                        game.state = "playing"
                    elif ui.PAUSE_RESTART_BTN.collidepoint(mx, my):
                        game.start_game(game.difficulty)
                    elif ui.PAUSE_MENU_BTN.collidepoint(mx, my):
                        game.state = "menu"
                else:  # playing
                    if ui.PAUSE_BTN.collidepoint(mx, my):
                        game.state = "paused"
                    elif event.button == 1 and game.player.invuln_item \
                            and game.wave_state in ("active", "boss"):
                        # 左键使用无敌道具
                        game.player.use_invuln()
                    elif event.button == 3 and game.player.clone_item \
                            and game.wave_state in ("active", "boss"):
                        # 右键释放分身道具
                        game.player.use_clone()
            elif event.type == pygame.MOUSEMOTION:
                if game.state == "help" and game.help_dragging:
                    my = event.pos[1]
                    track = ui.help_scrollbar_track_rect()
                    ms = ui.help_max_scroll(game.help_content_h)
                    if ms > 0:
                        sl = ui.help_slider_rect(game.help_scroll, game.help_content_h)
                        sl_h = sl.h if sl else 34
                        usable = track.h - sl_h
                        if usable > 0:
                            ratio = (my - track.y - game.help_drag_offset) / usable
                            game.help_scroll = max(0, min(ms, int(ratio * ms)))
            elif event.type == pygame.MOUSEBUTTONUP:
                game.help_dragging = False
            elif event.type == pygame.MOUSEWHEEL:
                if game.state == "help":
                    ms = ui.help_max_scroll(game.help_content_h)
                    game.help_scroll = max(0, min(ms,
                                                  game.help_scroll - event.y * ui.SCROLL_STEP))

        game.update(dt)
        game.draw()
        pygame.display.flip()


if __name__ == "__main__":
    main()
