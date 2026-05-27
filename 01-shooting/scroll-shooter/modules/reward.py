'''奖励系统'''
import pygame
import random
from modules.utils import get_chinese_font


class Reward:
    """奖励选项类"""
    
    # 常量配置
    BUTTON_WIDTH = 280
    BUTTON_HEIGHT = 80
    BUTTON_Y = 250
    BUTTON_GAP = 40
    TITLE_Y = 100
    
    # 颜色配置
    NORMAL_BG_COLOR = (70, 70, 200)
    NORMAL_SELECTED_COLOR = (100, 100, 255)
    NORMAL_BORDER_COLOR = (255, 255, 255)
    
    BOSS_BG_COLOR = (139, 105, 20)
    BOSS_SELECTED_COLOR = (180, 140, 0)
    BOSS_BORDER_COLOR = (255, 215, 0)  # 金色
    BOSS_TITLE_COLOR = (255, 215, 0)
    
    # 奖励配置
    MAX_MULTI_SHOT = 6
    HEAL_CHANCE = 0.2
    HEAL_VALUE = 100  # 固定回复100生命值
    
    # 基础奖励数值
    BASE_ATTACK_POWER = 3
    BASE_ATTACK_SPEED_REDUCE = 36  # 每次减少36ms（6%提升）
    BASE_MAX_HEALTH = 15
    
    def __init__(self, screen_width, screen_height, reward_count=1, player=None, 
                 is_boss_reward=False, player_stats=None):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.reward_count = reward_count
        self.current_reward = 1
        self.player = player
        self.is_boss_reward = is_boss_reward
        self.player_stats = player_stats or {}
        self.options = self.generate_options()
        self.selected = -1
        
        self.title_font = get_chinese_font(36)
        self.button_font = get_chinese_font(24)
    
    def generate_options(self):
        """生成奖励选项"""
        if self.is_boss_reward:
            return self._generate_boss_options()
        return self._generate_normal_options()
    
    def _generate_normal_options(self):
        """生成普通奖励选项"""
        # 根据BOSS奖励调整基础数值
        attack_power = self._get_attack_power_value()
        attack_speed_reduce = self._get_attack_speed_value()
        max_health = self._get_max_health_value()
        
        # 计算攻速提升百分比（基于初始600ms）
        initial_attack_speed = 600
        attack_speed_percent = int(attack_speed_reduce / initial_attack_speed * 100)
        
        # 构建奖励池
        normal_options = [
            ('attack_power', f'攻击力 +{attack_power}', attack_power),
            ('attack_speed', f'攻击速度 +{attack_speed_percent}%', attack_speed_reduce),
            ('max_health', f'最大生命值 +{max_health}', max_health)
        ]
        
        # 多段攻击（有限制）
        if self._can_add_multi_shot():
            normal_options.append(('multi_shot', '多段攻击 +1', 1))
        
        # 根据血量决定是否添加回血
        return self._select_normal_options(normal_options)
    
    def _get_attack_power_value(self):
        """获取攻击力数值"""
        return self.BASE_ATTACK_POWER * 2 if self.player_stats.get('has_attack_power_double') else self.BASE_ATTACK_POWER
    
    def _get_attack_speed_value(self):
        """获取攻速数值（减少的毫秒数）"""
        return self.BASE_ATTACK_SPEED_REDUCE * 2 if self.player_stats.get('has_attack_speed_double') else self.BASE_ATTACK_SPEED_REDUCE
    
    def _get_max_health_value(self):
        """获取生命值数值"""
        return self.BASE_MAX_HEALTH * 2 if self.player_stats.get('has_max_health_double') else self.BASE_MAX_HEALTH
    
    def _can_add_multi_shot(self):
        """检查是否可以添加多段攻击"""
        return self.player_stats.get('multi_shot_count', 0) < self.MAX_MULTI_SHOT
    
    def _select_normal_options(self, normal_options):
        """选择奖励选项"""
        is_full_health = self.player and self.player.health >= self.player.max_health
        
        if is_full_health:
            return self._select_from_options(normal_options, 2)
        elif random.random() < self.HEAL_CHANCE:
            heal_option = ('heal', '回复 100 生命值', self.HEAL_VALUE)
            selected = self._select_from_options(normal_options, 1)
            return selected + [heal_option]
        else:
            return self._select_from_options(normal_options, 2)
    
    def _select_from_options(self, options, count):
        """从选项中随机选择"""
        random.shuffle(options)
        return options[:count]
    
    def _generate_boss_options(self):
        """生成BOSS奖励选项"""
        boss_options = []
        
        # 5种BOSS奖励
        boss_reward_configs = [
            ('has_bullet_tracking', 'bullet_tracking', 'tracking.png', '子弹追踪'),
            ('has_attack_power_double', 'attack_power_double', 'attack.png', '后续攻击力+翻倍'),
            ('has_attack_speed_double', 'attack_speed_double', 'speed.png', '后续攻速提升+翻倍'),
            ('has_max_health_double', 'max_health_double', 'health.png', '后续生命值+翻倍'),
            ('has_bullet_clear', 'bullet_clear', 'clear.png', '子弹清除（一次性）')
        ]
        
        for stat_key, option_type, icon_file, description in boss_reward_configs:
            # 子弹清除可以重复获取，其他不能重复
            if stat_key == 'has_bullet_clear':
                # 只要拥有过就可以再次获取（不管当前是否可用）
                boss_options.append((option_type, icon_file, description, None))
            elif not self.player_stats.get(stat_key, False):
                boss_options.append((option_type, icon_file, description, None))
        
        # 随机选2个
        return self._select_from_options(boss_options, min(2, len(boss_options)))
    
    def draw(self, screen):
        """绘制奖励选择界面"""
        self._draw_overlay(screen)
        self._draw_title(screen)
        self._draw_buttons(screen)
    
    def _draw_overlay(self, screen):
        """绘制半透明背景"""
        overlay = pygame.Surface((self.screen_width, self.screen_height))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))
    
    def _draw_title(self, screen):
        """绘制标题"""
        if self.is_boss_reward:
            title_text = '[BOSS奖励选择]'
            title_color = self.BOSS_TITLE_COLOR
        else:
            title_text = f'选择奖励 ({self.current_reward}/{self.reward_count})'
            title_color = (255, 255, 255)
        
        title = self.title_font.render(title_text, True, title_color)
        title_rect = title.get_rect(center=(self.screen_width // 2, self.TITLE_Y))
        screen.blit(title, title_rect)
    
    def _draw_buttons(self, screen):
        """绘制按钮"""
        start_x = self._calculate_start_x()
        
        for i, option in enumerate(self.options):
            button_x = start_x + i * (self.BUTTON_WIDTH + self.BUTTON_GAP)
            # 兼容普通奖励(3元组)和BOSS奖励(4元组)
            description = option[2] if len(option) > 2 else option[1]
            self._draw_single_button(screen, button_x, i, description)
    
    def _calculate_start_x(self):
        """计算按钮组起始X坐标"""
        total_width = self.BUTTON_WIDTH * 2 + self.BUTTON_GAP
        return (self.screen_width - total_width) // 2
    
    def _draw_single_button(self, screen, button_x, index, description):
        """绘制单个按钮"""
        bg_color, border_color = self._get_button_colors(index)
        
        # 获取选项数据
        option = self.options[index]
        
        # 兼容普通奖励(3元组: type, desc, value)和BOSS奖励(4元组: type, icon, desc, value)
        if len(option) == 4:
            # BOSS奖励
            icon_file = option[1]
            text_desc = option[2]
        else:
            # 普通奖励
            icon_file = None
            text_desc = option[1]
        
        # 背景
        pygame.draw.rect(screen, bg_color, 
                        (button_x, self.BUTTON_Y, self.BUTTON_WIDTH, self.BUTTON_HEIGHT))
        pygame.draw.rect(screen, border_color, 
                        (button_x, self.BUTTON_Y, self.BUTTON_WIDTH, self.BUTTON_HEIGHT), 3)
        
        # 如果有图标文件，绘制图标
        if icon_file and icon_file.endswith('.png'):
            from modules.utils import load_icon
            icon = load_icon(icon_file, (48, 48))  # 奖励按钮图标：48x48
            # 图标居中偏上
            icon_x = button_x + (self.BUTTON_WIDTH - 48) // 2
            icon_y = self.BUTTON_Y + 8
            screen.blit(icon, (icon_x, icon_y))
            
            # 文字在图标下方
            text = self.button_font.render(text_desc, True, (255, 255, 255))
            text_rect = text.get_rect(center=(button_x + self.BUTTON_WIDTH // 2, 
                                             self.BUTTON_Y + 65))
            screen.blit(text, text_rect)
        else:
            # 没有图标，只显示文字（居中）
            text = self.button_font.render(text_desc, True, (255, 255, 255))
            text_rect = text.get_rect(center=(button_x + self.BUTTON_WIDTH // 2, 
                                             self.BUTTON_Y + self.BUTTON_HEIGHT // 2))
            screen.blit(text, text_rect)
    
    def _get_button_colors(self, index):
        """获取按钮颜色"""
        is_selected = (index == self.selected)
        
        if self.is_boss_reward:
            bg_color = self.BOSS_SELECTED_COLOR if is_selected else self.BOSS_BG_COLOR
            border_color = self.BOSS_BORDER_COLOR
        else:
            bg_color = self.NORMAL_SELECTED_COLOR if is_selected else self.NORMAL_BG_COLOR
            border_color = self.NORMAL_BORDER_COLOR
        
        return bg_color, border_color
    
    def check_click(self, mouse_pos):
        """检查点击了哪个选项"""
        start_x = self._calculate_start_x()
        
        for i in range(len(self.options)):
            button_x = start_x + i * (self.BUTTON_WIDTH + self.BUTTON_GAP)
            if (button_x <= mouse_pos[0] <= button_x + self.BUTTON_WIDTH and
                self.BUTTON_Y <= mouse_pos[1] <= self.BUTTON_Y + self.BUTTON_HEIGHT):
                return i
        return -1
    
    def apply_reward(self, player, option_index, player_stats=None):
        """应用奖励"""
        if option_index < 0 or option_index >= len(self.options):
            return
        
        # 兼容普通奖励(3元组)和BOSS奖励(4元组)
        option = self.options[option_index]
        if len(option) == 4:
            # BOSS奖励: (type, icon, desc, value)
            option_type, icon_file, description, value = option
        else:
            # 普通奖励: (type, desc, value)
            option_type, description, value = option
        
        # 普通奖励
        if option_type == 'attack_power':
            player.attack_power += value
        elif option_type == 'attack_speed':
            # 攻速提升：减少固定射击间隔（毫秒），数值越小射速越快
            player.attack_speed = max(50, player.attack_speed - value)
            print(f"  ⚡ 攻速提升：{player.attack_speed}ms（-{value}ms）")
        elif option_type == 'multi_shot':
            player.multi_shot += int(value)
            if player_stats:
                player_stats['multi_shot_count'] = player_stats.get('multi_shot_count', 0) + 1
        elif option_type == 'heal':
            # 回复固定生命值
            player.health = min(player.max_health, player.health + value)
            print(f"  💚 回复生命值：+{value}")
        elif option_type == 'max_health':
            player.max_health += value
            player.health += value
        # BOSS奖励
        elif option_type == 'bullet_tracking':
            if player_stats:
                player_stats['has_bullet_tracking'] = True
                print("  ✅ 获得BOSS奖励：子弹追踪！")
        elif option_type == 'attack_power_double':
            if player_stats:
                player_stats['has_attack_power_double'] = True
                print("  ✅ 获得BOSS奖励：攻击力获得 x2！")
        elif option_type == 'attack_speed_double':
            # 攻速提升翻俻：每次减少的间隔从20ms变为40ms
            if player_stats:
                player_stats['has_attack_speed_double'] = True
                print("  ✅ 获得BOSS奖励：攻速提升 x2！（后续每次-40ms）")
        elif option_type == 'max_health_double':
            if player_stats:
                player_stats['has_max_health_double'] = True
                print("  ✅ 获得BOSS奖励：生命提升 x2！")
        elif option_type == 'bullet_clear':
            if player_stats:
                player_stats['has_bullet_clear'] = True
                player_stats['bullet_clear_available'] = True  # 可以使用
                print("  ✅ 获得BOSS奖励：子弹清除（一次性）！")
