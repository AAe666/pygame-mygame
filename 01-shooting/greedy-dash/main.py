# -*- coding: utf-8 -*-
"""
Treasure Dash - 竖屏射击小游戏（主程序）
运行：python main.py
打包：venv/Scripts/python.exe -m PyInstaller GreedyDash.spec

玩法：
- 移动鼠标（或手指）控制单位队列左右平移（仅横向，Y 固定在底部）
- 自动向上射击：左侧打宝箱拿奖励，右侧打怪物求生存
- 技能：点击左上角「无敌 / 分身」图标释放（PC 也可用左键/右键任意处释放）
- ESC 暂停 / 继续，结束点按钮重开
- 主菜单选择难度：简单 / 普通 / 困难 / 噩梦
- 移动端：虚拟分辨率宽度固定 480，高度按设备宽高比自适应（铺满长屏零黑边），等比缩放触摸自动识别
"""
import math
import os
import random
import sys
import traceback
import faulthandler

# ---------- 启动诊断：原生层崩溃(SIGSEGV/Abort)也能把 Python 栈打到 logcat ----------
_BOOT_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "boot.log")


def _log(msg):
    """同时写 boot.log 与 stdout（p4a 中 stdout -> logcat，无线调试可见）。"""
    try:
        with open(_BOOT_LOG, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass
    try:
        sys.stdout.write(msg + "\n")
        sys.stdout.flush()
    except Exception:
        pass


# 注意：p4a(Android) 把 sys.stderr 重定向到 logcat，它没有真实 fileno；
# faulthandler.enable() 无参时会取 sys.stderr.fileno()，在 Android 上抛
# io.UnsupportedOperation: fileno。故传入一个真实文件对象，崩溃栈落盘到 fault.log。
_fault_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fault.log")
_fault_fh = open(_fault_path, "a", encoding="utf-8")
faulthandler.enable(file=_fault_fh)  # C 层崩溃时把 Python 调用栈写入 fault.log
_log("boot: faulthandler enabled")


def _excepthook_top(exc_type, exc_val, exc_tb):
    """模块级兜底：import 阶段 / 进入 main 之前的 Python 异常也能落盘，便于无数据线排查。"""
    text = "".join(traceback.format_exception(exc_type, exc_val, exc_tb))
    _log("FATAL (pre-main):\n" + text)
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "crash.log"),
                  "w", encoding="utf-8") as f:
            f.write(text)
    except Exception:
        pass


sys.excepthook = _excepthook_top

import pygame
_log("boot: pygame imported")

import settings as S
from player import Player, _glow, _glow_alpha
from enemy import Chest, Monster, BigChest
from boss import make_boss
from particle import ParticleSystem, StarField
import ui
_log("boot: all game modules imported")


# ---------- 显示抽象：虚拟分辨率 -> 真实屏幕（等比铺满）----------
# 游戏以宽度 480、高度自适应的虚拟表面绘制：PC 固定 480x720；手机端启动时
# 按设备宽高比算出的高度（_apply_virtual_height），使虚拟比例 = 设备比例，
# 等比缩放后铺满全屏、零黑边，且模型始终等比不变形。输入坐标经 to_virtual 换算。
VW, VH = S.SCREEN_W, S.SCREEN_H
# 触摸事件常量（部分平台无此属性，用 getattr 兼容）
FINGERDOWN = getattr(pygame, "FINGERDOWN", -1)


class View:
    """虚拟表面（固定 480x720，与 PC 同比例）到真实屏幕的等比缩放/坐标换算。
    手机长屏（比例比 2:3 更瘦高）下：游戏按原始比例居中铺满宽度，
    上下多余区域（信箱黑边）由 _draw_frame 用主题装饰填充，而非纯黑。"""

    def __init__(self, real):
        self.real = real
        self._play_buf = None       # 缩放后的游戏画面缓存（仅信箱化时用到）
        self._bar_pattern = None    # 黑边装饰点阵（按窗口宽重建）
        self._title = None
        self._author = None
        self.recompute(real.get_size())

    def recompute(self, size):
        self.w, self.h = size
        self.scale = min(self.w / VW, self.h / VH) or 1.0
        self.dx = (self.w - VW * self.scale) / 2.0
        self.dy = (self.h - VH * self.scale) / 2.0
        self._build_decor()

    def to_virtual(self, px, py):
        return ((px - self.dx) / self.scale, (py - self.dy) / self.scale)

    def _build_decor(self):
        """构建黑边装饰。PC 用原深紫渐变+宝石点阵 tile；Android 用太空背景
        （整张预渲染，每帧一次 blit）。用确定性随机不扰动游戏序列。"""
        w, h = self.w, self.h
        is_android = "ANDROID_ARGUMENT" in os.environ
        if is_android:
            # Android：太空背景（整张 real 尺寸预渲染，每帧只 blit 一次）
            bg = pygame.Surface((w, h))
            top, bot = (12, 8, 32), (2, 2, 12)
            for y in range(h):
                t = y / h
                col = (int(top[0] + (bot[0] - top[0]) * t),
                       int(top[1] + (bot[1] - top[1]) * t),
                       int(top[2] + (bot[2] - top[2]) * t))
                pygame.draw.line(bg, col, (0, y), (w, y))
            rng = random.Random(20260724)
            star_count = max(40, int(w * h / 550))
            for _ in range(star_count):
                x = rng.randint(0, w - 1)
                y = rng.randint(0, h - 1)
                b = rng.randint(80, 230)
                r = 1 if rng.random() > 0.12 else 2
                pygame.draw.circle(bg, (b, b, min(255, b + 25)), (x, y), r)
            self._space_bg = bg
        else:
            # PC：原深紫渐变 + 宝石点阵 tile（不改）
            tile = pygame.Surface((w, 40))
            top, bot = (26, 16, 48), (10, 12, 30)
            for y in range(40):
                t = y / 40.0
                col = (int(top[0] + (bot[0] - top[0]) * t),
                       int(top[1] + (bot[1] - top[1]) * t),
                       int(top[2] + (bot[2] - top[2]) * t))
                pygame.draw.line(tile, col, (0, y), (w, y))
            gem_cols = ((255, 210, 90), (255, 120, 150), (120, 200, 255), (200, 120, 255))
            for row in range(4):
                yy = 6 + row * 11
                off = (row * 23) % 92
                for gx in range(off, w, 92):
                    c = gem_cols[(gx // 92 + row) % len(gem_cols)]
                    r = 1 if (gx // 92) % 3 else 2
                    pygame.draw.circle(tile, c, (gx, yy), r)
            self._bar_pattern = tile
        self._title = ui.get_font(min(34, w // 12), bold=True).render(
            "GREEDY DASH", True, (255, 230, 255))
        self._author = ui.get_font(14).render("作者：%s" % S.AUTHOR, True, S.C_TEXT_DIM)

    def _draw_frame(self, dx, dy, sw, sh):
        """铺装饰（PC 循环 tile / Android 一次 blit 太空背景），游戏区加科幻描边。"""
        real = self.real
        if hasattr(self, '_space_bg'):
            real.blit(self._space_bg, (0, 0))
        else:
            yy = 0
            while yy < self.h:
                real.blit(self._bar_pattern, (0, yy))
                yy += 40
        pygame.draw.rect(real, S.C_DIVIDER, (dx - 1, dy - 1, sw + 2, sh + 2), 1)
        if dy >= 40:
            real.blit(self._title, self._title.get_rect(center=(self.w // 2, dy // 2)))
        if dy >= 26:
            if hasattr(self, '_space_bg'):
                real.blit(self._author, self._author.get_rect(
                    midright=(self.w - 12, self.h - dy // 2)))
            else:
                real.blit(self._author, self._author.get_rect(
                    center=(self.w // 2, self.h - dy // 2)))

    def present(self, virtual):
        dx = int(round(self.dx))
        dy = int(round(self.dy))
        sw = int(round(VW * self.scale))
        sh = int(round(VH * self.scale))
        if sw == self.w and sh == self.h:
            # 无黑边：直接铺满（1:1 或等比缩放）
            if abs(self.scale - 1.0) < 1e-6:
                self.real.blit(virtual, (0, 0))
            else:
                pygame.transform.scale(virtual, (self.w, self.h), self.real)
            return
        # 信箱化（手机长屏上下黑边）：太空背景填充 + 游戏区居中
        self._draw_frame(dx, dy, sw, sh)
        if sw == VW and sh == VH:
            # scale=1：直接 blit，省去 transform.scale 的逐像素拷贝
            self.real.blit(virtual, (dx, dy))
        else:
            if self._play_buf is None or self._play_buf.get_size() != (sw, sh):
                self._play_buf = pygame.Surface((sw, sh))
            pygame.transform.scale(virtual, (sw, sh), self._play_buf)
            self.real.blit(self._play_buf, (dx, dy))


# ---------- 安卓端虚拟高度自适应 ----------
def _apply_virtual_height(vh):
    """手机端：把虚拟画布高度设为 vh（由设备宽高比算出），使等比缩放后铺满
    全屏、零黑边；模型始终等比缩放不变形。同时重算 ui 模块里在 import 时
    用旧 SCREEN_H 算好的矩形常量，避免布局错位。"""
    global VW, VH
    VH = vh
    S.SCREEN_H = vh
    ui.RESUME_BTN = pygame.Rect(S.SCREEN_W // 2 - 110, S.SCREEN_H // 2 - 100, 220, 50)
    ui.PAUSE_RESTART_BTN = pygame.Rect(S.SCREEN_W // 2 - 110, S.SCREEN_H // 2 - 40, 220, 50)
    ui.PAUSE_MENU_BTN = pygame.Rect(S.SCREEN_W // 2 - 110, S.SCREEN_H // 2 + 20, 220, 50)
    ui.DOC_BTN_Y = S.SCREEN_H - 46
    ui.DOC_PREV_BTN = pygame.Rect(40, ui.DOC_BTN_Y, 90, 32)
    ui.DOC_NEXT_BTN = pygame.Rect(S.SCREEN_W - 130, ui.DOC_BTN_Y, 90, 32)
    ui.DOC_BACK_BTN = pygame.Rect(S.SCREEN_W // 2 - 60, ui.DOC_BTN_Y, 120, 32)
    ui.HELP_CONTENT_BOTTOM = ui.DOC_BTN_Y - 12
    ui.HELP_CONTENT_H = ui.HELP_CONTENT_BOTTOM - ui.HELP_CONTENT_TOP
    ui.RESTART_BTN = pygame.Rect(S.SCREEN_W // 2 - 230, S.SCREEN_H - 130, 220, 50)
    ui.MENU_BACK_BTN = pygame.Rect(S.SCREEN_W // 2 + 10, S.SCREEN_H - 130, 220, 50)


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
        self.touch_mode = False     # 触屏设备（安卓）下设为 True，切换技能释放方式
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
        self._flash_buf = pygame.Surface((S.SCREEN_W, S.SCREEN_H), pygame.SRCALPHA)
        self._intro_frames = None  # BOSS 过场预渲染帧列表（5 档脉冲，每帧纯 opaque blit）
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
        self._intro_frames = None  # 新 BOSS 需重新渲染过场帧
        self.wave_state = "boss_intro"
        self.boss_intro_timer = S.BOSS_INTRO_TIME

    def _build_intro_frames(self):
        """预渲染 5 帧光晕背景（暗底+分割线+脉冲光晕），BOSS 本体每帧实时画保证动画。"""
        layers = ((150, (180, 40, 120)), (100, (255, 80, 150)), (60, (255, 200, 200)))
        cx, cy = S.SCREEN_W // 2, S.SCREEN_H // 2 - 20
        # 暗底 + 分割线
        base = pygame.Surface((S.SCREEN_W, S.SCREEN_H))
        base.fill((8, 4, 18))
        base.blit(self.divider, (S.DIVIDER_X - 1, 0))
        # 构建 5 帧（脉冲量化 5 档），光晕用 alpha 合成烘焙进去
        self._intro_frames = []
        for q in range(5):
            pulse = 0.82 + q * 0.09
            frame = base.copy()
            for base_r, col in layers:
                glows = ui._INTRO_GLOW_CACHE.get(base_r)
                if glows is None:
                    glows = []
                    for pct in (82, 90, 98, 106, 114):
                        r = max(2, int(base_r * pct / 100))
                        g = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
                        for rr in range(r, 0, -2):
                            a = int(70 * (1 - rr / r))
                            pygame.draw.circle(g, (*col, a), (r, r), rr)
                        glows.append((r, g))
                    ui._INTRO_GLOW_CACHE[base_r] = glows
                idx = int((pulse - 0.82) / 0.36 * len(glows))
                idx = max(0, min(len(glows) - 1, idx))
                r, g = glows[idx]
                frame.blit(g, (int(cx - r), int(cy - r)))
            self._intro_frames.append(frame)

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
        mx, my = ui._mouse
        # Android：道具槽区域（左上角）不跟随鼠标，避免点击道具释放时玩家飘到道具 x 位置
        if not ("ANDROID_ARGUMENT" in os.environ and mx < 55 and my < 130):
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
        # BOSS 过场：烘焙背景（暗底+分割线+光晕）+ 实时 BOSS 动画 + 文字
        if self.wave_state == "boss_intro" and self.boss is not None:
            if self._intro_frames is None:
                self._build_intro_frames()
            pulse = 1 + 0.18 * math.sin(self.boss.t * 4)
            q = int((pulse - 0.82) / 0.36 * 4 + 0.5)
            q = max(0, min(4, q))
            self.screen.blit(self._intro_frames[q], (0, 0))
            self.boss.draw(self.screen, self.boss.t)
            ui.draw_boss_intro_name(self.screen, self.boss.name, self.boss.phase,
                                    self.boss.t)
            return

        self.screen.blit(self.bg, (0, 0))
        self.stars.draw(self.screen)

        if self.state == "menu":
            ui.draw_main_menu_fast(self.screen, self.ui_t)
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
            self.hud.draw(self.screen, self.player, self.wave, self.global_level, self.touch_mode)
            ui.draw_pause_button(self.screen,
                                 ui.PAUSE_BTN.collidepoint(ui._mouse))

        if self.wave_state == "boss" and self.boss is not None:
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
            self._flash_buf.fill((255, 255, 255, a))
            self.screen.blit(self._flash_buf, (0, 0))

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


def show_error(real, exc):
    """未捕获异常时把 traceback 画到 SDL 窗口上，方便无数据线排查。"""
    text = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "crash.log"), "w", encoding="utf-8") as f:
            f.write(text)
    except Exception:
        pass
    print("===== CRASH TRACEBACK =====")
    print(text)
    if real is None:
        return
    f = pygame.font.Font(None, 22)   # 默认字体，避免依赖内置中文字体
    lines = text.strip().splitlines()[-60:]
    clock = pygame.time.Clock()
    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if ev.type == getattr(pygame, "FINGERDOWN", -1) or ev.type == pygame.MOUSEBUTTONDOWN:
                pygame.quit(); sys.exit()
        w, h = real.get_size()
        surf = pygame.Surface((w, h))
        surf.fill((30, 0, 0))
        y = 12
        for ln in lines:
            for i in range(0, len(ln), 70):
                chunk = ln[i:i + 70]
                surf.blit(f.render(chunk, True, (255, 210, 210)), (10, y))
                y += 26
                if y > h - 20:
                    break
            if y > h - 20:
                break
        real.blit(surf, (0, 0))
        pygame.display.flip()
        clock.tick(15)


def main():
    # 强制 print 实时输出（避免缓冲导致看不到调试日志）
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass
    pygame.init()
    _log("boot: pygame.init ok")
    IS_ANDROID = "ANDROID_ARGUMENT" in os.environ
    print("[BOOT] ANDROID_ARGUMENT =", os.environ.get("ANDROID_ARGUMENT"), flush=True)

    # 未捕获异常时把 traceback 画到屏幕上（Android 无数据线也能看到报错）。
    # 必须在 set_mode 之前安装，否则初始化阶段抛错也抓不到（表现为启动即闪退）。
    _real_holder = {"real": None}
    def _excepthook(exc_type, exc_val, exc_tb):
        show_error(_real_holder["real"], exc_val)
    sys.excepthook = _excepthook

    if IS_ANDROID:
        # SCALED + GPU 缩放。关键：用「实际窗口物理尺寸」(get_window_size) 而非
        # 桌面分辨率 (get_desktop_sizes) 来算 real surface 高度——后者含状态栏，
        # 比例不匹配会导致 SDL letterbox 产生左右纯黑边（游戏被缩小居中）。
        # 先 probe 一次拿到实际窗口尺寸，再用匹配比例的尺寸重新 set_mode。
        try:
            pygame.display.set_mode((VW, VH), pygame.SCALED)
            pw, ph = pygame.display.get_window_size()
            print("[BOOT] window physical=%dx%d" % (pw, ph), flush=True)
        except Exception as e:
            print("[BOOT] probe failed (%s)" % e, flush=True)
            pw, ph = 1440, 2867
        # 防止横竖反转
        if pw > ph:
            pw, ph = ph, pw
        real_h = int(VW * ph / pw)
        print("[BOOT] window %dx%d -> real surface %dx%d"
              % (pw, ph, VW, real_h), flush=True)
        try:
            real = pygame.display.set_mode((VW, real_h), pygame.SCALED)
            print("[BOOT] SCALED ok, surface=%s" % (real.get_size(),), flush=True)
        except Exception as e:
            print("[BOOT] SCALED failed (%s), fallback FULLSCREEN" % e, flush=True)
            real = pygame.display.set_mode((VW, real_h), pygame.FULLSCREEN)
    else:
        # PC：窗口 480x720，可拖拽放大（放大后信箱化保持比例），不改
        real = pygame.display.set_mode((VW, VH), pygame.DOUBLEBUF | pygame.RESIZABLE)
    _real_holder["real"] = real
    print("[BOOT] real surface size =", real.get_size(), flush=True)
    _log("boot: set_mode ok")

    virtual = pygame.Surface((VW, VH))
    view = View(real)
    pygame.display.set_caption("%s  作者：%s" % (S.TITLE, S.AUTHOR))
    clock = pygame.time.Clock()
    fps_font = ui.get_font(13)
    game = Game(virtual)
    _log("boot: Game created")
    fps_timer = 0.0
    fps_surf = None       # Android：缓存 FPS 文字 surface（下黑边显示，0.25s 更新）

    _log("boot: entering main loop")
    while True:
        dt = min(clock.tick(S.FPS) / 1000.0, 0.05)

        if IS_ANDROID:
            # Android：0.25s 缓存 FPS surface 供下黑边显示
            fps_timer += dt
            if fps_timer >= 0.25:
                fps_timer = 0.0
                fps_surf = fps_font.render("FPS %.0f" % clock.get_fps(), True, (150, 210, 255))
        else:
            # PC：原 0.5s 更新 caption（不改）
            fps_timer += dt
            if fps_timer >= 0.5:
                fps_timer = 0.0
                pygame.display.set_caption(
                    "%s  作者：%s  FPS:%.0f" % (S.TITLE, S.AUTHOR, clock.get_fps()))

        # 真实鼠标/触摸坐标 -> 虚拟坐标，供 update 与绘制使用
        rx, ry = pygame.mouse.get_pos()
        vx, vy = view.to_virtual(rx, ry)
        ui.set_mouse_pos(vx, vy)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.ACTIVEEVENT:
                if game.state == "playing":
                    if event.gain == 0 and (event.state & 2 or event.state & 4):
                        game.state = "paused"
            elif event.type == FINGERDOWN:
                # 触屏设备：切换到触摸操作模式（技能改点图标释放）
                game.touch_mode = True
            elif event.type == pygame.VIDEORESIZE:
                view.recompute((event.w, event.h))
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
                mx, my = view.to_virtual(*event.pos)
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
                    elif ui.invuln_slot_rect().collidepoint(mx, my) \
                            and game.player.invuln_item \
                            and game.wave_state in ("active", "boss"):
                        # 点左上角无敌图标释放（PC/手机通用）
                        game.player.use_invuln()
                    elif ui.clone_slot_rect().collidepoint(mx, my) \
                            and game.player.clone_item \
                            and game.wave_state in ("active", "boss"):
                        # 点左上角分身图标释放（PC/手机通用）
                        game.player.use_clone()
                    elif not game.touch_mode and event.button == 1 \
                            and game.player.invuln_item \
                            and game.wave_state in ("active", "boss"):
                        # PC 兼容：左键任意处放无敌
                        game.player.use_invuln()
                    elif not game.touch_mode and event.button == 3 \
                            and game.player.clone_item \
                            and game.wave_state in ("active", "boss"):
                        # PC 兼容：右键任意处分身
                        game.player.use_clone()
            elif event.type == pygame.MOUSEMOTION:
                if game.state == "help" and game.help_dragging:
                    _, my = view.to_virtual(*event.pos)
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
        if not IS_ANDROID and game.state == "playing":
            # PC：原 FPS 诊断浮层在 virtual 左下角（不改）
            _fs = fps_font.render("FPS %.0f" % clock.get_fps(), True, (150, 210, 255))
            virtual.blit(_fs, (6, S.SCREEN_H - 18))
        view.present(virtual)
        if IS_ANDROID:
            if fps_surf is not None and view.dy >= 20:
                # Android：FPS 显示在下黑边左侧（太空背景区域）
                real.blit(fps_surf, (12, int(view.h - view.dy / 2) - fps_surf.get_height() // 2))
        pygame.display.flip()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # main 未进入（如 pygame.init C 层崩溃）或 show_error 自身异常时的兜底
        show_error(None, e)
