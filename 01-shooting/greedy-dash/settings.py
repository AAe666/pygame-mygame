# -*- coding: utf-8 -*-
"""
Treasure Dash - 全局配置与常量
所有图形均由 pygame.draw / pygame.gfxdraw 绘制，颜色统一用 RGB 元组定义。
"""

# ---------- 窗口与基础 ----------
SCREEN_W = 480          # 竖屏宽度
SCREEN_H = 720          # 竖屏高度
FPS = 60                # 锁定帧率
TITLE = "Greedy Dash"
DIVIDER_X = SCREEN_W // 2   # 中央垂直分割线 x 坐标 (240)：左=宝箱区，右=怪物区

# ---------- 颜色 (RGB 元组) ----------
# 背景渐变（深紫 -> 深蓝）
C_BG_TOP = (42, 22, 74)
C_BG_BOTTOM = (14, 18, 58)
C_DIVIDER = (185, 85, 255)      # 亮紫分割线

# 暂停 UI
C_PAUSE_ICON = (235, 235, 245)  # 暂停图标（白）
C_OVERLAY = (0, 0, 0)           # 暂停遮罩（黑）
C_RESUME_BORDER = (120, 220, 255)   # 继续按钮科幻边框
C_PLAY_TRI = (255, 255, 255)        # 播放三角

# 玩家飞船（青蓝色调）
C_SHIP_CORE = (0, 200, 255)
C_SHIP_CORE2 = (120, 235, 255)
C_SHIP_EDGE = (255, 255, 255)   # 白色描边
C_SHIP_GLOW = (0, 180, 255)     # 本体光晕
C_CLONE_GLOW = (150, 110, 255)  # 分身蓝紫光晕
C_FLAME = (255, 170, 60)        # 尾焰

# 宝箱（暖金色）
C_CHEST_BODY = (200, 150, 50)
C_CHEST_LID = (255, 205, 90)
C_CHEST_EDGE = (120, 80, 20)
C_CHEST_GEM = (255, 90, 130)
C_CHEST_GLOW = (255, 200, 70)
C_CHEST_HP_BG = (60, 60, 60)
C_CHEST_HP = (90, 230, 90)

# 怪物（暗紫红多刺）
C_MON_BODY = (120, 32, 70)
C_MON_EDGE = (60, 12, 35)
C_MON_GLOW = (200, 45, 45)      # 红色边缘光晕
C_MON_EYE = (255, 210, 110)     # 发光眼睛
C_MON_HP_BG = (90, 20, 20)
C_MON_HP = (255, 150, 40)

# 子弹（三层光球）
C_BULLET_OUT = (0, 255, 255)    # 外层半透明青
C_BULLET_MID = (255, 255, 255)  # 中层半透明白
C_BULLET_CORE = (255, 255, 255) # 核心纯白

# 文本
C_TEXT = (235, 235, 245)
C_TEXT_DIM = (150, 150, 170)
C_GOLD = (255, 210, 90)

# ---------- 玩家 ----------
PLAYER_Y = SCREEN_H - 40       # 玩家单位中心 y（底部）
UNIT_W = 32
UNIT_H = 20
UNIT_SPACING = 36              # 单位中心间距（水平队列）
ATTACK_BASE = 1                # 初始攻击力（每颗子弹伤害）
FIRE_INTERVAL_BASE = 0.3       # 初始射击间隔（秒）≈ 3.3 发/秒
MAX_UNITS = 4                  # 单位数量上限（含本体）

# ---------- 宝箱系统 ----------
CHEST_COUNT = 10
CHEST_SIZE = 26
CHEST_RESPAWN = 5.0            # 击破后重生延迟（秒）
CHEST_TOP_MARGIN = 60          # 顶部留白
CHEST_BOTTOM_AVOID = 120       # 底部避让区域（避免与玩家重叠）
CHEST_X = 70                   # 宝箱列 x 中心（左侧）
# 小宝箱血量 = 怪物血量 × 5（多项式增长，见 chest_hp）
# 大宝箱血量 = 怪物血量 × BIG_CHEST_HP_MULT（默认 12）
# 大宝箱（分割线左边右半部分生成，最多 1 个）
BIG_CHEST_SIZE = 46            # 包围盒边长
BIG_CHEST_SPEED = 40            # 下落速度 px/s（缓慢）
BIG_CHEST_HP_MULT = 12        # 血量 = 当前波怪物血量 * 12
BIG_CHEST_HIT_X = 30           # 命中半宽（比小宝箱宽，便于命中）
BIG_CHEST_HIT_Y = 28
# 大宝箱配色（豪华金红）
C_BIGCHEST_BODY = (150, 40, 40)
C_BIGCHEST_LID = (255, 210, 120)
C_BIGCHEST_EDGE = (120, 30, 30)
C_BIGCHEST_GEM = (255, 220, 120)
C_BIGCHEST_GLOW = (255, 170, 60)
C_BIGCHEST_RING = (255, 220, 140)   # 旋转光环
# 宝箱命中容差（让多单位时偏离中心的子弹也能命中，避免偶数单位全部打空）
CHEST_HIT_X = 22                # 横向命中半宽（宝箱视觉半宽 13，放宽到 22）
CHEST_HIT_Y = 16                # 纵向命中半高（宝箱视觉半高 13，放宽到 16）
C_SHIELD = (120, 200, 255)      # 护盾淡蓝保护罩

# 小宝箱奖励概率（不再出分身）
P_ATK = 0.70       # 攻击力
P_SPD = 0.30       # 攻速
# 大宝箱奖励概率（护盾满时其 15% 并入攻击增幅）
BIG_P_ATK = 40        # 攻击增幅
BIG_P_SPD = 25        # 超载火力
BIG_P_SHIELD = 15     # 护盾
BIG_P_UNIT = 20       # 分身

# ---------- 怪物 / 波次 ----------
MONSTER_SPEED = 80             # 下落速度 px/s
# 每波怪物数（随波数递增）：第 n 波 = 8 + (n-1)*2
MONSTER_COUNT_BASE = 8
MONSTER_COUNT_STEP = 2
WAVE_SPAWN_INTERVAL = 0.8      # 同波内生成间隔（秒）
WAVE_BANNER_TIME = 3.0         # 波次提示持续时间（秒，淡退；非阻塞，不影响出怪）
MONSTER_HP_BASE = 2            # 第 1 波怪物血量（固定，不随难度变化）
# 难度递增：第 1 波不变；第 2 波起血量乘以系数 1 + DIFFICULTY_STEP*(波次-1)
DIFFICULTY_STEP = 0.6          # 每波血量乘数增量（第 2 波 +60%，第 3 波 +120%...）
MONSTER_W = 32
MONSTER_H = 32
# 并排成群生成：5% 三个并排 / 10% 两个并排 / 85% 单个（空间不足时自动降级）
MONSTER_GROUP_SPACING = 40     # 并排单位中心间距（略大于怪物宽度）
MONSTER_P_TRIPLE = 0.05        # 三个并排概率
MONSTER_P_DOUBLE = 0.10        # 两个并排概率
MONSTER_SPAWN_MARGIN = 24      # 生成区左右留白（距分割线/右边界）

# ---------- 子弹 ----------
BULLET_SPEED = 620             # 子弹上行速度 px/s
BULLET_TRAIL = 5               # 拖尾残影帧数

# ---------- 粒子 ----------
STAR_COUNT = 50                # 背景星光数量

# ---------- 数值递推公式（宝箱/怪物血量、怪物数量）----------
def chest_hp(wave):
    """小宝箱血量（随波数多项式增长）：= 怪物血量 × 5。
    第1波=10，第7波=1010，避免指数爆炸。
    """
    return int(round(monster_hp(wave) * 5))


def monster_count(wave):
    """每波怪物数：8 + (波数-1) * 2。"""
    return MONSTER_COUNT_BASE + (wave - 1) * MONSTER_COUNT_STEP


def monster_hp(wave):
    """每波怪物血量（二次增长 + 难度系数）。
    第 1 波 = 2（固定不变）；第 2 波起乘以难度系数：
    HP(w) = (2 + (w-1) + (w-1)²) × (1 + DIFFICULTY_STEP*(w-1))
    第 1 波=2，第 7 波≈202。
    """
    d = wave - 1
    base = MONSTER_HP_BASE + d + d * d
    scale = 1.0 + DIFFICULTY_STEP * d
    return int(round(base * scale))


def attack_bonus(tier):
    """小宝箱攻击力增量序列（tier 从 0 起）：
    1, 2, 4, 7, 11, 16, 22, ...（相邻差值 1,2,3,4,5,6...）
    即 1 + tier*(tier+1)/2。
    """
    return 1 + tier * (tier + 1) // 2
