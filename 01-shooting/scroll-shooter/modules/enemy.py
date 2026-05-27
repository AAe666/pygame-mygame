'''敌人精灵类'''
import pygame
import random
import math
import cfg
from modules.bullet import Bullet


class Enemy(pygame.sprite.Sprite):
    """敌人精灵类"""
    
    # 常量配置
    BOSS_SIZE = (80, 80)
    BOSS_COLOR = (255, 0, 255)
    BOSS_SCORE = 500
    BOSS_SPEED = 1.5
    BOSS_ATTACK_POWER = 20
    BOSS_ENTRY_Y = 100
    
    NORMAL_BASE_SIZE = 30
    NORMAL_COLOR = (255, 0, 0)
    NORMAL_SCORE_BASE = 50
    
    # BOSS阶段颜色
    BOSS_STAGE_COLORS = {
        1: (255, 0, 255),    # 紫色 >70%
        2: (255, 165, 0),    # 橙色 40%-70%
        3: (255, 0, 0)       # 红色 <40%
    }
    
    def __init__(self, x, y, enemy_type='normal', wave_num=1, boss_defeated_count=0, is_boss_mode=False):
        pygame.sprite.Sprite.__init__(self)
        self.type = enemy_type
        self.wave_num = wave_num
        self.boss_defeated_count = boss_defeated_count
        self.is_boss_mode = is_boss_mode  # 是否是BOSS战模式
        
        if enemy_type == 'boss':
            self._init_boss()
        else:
            self._init_normal(wave_num)
        
        self.image = pygame.Surface(self.size)
        self.image.fill(self.color)
        self.rect = self.image.get_rect()
        self.rect.centerx = x
        self.rect.centery = y
        
        self.shoot_timer = 0
        self.shoot_interval = max(800, 2500 - wave_num * 120)
        self.base_shoot_interval = self.shoot_interval
    
    def _init_boss(self):
        """初始化BOSS属性"""
        self.size = self.BOSS_SIZE
        # BOSS血量增长：根据模式选择不同系数
        health_multiplier = cfg.BOSS_HEALTH_MULTIPLIER_BOSS_MODE if self.is_boss_mode else cfg.BOSS_HEALTH_MULTIPLIER
        self.health = cfg.BOSS_BASE_HEALTH * (health_multiplier ** self.boss_defeated_count)
        self.max_health = self.health
        self.speed = self.BOSS_SPEED
        self.score_value = self.BOSS_SCORE
        self.color = self.BOSS_COLOR
        self.attack_power = self.BOSS_ATTACK_POWER
        self.move_direction = 1
        self.move_timer = 0
        self.pattern_rotation = 0
    
    def _init_normal(self, wave_num):
        """初始化普通敌人属性"""
        size_factor = 1 + wave_num * 0.1
        self.size = (int(self.NORMAL_BASE_SIZE * size_factor), int(self.NORMAL_BASE_SIZE * size_factor))
        self.health = 5 + wave_num * 5  # 第一波10血，玩家攻击力10，刚好1枪击杀
        self.max_health = self.health
        self.speed = 3.2 + wave_num * 0.3
        self.score_value = self.NORMAL_SCORE_BASE + wave_num * 10
        self.color = self.NORMAL_COLOR
        self.attack_power = 10 + wave_num * 2
    
    def update(self, scroll_offset, screen_height, screen_width=800):
        """更新敌人位置"""
        if self.type == 'boss':
            return self._update_boss(screen_width)
        else:
            return self._update_normal(screen_height)
    
    def _update_boss(self, screen_width):
        """更新BOSS位置"""
        if self.rect.top < self.BOSS_ENTRY_Y:
            self.rect.y += self.speed
        else:
            self._move_boss(screen_width)
        return True
    
    def _move_boss(self, screen_width):
        """BOSS左右移动"""
        self.move_timer += 1
        
        # 每60帧可能改变方向
        if self.move_timer % 60 == 0 and random.random() < 0.3:
            self.move_direction *= -1
        
        self.rect.x += self.move_direction * 2
        
        # 边界检测
        if self.rect.left < 0:
            self.rect.left = 0
            self.move_direction = 1
        elif self.rect.right > screen_width:
            self.rect.right = screen_width
            self.move_direction = -1
    
    def _update_normal(self, screen_height):
        """更新普通敌人位置"""
        self.rect.y += self.speed
        return self.rect.top <= screen_height
    
    def take_damage(self, damage):
        """受到伤害"""
        self.health -= damage
        return self.health <= 0
    
    def shoot(self, current_time, player_pos=None):
        """敌人射击"""
        if current_time - self.shoot_timer < self.shoot_interval:
            return []
        
        self.shoot_timer = current_time
        
        if self.type == 'boss':
            return self._boss_shoot(player_pos)
        else:
            bullet = self._shoot_single(player_pos)
            return [bullet] if bullet else []
    
    def _boss_shoot(self, player_pos):
        """BOSS射击逻辑"""
        health_ratio = self.health / self.max_health
        
        if health_ratio > 0.7:
            # 阶段1: 散射
            self.shoot_interval = self.base_shoot_interval
            return self._shoot_triple(player_pos)
        elif health_ratio > 0.4:
            # 阶段2: 高速子弹
            self._update_stage2_interval()
            return self._shoot_fast(player_pos)
        else:
            # 阶段3: 全屏弹幕
            self._update_stage3_interval()
            return self._shoot_pattern()
    
    def _update_stage2_interval(self):
        """更新阶段2射击间隔"""
        x = self.boss_defeated_count
        frequency_multiplier = cfg.BOSS_STAGE2_FREQ_BASE + cfg.BOSS_STAGE2_FREQ_GROWTH * x
        self.shoot_interval = max(cfg.BOSS_STAGE2_MIN_INTERVAL, 
                                 int(self.base_shoot_interval / frequency_multiplier))
    
    def _update_stage3_interval(self):
        """更新阶段3射击间隔"""
        x = self.boss_defeated_count
        frequency_multiplier = cfg.BOSS_STAGE3_FREQ_BASE + cfg.BOSS_STAGE3_FREQ_GROWTH * x
        self.shoot_interval = max(cfg.BOSS_STAGE3_MIN_INTERVAL, 
                                 int(self.base_shoot_interval / frequency_multiplier))
    
    def _calculate_direction(self, player_pos, bullet_speed):
        """计算子弹方向"""
        if player_pos:
            dx = player_pos[0] - self.rect.centerx
            dy = player_pos[1] - self.rect.centery
            distance = max(1, math.sqrt(dx**2 + dy**2))
            return (dx / distance) * bullet_speed, (dy / distance) * bullet_speed
        return 0, bullet_speed
    
    def _shoot_single(self, player_pos):
        """普通射击：单颗子弹"""
        dx, dy = self._calculate_direction(player_pos, 5)
        
        # 20%概率添加随机偏移
        if random.random() < 0.2:
            offset_x = random.uniform(-50, 50)
            offset_y = random.uniform(-50, 50)
            target_x = player_pos[0] + offset_x if player_pos else self.rect.centerx
            target_y = player_pos[1] + offset_y if player_pos else self.rect.bottom
            dx = target_x - self.rect.centerx
            dy = target_y - self.rect.centery
            distance = max(1, math.sqrt(dx**2 + dy**2))
            dx = (dx / distance) * 5
            dy = (dy / distance) * 5
        
        return Bullet(self.rect.centerx, self.rect.bottom, dx, dy, self.attack_power, is_enemy=True)
    
    def _shoot_triple(self, player_pos):
        """BOSS阶段1：散射子弹"""
        bullets = []
        bullet_speed = 5
        spread_angle = 15
        bullet_count = cfg.BOSS_STAGE1_BULLET_BASE + self.boss_defeated_count * cfg.BOSS_STAGE1_BULLET_GROWTH
        
        base_angle = self._get_base_angle(player_pos)
        
        for i in range(bullet_count):
            angle = base_angle + (i - (bullet_count - 1) / 2) * spread_angle
            rad = math.radians(angle)
            dx = math.cos(rad) * bullet_speed
            dy = math.sin(rad) * bullet_speed
            bullets.append(Bullet(self.rect.centerx, self.rect.centery, dx, dy, self.attack_power, is_enemy=True))
        
        return bullets
    
    def _shoot_fast(self, player_pos):
        """BOSS阶段2：高速子弹"""
        bullets = []
        bullet_speed = cfg.BOSS_STAGE2_BULLET_SPEED
        spread_angle = 12
        bullet_count = cfg.BOSS_STAGE2_BULLET_BASE + self.boss_defeated_count * cfg.BOSS_STAGE2_BULLET_GROWTH
        
        base_angle = self._get_base_angle(player_pos)
        
        for i in range(bullet_count):
            angle = base_angle + (i - (bullet_count - 1) / 2) * spread_angle
            rad = math.radians(angle)
            dx = math.cos(rad) * bullet_speed
            dy = math.sin(rad) * bullet_speed
            bullets.append(Bullet(self.rect.centerx, self.rect.centery, dx, dy, self.attack_power, is_enemy=True))
        
        return bullets
    
    def _shoot_pattern(self):
        """BOSS阶段3：全屏弹幕"""
        bullets = []
        bullet_speed = cfg.BOSS_STAGE3_BULLET_SPEED
        bullet_count = cfg.BOSS_STAGE3_BULLET_BASE + self.boss_defeated_count * cfg.BOSS_STAGE3_BULLET_GROWTH
        
        self.pattern_rotation += 7.5
        
        for i in range(bullet_count):
            angle = (360 / bullet_count) * i + self.pattern_rotation
            rad = math.radians(angle)
            dx = math.cos(rad) * bullet_speed
            dy = math.sin(rad) * bullet_speed
            bullets.append(Bullet(self.rect.centerx, self.rect.centery, dx, dy, self.attack_power, is_enemy=True))
        
        return bullets
    
    def _get_base_angle(self, player_pos):
        """获取基础射击角度"""
        if player_pos:
            dx = player_pos[0] - self.rect.centerx
            dy = player_pos[1] - self.rect.centery
            return math.degrees(math.atan2(dy, dx))
        return 90  # 默认向下
    
    def draw(self, screen):
        """绘制敌人"""
        if self.type == 'boss':
            self._update_boss_color()
        
        screen.blit(self.image, self.rect)
        
        # 始终显示血条（包括满血）
        self._draw_health_bar(screen)
    
    def _update_boss_color(self):
        """更新BOSS颜色"""
        health_ratio = self.health / self.max_health
        if health_ratio > 0.7:
            color = self.BOSS_STAGE_COLORS[1]
        elif health_ratio > 0.4:
            color = self.BOSS_STAGE_COLORS[2]
        else:
            color = self.BOSS_STAGE_COLORS[3]
        
        self.image.fill(color)
    
    def _draw_health_bar(self, screen):
        """绘制血条（带数值）"""
        from modules.utils import get_chinese_font, show_text
        
        health_ratio = self.health / self.max_health
        bar_width = self.size[0]
        bar_height = 8
        bar_y = self.rect.top - 15
        
        # 血条背景
        pygame.draw.rect(screen, (40, 40, 40), 
                        (self.rect.left, bar_y, bar_width, bar_height))
        
        # 血条填充（根据阶段变色）
        if health_ratio > 0.7:
            bar_color = (0, 200, 0)  # 绿色
        elif health_ratio > 0.4:
            bar_color = (200, 200, 0)  # 黄色
        else:
            bar_color = (200, 0, 0)  # 红色
        
        fill_width = int(bar_width * health_ratio)
        if fill_width > 0:
            pygame.draw.rect(screen, bar_color, 
                            (self.rect.left, bar_y, fill_width, bar_height))
        
        # 边框
        pygame.draw.rect(screen, (255, 255, 255), 
                        (self.rect.left, bar_y, bar_width, bar_height), 1)
        
        # 显示数值（血条上方，不重叠）
        health_font = get_chinese_font(12)
        health_text = f'{int(self.health)}/{int(self.max_health)}'
        
        # 添加文字阴影（血条上方10像素）
        show_text(screen, health_text, (0, 0, 0), health_font, 
                 self.rect.centerx + 1, bar_y - 12 + 1, center=True)
        show_text(screen, health_text, (255, 255, 255), health_font, 
                 self.rect.centerx, bar_y - 12, center=True)
