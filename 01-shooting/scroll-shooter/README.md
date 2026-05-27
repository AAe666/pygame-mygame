# 🎮 卷轴射击游戏 (Scroll Shooter)

一个使用 Pygame 开发的经典纵向卷轴射击游戏，包含丰富的奖励系统、BOSS战模式和多种游戏机制。

## 📖 目录

- [游戏特色](#游戏特色)
- [游戏模式](#游戏模式)
- [操作说明](#操作说明)
- [奖励系统](#奖励系统)
- [BOSS机制](#boss机制)
- [CDK兑换码](#cdk兑换码)
- [安装运行](#安装运行)
- [项目结构](#项目结构)
- [配置说明](#配置说明)
- [开发说明](#开发说明)

## 🌟 游戏特色

### 核心玩法
- **鼠标控制**：鼠标移动控制飞机位置，自动射击
- **波次系统**：敌人分波次生成，难度逐步提升
- **奖励选择**：每波结束后根据消灭率获得不同数量的奖励
- **属性成长**：攻击力、攻速、多段攻击、生命值等可永久提升

### 视觉效果
- **星空背景**：滚动的星空营造太空射击氛围
- **粒子系统**：敌人爆炸时的粒子特效
- **血条显示**：实时显示玩家和BOSS的生命值
- **图标化HUD**：右上角显示攻击属性，清晰直观

### 游戏平衡
- **难度曲线**：普通模式和BOSS战模式采用不同的难度增长曲线
- **奖励机制**：消灭率越高，奖励越丰厚
- **BOSS阶段**：BOSS根据血量分为3个战斗阶段，攻击模式不同

## 🎯 游戏模式

### 1. 普通模式
- 每5波出现一个BOSS
- 普通波次：3-10个敌人（随波数增加）
- BOSS波：1个BOSS + 奖励选择
- 难度增长系数：1.8（适中）

### 2. BOSS战模式
- 每波都是BOSS，连续挑战
- 无小怪，纯BOSS战体验
- 难度增长系数：1.5（更平缓）
- BOSS奖励耗尽后给3个普通奖励

## 🎮 操作说明

| 操作 | 按键 | 说明 |
|------|------|------|
| 移动 | 鼠标移动 | 控制飞机位置 |
| 射击 | 自动 | 根据攻速自动射击 |
| 暂停 | ESC / Enter | 暂停/继续游戏 |
| 清屏 | 鼠标左键 | 使用子弹清除道具（如有） |
| 选择奖励 | 鼠标左键 | 点击奖励按钮 |

## 🎁 奖励系统

### 普通奖励（3选1/2选1/1选1）

根据波次消灭率决定奖励次数：
- **100%消灭**：3个奖励选项
- **80%-99%消灭**：2个奖励选项
- **低于80%**：1个奖励选项

#### 奖励类型

| 奖励 | 效果 | 说明 |
|------|------|------|
| 攻击力 +3 | 攻击伤害+3 | 有BOSS奖励则+6 |
| 攻速提升 | 攻击速度+6% | 射速提升，有BOSS奖励则+12% |
| 多段攻击 | 子弹数量+1 | 同时发射更多子弹（最多+6） |
| 回复100生命 | 固定回复100点生命 | 战术性回复 |
| 最大生命 +15 | 生命值上限+15 | 有BOSS奖励则+30 |

### BOSS奖励（2选1）

击败BOSS后专属奖励，金色边框显示：

| 奖励 | 效果 | 说明 |
|------|------|------|
| 子弹追踪 | 子弹自动追踪最近敌人 | 强力辅助 |
| 攻击力翻倍 | 后续攻击力奖励×2 | 从+3变为+6 |
| 攻速翻倍 | 后续攻速奖励×2 | 从+6%变为+12% |
| 生命值翻倍 | 后续生命奖励×2 | 从+15变为+30 |
| 子弹清除（一次性） | 清除全场敌人子弹 | 保命神技 |

**注意**：BOSS奖励中的"后续XX+翻倍"是指**未来获得的该类奖励效果翻倍**，不是当前属性立即翻倍。

## 👾 BOSS机制

### 血量计算
```
BOSS血量 = 基础血量 × (增长系数 ^ 已击败BOSS数)

普通模式: 500 × (1.8 ^ n)
BOSS战模式: 500 × (1.5 ^ n)
```

### 三阶段攻击

BOSS根据血量百分比切换攻击模式：

#### 阶段1：血量 > 70%（紫色）
- **攻击方式**：散射子弹
- **子弹数量**：5 + 已击败BOSS数
- **射击频率**：正常
- **子弹速度**：慢

#### 阶段2：血量 40%-70%（橙色）
- **攻击方式**：高速子弹
- **子弹数量**：6 + 已击败BOSS数
- **射击频率**：1.5 + 0.2×倍率（随击败数增长）
- **子弹速度**：9（较快）
- **最小间隔**：500ms

#### 阶段3：血量 < 40%（红色）
- **攻击方式**：全屏弹幕
- **子弹数量**：15 + 2×已击败BOSS数
- **射击频率**：2.0 + 0.2×倍率（随击败数增长）
- **子弹速度**：10（快）
- **最小间隔**：350ms

### BOSS移动
- 进入屏幕后停在顶部
- 左右移动，碰边界反弹
- 随机改变移动方向

## 🔑 CDK兑换码

在游戏开始界面输入CDK兑换码，可获得初始属性加成：

| CDK代码 | 效果 | 说明 |
|---------|------|------|
| `health_10x` | 初始生命值×10 | 从120变为1200 |
| `attack_10x` | 初始攻击力×10 | 从10变为100 |
| `speed_10x` | 初始攻速×10 | 射击间隔从600ms变为60ms |

**重要**：
- CDK只影响**初始值**，后续奖励在此基础上叠加
- 输入框支持小写字母、数字、下划线
- 无效CDK会提示"CDK不存在"
- 激活成功会显示绿色提示框（3秒）

## 📦 安装运行

### 环境要求
- Python 3.8+
- Pygame 2.0+
- Windows系统（字体依赖）

### 安装步骤

1. **克隆或下载项目**
```bash
cd D:\TYW\Code\Games\01-shooting\scroll-shooter
```

2. **创建虚拟环境**（推荐）
```bash
python -m venv venv312
venv312\Scripts\activate
```

3. **安装依赖**
```bash
pip install pygame
```

4. **运行游戏**
```bash
python main.py
```

### 打包发布

项目已包含PyInstaller配置文件，可打包为独立exe：

```bash
# 使用提供的批处理文件
build.bat

# 或手动打包
pyinstaller ScrollShooter.spec
```

打包后的exe位于 `dist/` 目录。

## 📁 项目结构

```
scroll-shooter/
├── main.py                 # 游戏主程序（游戏循环、状态管理）
├── cfg.py                  # 配置文件（所有游戏参数）
├── requirements.txt        # Python依赖
├── ScrollShooter.spec     # PyInstaller打包配置
├── build.bat              # 打包批处理脚本
├── README.md              # 项目文档
│
├── modules/               # 游戏模块
│   ├── __init__.py       # 模块初始化
│   ├── player.py         # 玩家精灵类
│   ├── enemy.py          # 敌人和BOSS类
│   ├── bullet.py         # 子弹类
│   ├── reward.py         # 奖励系统
│   ├── particles.py      # 粒子系统
│   ├── sprites.py        # 旧版精灵类（兼容）
│   └── utils.py          # 工具函数（UI绘制、敌人生成等）
│
├── resources/             # 资源文件
│   ├── attack.png        # 攻击力图标
│   ├── speed.png         # 攻速图标
│   ├── multi.png         # 多段攻击图标
│   ├── health.png        # 生命值图标
│   ├── tracking.png      # 子弹追踪图标
│   └── clear.png         # 子弹清除图标
│
├── venv312/              # Python虚拟环境
├── build/                # PyInstaller构建目录
└── dist/                 # 打包输出目录
```

## ⚙️ 配置说明

所有游戏参数集中在 `cfg.py` 中，方便调整：

### 屏幕配置
```python
SCREENSIZE = (800, 600)  # 窗口尺寸
FPS = 60                  # 帧率
```

### 游戏参数
```python
PLAYER_Y = 450            # 玩家初始Y位置
SCROLL_SPEED = 2          # 卷轴滚动速度
WAVE_DISTANCE = 800       # 每波敌人之间的距离
BOSS_WAVE_INTERVAL = 5    # 每5波出现BOSS
```

### BOSS难度配置
```python
BOSS_BASE_HEALTH = 500               # BOSS基础血量
BOSS_HEALTH_MULTIPLIER = 1.8         # 普通模式增长系数
BOSS_HEALTH_MULTIPLIER_BOSS_MODE = 1.5  # BOSS战模式增长系数

# 阶段1参数
BOSS_STAGE1_BULLET_BASE = 5
BOSS_STAGE1_BULLET_GROWTH = 1

# 阶段2参数
BOSS_STAGE2_BULLET_BASE = 6
BOSS_STAGE2_BULLET_GROWTH = 1
BOSS_STAGE2_FREQ_BASE = 1.5
BOSS_STAGE2_FREQ_GROWTH = 0.2
BOSS_STAGE2_BULLET_SPEED = 9
BOSS_STAGE2_MIN_INTERVAL = 500

# 阶段3参数
BOSS_STAGE3_BULLET_BASE = 15
BOSS_STAGE3_BULLET_GROWTH = 2
BOSS_STAGE3_FREQ_BASE = 2.0
BOSS_STAGE3_FREQ_GROWTH = 0.2
BOSS_STAGE3_BULLET_SPEED = 10
BOSS_STAGE3_MIN_INTERVAL = 350
```

## 💻 开发说明

### 代码架构

游戏采用**模块化设计**，主要模块职责：

- **main.py**：游戏主循环、状态机、事件处理
- **cfg.py**：配置集中管理，避免硬编码
- **modules/player.py**：玩家逻辑
- **modules/enemy.py**：敌人和BOSS逻辑
- **modules/bullet.py**：子弹逻辑
- **modules/reward.py**：奖励系统
- **modules/particles.py**：粒子特效
- **modules/utils.py**：UI绘制、敌人生成等工具函数

### 游戏状态机

```
STATE_START (开始界面)
    ↓ 选择模式
STATE_PLAYING (游戏进行中)
    ↓ 波次清除
STATE_REWARD (奖励选择)
    ↓ 选择完毕
STATE_PLAYING (继续游戏)
    ↓ 玩家死亡
STATE_GAME_OVER (游戏结束)
    ↓ 点击重新开始
STATE_PLAYING
```

### 暂停状态

按下ESC/Enter进入暂停：
- 显示暂停界面
- 可点击"继续游戏"或"返回主界面"
- 暂停期间不更新游戏逻辑

### 核心机制

#### 敌人生成
```python
# 普通波
enemy_count = min(3 + wave_num // 2, 10)  # 3-10个

# BOSS波
if wave_num % 5 == 0 or game_mode == 'boss':
    spawn_boss()
```

#### 奖励次数计算
```python
kill_ratio = killed / total
if kill_ratio >= 1.0: reward_count = 3
elif kill_ratio >= 0.8: reward_count = 2
else: reward_count = 1
```

#### 子弹追踪
```python
# 找到最近敌人
closest = min(enemies, key=lambda e: distance(bullet, e))
# 调整方向
bullet.dx = bullet.dx * 0.7 + target_dx * 0.3
bullet.dy = bullet.dy * 0.7 + target_dy * 0.3
```

### 性能优化

1. **图标缓存**：避免重复加载和缩放图标
2. **独立随机数生成器**：背景星空使用固定种子，不影响游戏随机性
3. **碰撞检测优化**：使用Pygame内置的`sprite.collide_rect`
4. **列表推导式**：清理死亡敌人和越界子弹

### 扩展建议

- [ ] 添加音效和背景音乐
- [ ] 增加更多BOSS类型
- [ ] 添加道具掉落系统
- [ ] 实现排行榜功能
- [ ] 添加更多游戏模式
- [ ] 优化移动端适配

## 📝 版本历史

### v1.0.0 (当前版本)
- ✅ 基础射击玩法
- ✅ 波次系统
- ✅ 奖励系统（普通+BOSS）
- ✅ BOSS三阶段攻击
- ✅ CDK兑换码系统
- ✅ 两种游戏模式
- ✅ 粒子特效
- ✅ 图标化HUD
- ✅ 暂停系统
- ✅ 玩法说明

## 📄 许可证

本项目仅供学习和娱乐使用。

## 🤝 贡献

欢迎提交Issue和Pull Request！

---

**享受游戏！** 🚀
