'''游戏配置文件 - 集中管理所有游戏参数'''

# ==================== 屏幕配置 ====================
SCREENSIZE = (800, 600)
FPS = 60

# ==================== 颜色定义 ====================
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
CYAN = (0, 255, 255)
MAGENTA = (255, 0, 255)
GRAY = (128, 128, 128)
DARK_GRAY = (64, 64, 64)
ORANGE = (255, 165, 0)
PURPLE = (128, 0, 128)

# ==================== 游戏参数 ====================
PLAYER_Y = 450  # 主角固定Y位置
SCROLL_SPEED = 2  # 卷轴滚动速度
WAVE_DISTANCE = 800  # 每波敌人之间的距离
BOSS_WAVE_INTERVAL = 5  # 每5波出现一个BOSS

# ==================== BOSS难度配置 ====================
BOSS_BASE_COUNT = 1  # x的初始值（默认1）
BOSS_BASE_HEALTH = 500  # BOSS基础血量
BOSS_HEALTH_MULTIPLIER = 1.6  # BOSS血量增长系数（降低：1.8→1.6，普通模式更合理）
BOSS_HEALTH_MULTIPLIER_BOSS_MODE = 1.8  # BOSS战模式专属增长系数（提高：1.5→1.8，增加挑战性）

# 阶段1参数 (>70%血量)
BOSS_STAGE1_BULLET_BASE = 5  # 基础子弹数
BOSS_STAGE1_BULLET_GROWTH = 1  # 每击败一个BOSS增加的子弹数

# 阶段2参数 (40%-70%血量)
BOSS_STAGE2_BULLET_BASE = 6  # 基础子弹数
BOSS_STAGE2_BULLET_GROWTH = 1  # 每击败一个BOSS增加的子弹数
BOSS_STAGE2_FREQ_BASE = 1.5  # 基础频率倍数
BOSS_STAGE2_FREQ_GROWTH = 0.2  # 每击败一个BOSS增加的频率倍数（降低：0.3→0.2）
BOSS_STAGE2_BULLET_SPEED = 9  # 子弹速度（降低：10→9）
BOSS_STAGE2_MIN_INTERVAL = 500  # 最小射击间隔（增加：400→500，给玩家更多反应时间）

# 阶段3参数 (<40%血量)
BOSS_STAGE3_BULLET_BASE = 15  # 基础子弹数（降低：18→15）
BOSS_STAGE3_BULLET_GROWTH = 2  # 每击败一个BOSS增加的子弹数（降低：3→2）
BOSS_STAGE3_FREQ_BASE = 1.8  # 基础频率倍数（降低：2.0→1.8）
BOSS_STAGE3_FREQ_GROWTH = 0.15  # 每击败一个BOSS增加的频率倍数（降低：0.2→0.15）
BOSS_STAGE3_BULLET_SPEED = 10  # 子弹速度（降低：12→10）
BOSS_STAGE3_MIN_INTERVAL = 400  # 最小射击间隔（增加：350→400，给玩家更多反应时间）

# ==================== 资源路径 ====================
RESOURCE_DIR = 'resources'
