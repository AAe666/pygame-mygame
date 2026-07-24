# -*- coding: utf-8 -*-
"""
Treasure Dash - 全局配置与常量
所有图形均由 pygame.draw / pygame.gfxdraw 绘制，颜色统一用 RGB 元组定义。
"""

# ---------- 窗口与基础 ----------
SCREEN_W = 480          # 竖屏宽度
SCREEN_H = 720          # 竖屏高度（PC 默认；手机端启动时按设备比例自适应拉高铺满）
FPS = 60                # 锁定帧率
TITLE = "Greedy Dash"
AUTHOR = "波斯睫毛"
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
C_BULLET_CORE = (255, 255, 255)  # 核心纯白

# 文本
C_TEXT = (235, 235, 245)
C_TEXT_DIM = (150, 150, 170)
C_GOLD = (255, 210, 90)

# ---------- 玩家 ----------
PLAYER_BOTTOM_GAP = 40         # 玩家单位中心距屏幕底部间距（单位始终贴底）
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
# 大宝箱奖励概率（护盾满时其 15% 并入攻击增幅；金身已持有时其 15% 并入攻击增幅）
BIG_P_ATK = 25        # 攻击增幅
BIG_P_SPD = 25        # 超载火力
BIG_P_SHIELD = 15     # 护盾
BIG_P_UNIT = 20       # 临时分身（持续 3 秒）
BIG_P_INVULN = 15     # 金身（无敌 1 秒道具）

# ---------- 难度系统 ----------
# 四难度参数表。差异仅在三处：怪物血量曲线(lin/quad)、总波数(waves)、BOSS阶段数(phases)。
# 其余参数（怪物基础数量/步进、BOSS血量倍率、玩家射速、BOSS子弹速度等）四难度完全一致。
DIFFICULTY_PARAMS = {
    "easy":      {"lin": 0.45, "quad": 0.15, "waves": 10, "phases": 2,
                  "boss_mult": 100, "name": "简单",
                  "desc": "怪物更脆，BOSS 仅二阶段"},
    "normal":    {"lin": 0.6,  "quad": 0.2,  "waves": 10, "phases": 2,
                  "boss_mult": 140, "name": "普通",
                  "desc": "标准难度，BOSS 仅二阶段"},
    "hard":      {"lin": 0.75, "quad": 0.25, "waves": 10, "phases": 3,
                  "boss_mult": 170, "name": "困难",
                  "desc": "怪物更强，BOSS 三阶段"},
    "nightmare": {"lin": 0.9,  "quad": 0.32, "waves": 11, "phases": 3,
                  "boss_mult": 200, "name": "噩梦",
                  "desc": "怪物极强，11 关含压轴 BOSS，三阶段"},
}
DIFFICULTY_ORDER = ["easy", "normal", "hard", "nightmare"]

# 当前难度（运行时由主菜单设置；默认普通）
CURRENT_DIFFICULTY = "normal"
DIFFICULTY_LIN = 0.6           # 线性项（由 set_difficulty 更新）
DIFFICULTY_QUAD = 0.2          # 二次项（由 set_difficulty 更新）
WAVE_TOTAL = 10                # 总波数（由 set_difficulty 更新）
BOSS_PHASES = 2                # BOSS 阶段数：2 或 3（由 set_difficulty 更新）
BOSS_HP_MULT = 100             # BOSS 血量倍率（由 set_difficulty 按难度更新）

# BOSS 阶段触发血量阈值
PHASE2_THRESHOLD_2P = 0.50     # 二阶段难度（简单/普通）：50% 触发二阶段
PHASE2_THRESHOLD_3P = 0.70     # 三阶段难度（困难/噩梦）：70% 触发二阶段
PHASE3_THRESHOLD = 0.40        # 三阶段难度：40% 触发三阶段


def set_difficulty(d):
    """设置当前难度，更新全局难度相关变量。"""
    global CURRENT_DIFFICULTY, DIFFICULTY_LIN, DIFFICULTY_QUAD, WAVE_TOTAL, BOSS_PHASES
    global BOSS_HP_MULT
    p = DIFFICULTY_PARAMS[d]
    CURRENT_DIFFICULTY = d
    DIFFICULTY_LIN = p["lin"]
    DIFFICULTY_QUAD = p["quad"]
    WAVE_TOTAL = p["waves"]
    BOSS_PHASES = p["phases"]
    BOSS_HP_MULT = p["boss_mult"]


def difficulty_name(d=None):
    return DIFFICULTY_PARAMS[d or CURRENT_DIFFICULTY]["name"]


# ---------- 怪物 / 波次 ----------
MONSTER_SPEED = 80             # 下落速度 px/s
# 每波怪物数（随波数递增）：第 n 波 = 12 + (n-1)*2（四难度一致）
MONSTER_COUNT_BASE = 12
MONSTER_COUNT_STEP = 2
WAVE_SPAWN_INTERVAL = 0.8      # 同波内生成间隔（秒）
WAVE_BANNER_TIME = 3.0         # 波次提示持续时间（秒，淡退；非阻塞，不影响出怪）
MONSTER_HP_BASE = 2            # 第 1 波怪物血量（固定，不随难度变化）
# 难度递增：第 1 波不变；第 2 波起乘以二次曲线系数
# scale = 1 + DIFFICULTY_LIN*d + DIFFICULTY_QUAD*d²   (d = 波次-1)
MONSTER_W = 32
MONSTER_H = 32
# 并排成群生成：5% 三个并排 / 10% 两个并排 / 85% 单个（空间不足时自动降级）
MONSTER_GROUP_SPACING = 40     # 并排单位中心间距（略大于怪物宽度）
MONSTER_P_TRIPLE = 0.05        # 三个并排概率
MONSTER_P_DOUBLE = 0.10        # 两个并排概率
MONSTER_SPAWN_MARGIN = 24      # 生成区左右留白（距分割线/右边界）

# ---------- 子弹 ----------
BULLET_SPEED = 620             # 子弹上行速度 px/s
BULLET_TRAIL = 3               # 拖尾残影帧数（原 5，减段以降低每帧叠加混合开销）

# ---------- 粒子 ----------
STAR_COUNT = 50                # 背景星光数量
PARTICLE_CAP = 120             # 粒子数量上限（手机软渲染下 BLEND_ADD 混合贵，降上限保帧率）

# ---------- 数值递推公式（宝箱/怪物血量、怪物数量）----------
def chest_hp(wave):
    """小宝箱血量（随波数多项式增长）：= 怪物血量 × 5。"""
    return int(round(monster_hp(wave) * 5))


def monster_count(wave):
    """每波怪物数：12 + (波数-1) * 2。"""
    return MONSTER_COUNT_BASE + (wave - 1) * MONSTER_COUNT_STEP


def monster_hp(wave):
    """每波怪物血量（二次增长 + 二次曲线难度系数，难度由 set_difficulty 设置）。
    HP(w) = (2 + d + d²) × (1 + LIN·d + QUAD·d²)    , d = w-1
    """
    d = wave - 1
    base = MONSTER_HP_BASE + d + d * d
    scale = 1.0 + DIFFICULTY_LIN * d + DIFFICULTY_QUAD * d * d
    return int(round(base * scale))


_ATTACK_BONUS = [1, 1, 1.5, 1.5, 2, 2, 2.5, 3, 3, 4]


def attack_bonus(tier):
    """小宝箱攻击力增量（tier = 波次-1）：
    1, 1, 1.5, 1.5, 2, 2, 2.5, 3, 3, 4（支持小数，不取整）。
    超出范围取末值。
    """
    if 0 <= tier < len(_ATTACK_BONUS):
        return _ATTACK_BONUS[tier]
    return _ATTACK_BONUS[-1]


# ---------- BOSS 系统 ----------
# BOSS 血量 = 该波怪物血量 × BOSS_HP_MULT（倍率随难度：简单50/普通100/困难150/噩梦200，
# 见 DIFFICULTY_PARAMS 的 boss_mult，由 set_difficulty 更新）
BOSS_Y = 92                    # BOSS 中心 y（固定在顶部，不下落）
BOSS_INTRO_TIME = 2.0          # BOSS 出场展示时长（秒，期间游戏暂停）
BOSS_BULLET_SPEED = 200        # BOSS 普通子弹速度（四难度一致）
BOSS_BULLET_FAST = 320         # BOSS 快速子弹速度（四难度一致）
# BOSS 配色
C_BOSS_BODY = (90, 30, 80)
C_BOSS_EDGE = (40, 10, 35)
C_BOSS_GLOW = (200, 60, 160)
C_BOSS_EYE = (255, 220, 120)
C_BOSS_BULLET = (255, 90, 130)
C_BOSS_BULLET2 = (255, 180, 80)
C_BOSS_HP_BG = (50, 20, 30)
C_BOSS_HP = (255, 80, 110)
C_BEAM_WARN = (255, 80, 80)
C_BEAM_FIRE = (255, 240, 120)
# 棱镜哨卫光柱：均匀分段覆盖 [BEAM_SEG_START, BEAM_SEG_END]
BEAM_SEG_START = 24
BEAM_SEG_END = 456
# 横扫激光（棱镜哨卫三阶段 / 终焉之主二阶段）：有伤害 0.8s / 预警无伤害 0.8s 交替
SWEEP_BEAM_ON = 0.8
SWEEP_BEAM_OFF = 0.8
SWEEP_BEAM_WIDTH = 26          # 横扫激光宽度
SWEEP_BEAM_SPEED = 50          # 横扫激光横向移动速度 px/s（v3.1.0 减半）

# 追踪导弹转向速度（弧度/秒）——较慢，玩家横向移动可躲
TRACKING_TURN_SPEED = 0.8

# 落点轰炸（天罚核心）：各阶段预警时长由 marker 自带 warn_time 决定
BOMB_WARN_TIME = 1.2           # 一阶段标记预警时长
BOMB_RADIUS = 46               # 爆炸半径
BOMB_LINGER = 0.5              # 爆炸后残留时长（秒）后清除

# 虚空行者传送
VOID_TELEPORT_CYCLE = 3.0      # 传送周期（一阶段；二/三阶段在 boss.py 中减半）

# 终焉之主（压轴 BOSS）
FINAL_SATELLITE_COUNT = 3      # 护盾卫星数量
FINAL_SATELLITE_DIST = 70      # 卫星环绕半径
FINAL_SATELLITE_HP = 60        # 单个卫星血量
FINAL_SATELLITE_REGEN_PCT = 0.01  # 护盾存在时本体每秒回血百分比（1%）

# ---------- 金身（无敌道具）与临时分身 ----------
TEMP_CLONE_TIME = 3.0          # 临时分身持续时间（秒）
TEMP_CLONE_MAX = 3             # 临时分身同时存在上限
INVULN_TIME = 3.0              # 金身无敌持续时间（秒）（v3.1.0 由 2 秒改为 3 秒）
INVULN_SLOT_POS = (26, 62)     # 无敌道具槽中心（左上角，暂停键下方，避开宝箱）
INVULN_SLOT_R = 14             # 道具槽半径（缩小以免遮挡宝箱）
CLONE_SLOT_POS = (26, 98)      # 分身道具槽中心（无敌槽下方）
C_INVULN_GOLD = (255, 215, 90)   # 金身金边 / 图标
C_INVULN_SLOT = (90, 75, 35)     # 空槽暗金
