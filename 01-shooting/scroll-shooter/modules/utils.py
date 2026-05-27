'''工具函数'''
import pygame
import os
import random

# 图标缓存
_icon_cache = {}

def load_icon(icon_name, size=(32, 32)):
    """加载并缩放图标
    
    Args:
        icon_name: 图标文件名（不含路径），如 'attack.png'
        size: 目标尺寸 (width, height)，默认 32x32
    
    Returns:
        pygame.Surface: 缩放后的图标 surface
    """
    import cfg
    
    # 检查缓存
    cache_key = (icon_name, size)
    if cache_key in _icon_cache:
        return _icon_cache[cache_key]
    
    # 构建图标路径（使用绝对路径）
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    icon_path = os.path.join(base_dir, 'resources', icon_name)
    
    if not os.path.exists(icon_path):
        print(f"  ⚠️ 图标文件不存在: {icon_path}")
        # 返回一个空的透明 surface
        empty = pygame.Surface(size, pygame.SRCALPHA)
        empty.fill((0, 0, 0, 0))
        _icon_cache[cache_key] = empty
        return empty
    
    try:
        # 加载图标
        icon = pygame.image.load(icon_path).convert_alpha()
        # 缩放到目标尺寸
        icon = pygame.transform.smoothscale(icon, size)
        # 缓存
        _icon_cache[cache_key] = icon
        return icon
    except Exception as e:
        print(f"  ⚠️ 加载图标失败 {icon_name}: {e}")
        empty = pygame.Surface(size, pygame.SRCALPHA)
        empty.fill((0, 0, 0, 0))
        _icon_cache[cache_key] = empty
        return empty


def get_chinese_font(size):
    """获取支持中文的字体"""
    import os
    
    # Windows系统字体路径（优先使用ttf而非ttc）
    windows_fonts = [
        r'C:\Windows\Fonts\simhei.ttf',   # 黑体
        r'C:\Windows\Fonts\simkai.ttf',   # 楷体
        r'C:\Windows\Fonts\simsun.ttc',   # 宋体
        r'C:\Windows\Fonts\msyh.ttc',     # 微软雅黑
    ]
    
    for font_path in windows_fonts:
        if os.path.exists(font_path):
            try:
                font = pygame.font.Font(font_path, size)
                # 测试是否能正确渲染中文
                test_surface = font.render('测试', True, (255, 255, 255))
                if test_surface.get_width() > 0:
                    return font
            except Exception as e:
                continue
    
    # 如果Windows字体都不行，尝试SysFont
    chinese_font_names = ['simhei', 'simsun', 'microsoftyahei', 'msyh']
    for font_name in chinese_font_names:
        try:
            font = pygame.font.SysFont(font_name, size)
            test_surface = font.render('测试', True, (255, 255, 255))
            if test_surface.get_width() > 0:
                return font
        except:
            continue
    
    # 如果都不行，返回默认字体
    return pygame.font.Font(None, size)


def show_text(screen, text, color, font, x, y, center=False):
    """显示文字"""
    text_render = font.render(text, True, color)
    text_rect = text_render.get_rect()
    if center:
        text_rect.center = (x, y)
    else:
        text_rect.topleft = (x, y)
    screen.blit(text_render, text_rect)
    return text_rect


def show_life(screen, health, max_health, x, y):
    """显示生命值（带数值和美化）"""
    bar_width = 150
    bar_height = 18
    health_ratio = health / max_health if max_health > 0 else 0
    
    # 血条背景（深色）
    pygame.draw.rect(screen, (40, 40, 40), (x, y, bar_width, bar_height))
    
    # 血条填充（根据血量比例渐变颜色）
    if health_ratio > 0.6:
        bar_color = (0, 200, 0)  # 绿色
    elif health_ratio > 0.3:
        bar_color = (200, 200, 0)  # 黄色
    else:
        bar_color = (200, 0, 0)  # 红色
    
    fill_width = int(bar_width * health_ratio)
    if fill_width > 0:
        pygame.draw.rect(screen, bar_color, (x + 2, y + 2, fill_width - 4, bar_height - 4))
        # 添加高光效果
        highlight_color = (min(255, bar_color[0] + 80), 
                          min(255, bar_color[1] + 80), 
                          min(255, bar_color[2] + 80))
        pygame.draw.rect(screen, highlight_color, 
                        (x + 2, y + 2, fill_width - 4, (bar_height - 4) // 3))
    
    # 边框
    pygame.draw.rect(screen, (255, 255, 255), (x, y, bar_width, bar_height), 2)
    
    # 显示数值（在血条中间）
    health_font = get_chinese_font(12)
    health_text = f'{int(health)} / {max_health}'
    
    # 添加文字阴影
    show_text(screen, health_text, (0, 0, 0), health_font, 
             x + bar_width // 2 + 1, y + bar_height // 2 + 1, center=True)
    show_text(screen, health_text, (255, 255, 255), health_font, 
             x + bar_width // 2, y + bar_height // 2, center=True)


def generate_wave_enemies(wave_num, screen_width, boss_defeated_count=0, force_boss=False, is_boss_mode=False):
    """生成一波敌人"""
    from modules.enemy import Enemy
    import cfg
    
    enemies = []
    
    # BOSS波或强制生成BOSS
    if force_boss or wave_num % cfg.BOSS_WAVE_INTERVAL == 0:
        boss = Enemy(screen_width // 2, -100, 'boss', wave_num, boss_defeated_count, is_boss_mode)
        enemies.append(boss)
    else:
        # 普通波：敌人数量随波数增加（3-10个）
        enemy_count = min(3 + wave_num // 2, 10)
        
        for i in range(enemy_count):
            x = random.randint(50, screen_width - 50)
            y = -50 - i * 60  # 从屏幕上方依次出现
            enemy = Enemy(x, y, 'normal', wave_num)
            enemies.append(enemy)
    
    return enemies


def draw_background(screen, scroll_offset, bg_color=(0, 0, 50)):
    """绘制滚动背景"""
    screen.fill(bg_color)
    
    # 绘制一些星空效果
    rng = random.Random(42)  # 使用独立的随机数生成器，不影响全局random
    for _ in range(100):
        x = rng.randint(0, 800)
        y = (rng.randint(0, 600) + scroll_offset) % 600
        size = rng.randint(1, 3)
        brightness = rng.randint(100, 255)
        pygame.draw.circle(screen, (brightness, brightness, brightness), (x, y), size)


def draw_hud(screen, player, wave_num, score, boss_active=False, player_stats=None):
    """绘制HUD（头上显示）"""
    # 使用支持中文的字体
    hud_font = get_chinese_font(18)
    
    # 暂停按钮（左上角）
    pause_button_x = 10
    pause_button_y = 10
    pause_button_width = 60
    pause_button_height = 25
    
    # 绘制暂停按钮
    pygame.draw.rect(screen, (100, 100, 100), 
                    (pause_button_x, pause_button_y, pause_button_width, pause_button_height))
    pygame.draw.rect(screen, (255, 255, 255), 
                    (pause_button_x, pause_button_y, pause_button_width, pause_button_height), 2)
    
    # 绘制暂停文字
    show_text(screen, '暂停', (255, 255, 255), hud_font, 
             pause_button_x + pause_button_width // 2, 
             pause_button_y + pause_button_height // 2, 
             center=True)
    
    # 波数（在暂停按钮右边）
    show_text(screen, f'波数: {wave_num}', (255, 255, 255), hud_font, 80, 10)
    
    # 显示距离BOSS还有几波
    import cfg
    waves_to_boss = cfg.BOSS_WAVE_INTERVAL - (wave_num % cfg.BOSS_WAVE_INTERVAL)
    if waves_to_boss == 0:
        boss_text = 'BOSS战！'
        boss_color = (255, 0, 0)  # 红色
    else:
        boss_text = f'距离BOSS: {waves_to_boss}波'
        boss_color = (255, 255, 0)  # 黄色
    show_text(screen, boss_text, boss_color, hud_font, 80, 35)
    
    # 分数
    show_text(screen, f'分数: {score}', (255, 255, 0), hud_font, 80, 60)
    
    # 生命值
    show_life(screen, player.health, player.max_health, 80, 85)
    
    # 攻击属性（右上角，美化显示）
    stat_font = get_chinese_font(18)  # 增大文字：16→18
    stat_x = 650
    stat_y = 10
    stat_spacing = 24  # 稍微增大间距以适应大文字
    icon_size = (18, 18)  # 图标尺寸不变：18x18
    
    # 背景框（稍微增大高度以适应大文字）
    bg_width = 140
    bg_height = 76
    pygame.draw.rect(screen, (30, 30, 50, 180), (stat_x - 5, stat_y - 5, bg_width, bg_height))
    pygame.draw.rect(screen, (100, 100, 150), (stat_x - 5, stat_y - 5, bg_width, bg_height), 2)
    
    # 攻击力 - 使用图标
    atk_color = (255, 100, 100) if player.attack_power > 20 else (0, 255, 255)
    atk_icon = load_icon('attack.png', icon_size)
    # 图标和文字垂直居中对齐（行高24，图标18，文字18，偏移3px）
    screen.blit(atk_icon, (stat_x, stat_y + 3))
    show_text(screen, f'{player.attack_power}', atk_color, stat_font, stat_x + 22, stat_y)
    
    # 攻击速度 - 使用图标
    # 显示攻速提升百分比（基于初始600ms）
    initial_attack_speed = 600
    # 计算提升百分比，防止负数
    speed_increase_percent = max(0, int((initial_attack_speed - player.attack_speed) / initial_attack_speed * 100))
    spd_color = (100, 255, 100) if speed_increase_percent > 20 else (0, 255, 255)
    spd_icon = load_icon('speed.png', icon_size)
    screen.blit(spd_icon, (stat_x, stat_y + stat_spacing + 3))
    show_text(screen, f'+{speed_increase_percent}%', spd_color, stat_font, stat_x + 22, stat_y + stat_spacing)
    
    # 多段攻击 - 使用图标
    multi_color = (255, 255, 100) if player.multi_shot > 3 else (0, 255, 255)
    multi_icon = load_icon('multi.png', icon_size)
    screen.blit(multi_icon, (stat_x, stat_y + stat_spacing * 2 + 3))
    show_text(screen, f'{player.multi_shot}', multi_color, stat_font, stat_x + 22, stat_y + stat_spacing * 2)
    
    # 子弹清除道具图标（右侧中间位置）
    if player_stats and player_stats.get('has_bullet_clear', False):
        icon_x = 750
        icon_y = 120
        icon_size_display = 48  # 增大道具图标框
        
        # 检查是否可用
        is_available = player_stats.get('bullet_clear_available', False)
        
        if is_available:
            # 可用：显示金色边框和图标
            pygame.draw.rect(screen, (139, 105, 20),  # 金色背景
                            (icon_x, icon_y, icon_size_display, icon_size_display))
            pygame.draw.rect(screen, (255, 215, 0),  # 金色边框
                            (icon_x, icon_y, icon_size_display, icon_size_display), 3)
            
            # 绘制子弹清除图标（40x40，留4px边距）
            clear_icon = load_icon('clear.png', (40, 40))
            screen.blit(clear_icon, (icon_x + 4, icon_y + 4))
            
            # 提示文字
            show_text(screen, '点击清除', (255, 215, 0), hud_font, 
                     icon_x + icon_size_display // 2, icon_y + icon_size_display + 5, center=True)
        else:
            # 已使用：显示灰色
            pygame.draw.rect(screen, (50, 50, 50),  # 灰色背景
                            (icon_x, icon_y, icon_size_display, icon_size_display))
            pygame.draw.rect(screen, (100, 100, 100),  # 灰色边框
                            (icon_x, icon_y, icon_size_display, icon_size_display), 2)
            
            # 绘制已用文字
            show_text(screen, '[已用]', (150, 150, 150), get_chinese_font(16), 
                     icon_x + icon_size_display // 2, icon_y + icon_size_display // 2, center=True)


def draw_start_screen(screen, font):
    """绘制开始界面"""
    import cfg
    
    screen.fill((0, 0, 50))
    
    # 标题
    title_font = get_chinese_font(48)
    show_text(screen, '卷轴射击', (255, 255, 0), title_font, 400, 100, center=True)
    
    # 模式选择按钮
    button_width = 200
    button_height = 50
    button_y = 200
    
    # 普通模式按钮
    normal_button_x = 150
    pygame.draw.rect(screen, (0, 100, 0), 
                    (normal_button_x, button_y, button_width, button_height))
    pygame.draw.rect(screen, (0, 255, 0), 
                    (normal_button_x, button_y, button_width, button_height), 3)
    show_text(screen, '普通模式', (255, 255, 255), font, 
             normal_button_x + button_width // 2, button_y + button_height // 2, center=True)
    show_text(screen, f'每{cfg.BOSS_WAVE_INTERVAL}波BOSS', (200, 200, 200), font, 
             normal_button_x + button_width // 2, button_y + button_height + 15, center=True)
    
    # BOSS战模式按钮
    boss_button_x = 450
    pygame.draw.rect(screen, (100, 0, 0), 
                    (boss_button_x, button_y, button_width, button_height))
    pygame.draw.rect(screen, (255, 0, 0), 
                    (boss_button_x, button_y, button_width, button_height), 3)
    show_text(screen, 'BOSS战模式', (255, 255, 255), font, 
             boss_button_x + button_width // 2, button_y + button_height // 2, center=True)
    show_text(screen, '每波都是BOSS', (200, 200, 200), font, 
             boss_button_x + button_width // 2, button_y + button_height + 15, center=True)
    
    # 玩法说明按钮
    help_button_width = 180
    help_button_height = 40
    help_button_x = 310
    help_button_y = 300
    
    pygame.draw.rect(screen, (0, 50, 100), 
                    (help_button_x, help_button_y, help_button_width, help_button_height))
    pygame.draw.rect(screen, (0, 150, 255), 
                    (help_button_x, help_button_y, help_button_width, help_button_height), 2)
    show_text(screen, '[玩法说明]', (255, 255, 255), font, 
             help_button_x + help_button_width // 2, help_button_y + help_button_height // 2, center=True)
    
    # 排行榜按钮
    leaderboard_button_width = 180
    leaderboard_button_height = 40
    leaderboard_button_x = 310
    leaderboard_button_y = 350
    
    pygame.draw.rect(screen, (100, 50, 0), 
                    (leaderboard_button_x, leaderboard_button_y, leaderboard_button_width, leaderboard_button_height))
    pygame.draw.rect(screen, (255, 150, 0), 
                    (leaderboard_button_x, leaderboard_button_y, leaderboard_button_width, leaderboard_button_height), 2)
    show_text(screen, '[排行榜]', (255, 255, 255), font, 
             leaderboard_button_x + leaderboard_button_width // 2, leaderboard_button_y + leaderboard_button_height // 2, center=True)
    
    # CDK输入框位置下移
    # CDK将在500位置


def draw_cdk_input(screen, font, cdk_text, is_active):
    """绘制CDK输入框"""
    import cfg
    
    # CDK标题
    cdk_title_font = get_chinese_font(20)
    show_text(screen, '[CDK兑换码]', (255, 215, 0), cdk_title_font, 400, 490, center=True)
    
    # 输入框
    input_box_x = 250
    input_box_y = 520
    input_box_width = 300
    input_box_height = 40
    
    # 输入框背景
    if is_active:
        box_color = (60, 60, 120)  # 激活状态：亮色
        border_color = (255, 255, 0)  # 黄色边框
    else:
        box_color = (40, 40, 80)  # 未激活状态：暗色
        border_color = (150, 150, 150)  # 灰色边框
    
    pygame.draw.rect(screen, box_color, (input_box_x, input_box_y, input_box_width, input_box_height))
    pygame.draw.rect(screen, border_color, (input_box_x, input_box_y, input_box_width, input_box_height), 2)
    
    # 显示输入的文本或提示
    if cdk_text:
        show_text(screen, cdk_text, (255, 255, 255), font, 
                 input_box_x + input_box_width // 2, input_box_y + input_box_height // 2, center=True)
    else:
        show_text(screen, '输入CDK兑换码', (150, 150, 150), font, 
                 input_box_x + input_box_width // 2, input_box_y + input_box_height // 2, center=True)


def draw_cdk_message(screen, message, success):
    """绘制CDK提示消息"""
    import cfg
    
    # 消息框位置和大小
    box_width = 350
    box_height = 60
    box_x = (cfg.SCREENSIZE[0] - box_width) // 2
    box_y = 420
    
    # 根据成功或失败选择颜色
    if success:
        bg_color = (0, 100, 0)  # 绿色背景
        border_color = (0, 255, 0)  # 绿色边框
        text_color = (255, 255, 255)  # 白色文字
    else:
        bg_color = (100, 0, 0)  # 红色背景
        border_color = (255, 0, 0)  # 红色边框
        text_color = (255, 200, 200)  # 浅红色文字
    
    # 绘制消息框
    pygame.draw.rect(screen, bg_color, (box_x, box_y, box_width, box_height))
    pygame.draw.rect(screen, border_color, (box_x, box_y, box_width, box_height), 2)
    
    # 显示消息
    show_text(screen, message, text_color, get_chinese_font(16), 
             box_x + box_width // 2, box_y + box_height // 2, center=True)


def draw_help_screen(screen, scroll_offset=0):
    """绘制玩法说明界面（支持滚动）
    
    Args:
        screen: pygame屏幕对象
        scroll_offset: 滚动偏移量（正值向上滚动）
    """
    import cfg
    
    # 半透明背景
    overlay = pygame.Surface(cfg.SCREENSIZE)
    overlay.set_alpha(230)
    overlay.fill((20, 20, 60))
    screen.blit(overlay, (0, 0))
    
    # 背景框 - 留出底部按钮空间
    box_x = 80
    box_y = 40
    box_width = 640
    box_height = 450  # 减小高度，为按钮留空间
    
    # 背景框渐变效果
    for i in range(10):
        alpha = 200 - i * 15
        color = (30 + i * 5, 30 + i * 5, 80 + i * 10)
        pygame.draw.rect(screen, color, 
                        (box_x + i, box_y + i, box_width - i * 2, box_height - i * 2))
    
    # 边框
    pygame.draw.rect(screen, (100, 150, 255), (box_x, box_y, box_width, box_height), 3)
    pygame.draw.rect(screen, (150, 200, 255), (box_x + 3, box_y + 3, box_width - 6, box_height - 6), 2)
    
    # 标题（固定在顶部）
    title_font = get_chinese_font(36)
    show_text(screen, '[玩法说明]', (255, 255, 100), title_font, 400, 65, center=True)
    
    # 分隔线
    pygame.draw.line(screen, (100, 150, 255), (120, 95), (680, 95), 2)
    
    # 创建内容区域裁剪表面（需要足够大以容纳所有内容）
    estimated_content_height = 900  # 增加高度，确保内容完整显示
    content_surface = pygame.Surface((box_width - 40, estimated_content_height), pygame.SRCALPHA)
    content_surface.fill((0, 0, 0, 0))  # 透明背景
    
    # 内容字体
    content_font = get_chinese_font(18)
    small_font = get_chinese_font(16)
    
    y_pos = 10
    line_height = 28
    
    # 游戏目标
    show_text(content_surface, '[游戏目标]', (255, 220, 100), content_font, 20, y_pos)
    y_pos += line_height
    show_text(content_surface, '• 鼠标控制飞机移动，自动射击', (255, 255, 255), small_font, 40, y_pos)
    y_pos += line_height
    show_text(content_surface, '• 消灭敌人，生存更久，获取更强奖励', (255, 255, 255), small_font, 40, y_pos)
    y_pos += line_height
    show_text(content_surface, '• 挑战更高波数，击败更多BOSS', (255, 255, 255), small_font, 40, y_pos)
    y_pos += line_height + 6
    
    # 游戏模式
    show_text(content_surface, '[游戏模式]', (255, 220, 100), content_font, 20, y_pos)
    y_pos += line_height
    show_text(content_surface, '• 普通模式：每5波出现一个BOSS', (255, 255, 255), small_font, 40, y_pos)
    y_pos += line_height
    show_text(content_surface, '• BOSS战模式：每波都是BOSS，连续挑战', (255, 255, 255), small_font, 40, y_pos)
    y_pos += line_height
    show_text(content_surface, '• BOSS战模式难度增长更平缓（1.5 vs 1.8）', (255, 255, 255), small_font, 40, y_pos)
    y_pos += line_height + 6
    
    # 奖励系统
    show_text(content_surface, '[奖励系统]', (255, 220, 100), content_font, 20, y_pos)
    y_pos += line_height
    show_text(content_surface, '• 每波敌人清除后获得奖励选择', (255, 255, 255), small_font, 40, y_pos)
    y_pos += line_height
    show_text(content_surface, '• 消灭率100%：3个奖励选项', (255, 255, 255), small_font, 40, y_pos)
    y_pos += line_height
    show_text(content_surface, '• 消灭率80%+：2个奖励选项', (255, 255, 255), small_font, 40, y_pos)
    y_pos += line_height
    show_text(content_surface, '• 消灭率<80%：1个奖励选项', (255, 255, 255), small_font, 40, y_pos)
    y_pos += line_height + 6
    
    # 普通奖励
    show_text(content_surface, '[普通奖励类型]', (255, 220, 100), content_font, 20, y_pos)
    y_pos += line_height
    show_text(content_surface, '• 攻击力+3：提升基础伤害（有BOSS奖励则+6）', (255, 255, 255), small_font, 40, y_pos)
    y_pos += line_height
    show_text(content_surface, '• 攻速提升：攻击速度+6%（有BOSS奖励则+12%）', (255, 255, 255), small_font, 40, y_pos)
    y_pos += line_height
    show_text(content_surface, '• 多段攻击：子弹数量+1（最多+6）', (255, 255, 255), small_font, 40, y_pos)
    y_pos += line_height
    show_text(content_surface, '• 回复100生命值：固定回复100点生命', (255, 255, 255), small_font, 40, y_pos)
    y_pos += line_height
    show_text(content_surface, '• 最大生命+15：永久提升血量上限（有BOSS奖励则+30）', (255, 255, 255), small_font, 40, y_pos)
    y_pos += line_height + 6
    
    # BOSS奖励
    show_text(content_surface, '[BOSS奖励]', (255, 220, 100), content_font, 20, y_pos)
    y_pos += line_height
    show_text(content_surface, '• 击败BOSS后先选择BOSS奖励（金色边框）', (255, 255, 255), small_font, 40, y_pos)
    y_pos += line_height
    show_text(content_surface, '• BOSS奖励选完后继续选择普通奖励', (255, 255, 255), small_font, 40, y_pos)
    y_pos += line_height
    show_text(content_surface, '• 子弹追踪：子弹自动追踪最近敌人', (255, 255, 255), small_font, 40, y_pos)
    y_pos += line_height
    show_text(content_surface, '• 攻击力翻倍：后续攻击力奖励×2（+3变+6）', (255, 255, 255), small_font, 40, y_pos)
    y_pos += line_height
    show_text(content_surface, '• 攻速翻倍：后续攻速奖励×2（+6%变+12%）', (255, 255, 255), small_font, 40, y_pos)
    y_pos += line_height
    show_text(content_surface, '• 生命值翻倍：后续生命奖励×2（+15变+30）', (255, 255, 255), small_font, 40, y_pos)
    y_pos += line_height
    show_text(content_surface, '• 子弹清除：一次性清除全场敌人子弹', (255, 255, 255), small_font, 40, y_pos)
    y_pos += line_height
    show_text(content_surface, '• "后续XX+翻倍"指未来该类奖励效果×2', (255, 255, 255), small_font, 40, y_pos)
    y_pos += line_height + 6
    
    # BOSS机制
    show_text(content_surface, '[BOSS三阶段攻击]', (255, 220, 100), content_font, 20, y_pos)
    y_pos += line_height
    show_text(content_surface, '• 阶段1（血量>70%）：散射子弹，速度慢', (255, 255, 255), small_font, 40, y_pos)
    y_pos += line_height
    show_text(content_surface, '• 阶段2（血量40%-70%）：高速子弹，频率增加', (255, 255, 255), small_font, 40, y_pos)
    y_pos += line_height
    show_text(content_surface, '• 阶段3（血量<40%）：全屏弹幕，最猛烈', (255, 255, 255), small_font, 40, y_pos)
    y_pos += line_height
    show_text(content_surface, '• BOSS血量=500×(增长系数^已击败BOSS数)', (255, 255, 255), small_font, 40, y_pos)
    y_pos += line_height + 6
    
    # 操作说明
    show_text(content_surface, '[操作说明]', (255, 220, 100), content_font, 20, y_pos)
    y_pos += line_height
    show_text(content_surface, '• 鼠标移动：控制飞机位置', (255, 255, 255), small_font, 40, y_pos)
    y_pos += line_height
    show_text(content_surface, '• 自动射击：根据攻速自动发射子弹', (255, 255, 255), small_font, 40, y_pos)
    y_pos += line_height
    show_text(content_surface, '• 鼠标左键：使用子弹清除道具（如有）', (255, 255, 255), small_font, 40, y_pos)
    y_pos += line_height
    show_text(content_surface, '• ESC/Enter：暂停/继续游戏', (255, 255, 255), small_font, 40, y_pos)
    y_pos += line_height + 6
    
    # CDK说明
    show_text(content_surface, '[CDK兑换码]', (255, 220, 100), content_font, 20, y_pos)
    y_pos += line_height
    show_text(content_surface, '• 开始界面输入CDK获得初始加成', (255, 255, 255), small_font, 40, y_pos)
    y_pos += line_height
    show_text(content_surface, '• health_10x：初始生命值×10（120→1200）', (255, 255, 255), small_font, 40, y_pos)
    y_pos += line_height
    show_text(content_surface, '• attack_10x：初始攻击力×10（10→100）', (255, 255, 255), small_font, 40, y_pos)
    y_pos += line_height
    show_text(content_surface, '• speed_10x：初始攻速×10（600ms→60ms）', (255, 255, 255), small_font, 40, y_pos)
    y_pos += line_height
    show_text(content_surface, '• CDK只影响初始值，后续奖励叠加', (255, 255, 255), small_font, 40, y_pos)
    
    # 滚动提示
    total_content_height = y_pos
    visible_height = box_height - 70  # 可见区域高度
    if total_content_height > visible_height:
        show_text(content_surface, '↑↓ 或滚轮滚动', (150, 150, 200), get_chinese_font(14), 20, total_content_height + 10)
        total_content_height += 30
    
    # 计算裁剪区域
    clip_y = max(0, min(scroll_offset, total_content_height - visible_height))
    
    # 将内容表面绘制到屏幕上（带裁剪）
    screen.blit(content_surface, (box_x + 20, box_y + 60), 
                (0, clip_y, box_width - 40, min(visible_height, total_content_height - clip_y)))
    
    # 滚动条
    if total_content_height > visible_height:
        scrollbar_x = box_x + box_width - 15
        scrollbar_y = box_y + 60
        scrollbar_width = 8
        scrollbar_height = visible_height
        
        # 滚动条背景
        pygame.draw.rect(screen, (50, 50, 100), 
                        (scrollbar_x, scrollbar_y, scrollbar_width, scrollbar_height))
        
        # 滚动条滑块
        scroll_ratio = visible_height / total_content_height
        thumb_height = max(30, int(scrollbar_height * scroll_ratio))
        thumb_y = scrollbar_y + int((clip_y / (total_content_height - visible_height)) * (scrollbar_height - thumb_height))
        pygame.draw.rect(screen, (150, 200, 255), 
                        (scrollbar_x, thumb_y, scrollbar_width, thumb_height))
    
    # 底部固定按钮区域
    button_y = box_y + box_height + 20
    close_button_x = 350
    close_button_width = 100
    close_button_height = 40
    
    # 按钮背景渐变
    pygame.draw.rect(screen, (150, 0, 0), 
                    (close_button_x, button_y, close_button_width, close_button_height))
    pygame.draw.rect(screen, (200, 50, 50), 
                    (close_button_x + 2, button_y + 2, close_button_width - 4, close_button_height - 4))
    
    # 按钮边框
    pygame.draw.rect(screen, (255, 100, 100), 
                    (close_button_x, button_y, close_button_width, close_button_height), 2)
    
    show_text(screen, '我知道了', (255, 255, 255), content_font, 
             close_button_x + close_button_width // 2, button_y + close_button_height // 2, center=True)
    
    # 返回滚动偏移量供下次使用
    return scroll_offset


def draw_game_over_screen(screen, font, score, wave_num):
    """绘制游戏结束界面"""
    screen.fill((0, 0, 0))
    
    # 标题
    title_font = get_chinese_font(48)
    show_text(screen, '游戏结束', (255, 0, 0), title_font, 400, 150, center=True)
    
    # 统计
    show_text(screen, f'最终分数: {score}', (255, 255, 0), font, 400, 250, center=True)
    show_text(screen, f'到达波数: {wave_num}', (255, 255, 255), font, 400, 290, center=True)
    
    # 重新开始提示
    show_text(screen, '点击重新开始', (0, 255, 0), font, 400, 400, center=True)


def draw_victory_screen(screen, font, score, wave_num):
    """绘制胜利界面（可选）"""
    screen.fill((0, 50, 0))
    
    # 标题
    title_font = get_chinese_font(48)
    show_text(screen, '恭喜通关！', (255, 255, 0), title_font, 400, 150, center=True)
    
    # 统计
    show_text(screen, f'最终分数: {score}', (255, 255, 0), font, 400, 250, center=True)
    show_text(screen, f'完成波数: {wave_num}', (255, 255, 255), font, 400, 290, center=True)
    
    # 继续提示
    show_text(screen, '点击继续挑战', (0, 255, 0), font, 400, 400, center=True)


def draw_leaderboard_screen(screen, leaderboard_data):
    """绘制排行榜界面
    
    Args:
        screen: pygame屏幕对象
        leaderboard_data: {'normal': [...], 'boss': [...]}
    """
    import cfg
    
    # 半透明背景
    overlay = pygame.Surface(cfg.SCREENSIZE)
    overlay.set_alpha(230)
    overlay.fill((20, 20, 60))
    screen.blit(overlay, (0, 0))
    
    # 背景框
    box_x = 80
    box_y = 40
    box_width = 640
    box_height = 500
    
    # 背景框渐变效果
    for i in range(10):
        color = (30 + i * 5, 30 + i * 5, 80 + i * 10)
        pygame.draw.rect(screen, color, 
                        (box_x + i, box_y + i, box_width - i * 2, box_height - i * 2))
    
    # 边框
    pygame.draw.rect(screen, (100, 150, 255), (box_x, box_y, box_width, box_height), 3)
    pygame.draw.rect(screen, (150, 200, 255), (box_x + 3, box_y + 3, box_width - 6, box_height - 6), 2)
    
    # 标题
    title_font = get_chinese_font(36)
    show_text(screen, '[排行榜]', (255, 255, 100), title_font, 400, 65, center=True)
    
    # 分隔线
    pygame.draw.line(screen, (100, 150, 255), (120, 95), (680, 95), 2)
    
    # 内容字体
    content_font = get_chinese_font(20)
    small_font = get_chinese_font(16)
    
    # 普通模式排行榜
    y_pos = 115
    show_text(screen, '[普通模式]', (255, 220, 100), content_font, 120, y_pos)
    y_pos += 35
    
    normal_data = leaderboard_data.get('normal', [])
    if normal_data:
        for i, entry in enumerate(normal_data):
            rank_color = [(255, 215, 0), (192, 192, 192), (205, 127, 50)][i]  # 金银铜
            rank_text = f'#{i+1}'
            score_text = f"分数: {entry['score']}  波数: {entry['wave']}"
            time_text = entry.get('timestamp', '')
            
            show_text(screen, rank_text, rank_color, content_font, 140, y_pos)
            show_text(screen, score_text, (255, 255, 255), small_font, 200, y_pos + 3)
            show_text(screen, time_text, (150, 150, 200), get_chinese_font(14), 200, y_pos + 23)
            y_pos += 50
    else:
        show_text(screen, '暂无记录', (150, 150, 200), small_font, 200, y_pos)
        y_pos += 50
    
    # BOSS战模式排行榜
    y_pos += 10
    show_text(screen, '[BOSS战模式]', (255, 220, 100), content_font, 120, y_pos)
    y_pos += 35
    
    boss_data = leaderboard_data.get('boss', [])
    if boss_data:
        for i, entry in enumerate(boss_data):
            rank_color = [(255, 215, 0), (192, 192, 192), (205, 127, 50)][i]  # 金银铜
            rank_text = f'#{i+1}'
            score_text = f"分数: {entry['score']}  波数: {entry['wave']}"
            time_text = entry.get('timestamp', '')
            
            show_text(screen, rank_text, rank_color, content_font, 140, y_pos)
            show_text(screen, score_text, (255, 255, 255), small_font, 200, y_pos + 3)
            show_text(screen, time_text, (150, 150, 200), get_chinese_font(14), 200, y_pos + 23)
            y_pos += 50
    else:
        show_text(screen, '暂无记录', (150, 150, 200), small_font, 200, y_pos)
        y_pos += 50
    
    # 分隔线
    pygame.draw.line(screen, (100, 150, 255), (120, y_pos + 5), (680, y_pos + 5), 2)
    y_pos += 20
    
    # 关闭按钮
    close_button_x = 350
    close_button_y = y_pos
    close_button_width = 100
    close_button_height = 40
    
    # 按钮背景渐变
    pygame.draw.rect(screen, (150, 0, 0), 
                    (close_button_x, close_button_y, close_button_width, close_button_height))
    pygame.draw.rect(screen, (200, 50, 50), 
                    (close_button_x + 2, close_button_y + 2, close_button_width - 4, close_button_height - 4))
    
    # 按钮边框
    pygame.draw.rect(screen, (255, 100, 100), 
                    (close_button_x, close_button_y, close_button_width, close_button_height), 2)
    
    show_text(screen, '我知道了', (255, 255, 255), content_font, 
             close_button_x + close_button_width // 2, close_button_y + close_button_height // 2, center=True)
    
    # 返回按钮坐标供点击检测使用
    return {
        'x': close_button_x,
        'y': close_button_y,
        'width': close_button_width,
        'height': close_button_height
    }
