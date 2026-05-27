'''玩家精灵类'''
import pygame
from modules.bullet import Bullet
from modules.utils import get_chinese_font, show_text


class Player(pygame.sprite.Sprite):
    """玩家精灵类"""
    
    # 常量配置
    WIDTH = 40
    HEIGHT = 40
    COLOR = (0, 255, 0)  # 绿色
    BULLET_SPEED = 9
    HEALTH_BAR_WIDTH = 60
    HEALTH_BAR_HEIGHT = 8
    
    def __init__(self):
        pygame.sprite.Sprite.__init__(self)
        self.image = pygame.Surface((self.WIDTH, self.HEIGHT))
        self.image.fill(self.COLOR)
        self.rect = self.image.get_rect()
        self.rect.centerx = 400
        self.rect.centery = 450
        
        # 玩家属性
        self.attack_power = 10
        self.attack_speed = 600  # 初始射击间隔600ms（降低一半，给玩家成长空间）
        self.multi_shot = 1
        self.last_shot_time = 0
        self.score = 0
        self.health = 120  # 从100提高到120（初始更耐打）
        self.max_health = 120  # 从100提高到120
        
    def update(self, mouse_pos, screen_width, screen_height):
        """更新位置，跟随鼠标"""
        self.rect.centerx = mouse_pos[0]
        self.rect.centery = mouse_pos[1]
        
        # 限制在屏幕范围内
        self.rect.left = max(0, self.rect.left)
        self.rect.right = min(screen_width, self.rect.right)
        self.rect.top = max(0, self.rect.top)
        self.rect.bottom = min(screen_height, self.rect.bottom)
    
    def shoot(self, current_time):
        """射击"""
        if current_time - self.last_shot_time < self.attack_speed:
            return []
        
        self.last_shot_time = current_time
        bullets = []
        
        if self.multi_shot == 1:
            # 单发
            bullet = Bullet(self.rect.centerx, self.rect.top, 0, -self.BULLET_SPEED, self.attack_power)
            bullets.append(bullet)
        else:
            # 多段攻击：垂直向前，水平分散
            bullets = self._shoot_multi()
        
        return bullets
    
    def _shoot_multi(self):
        """多段攻击"""
        bullets = []
        bullet_spacing = 15
        total_width = (self.multi_shot - 1) * bullet_spacing
        start_x = self.rect.centerx - total_width / 2
        
        for i in range(self.multi_shot):
            x_pos = start_x + i * bullet_spacing
            bullet = Bullet(x_pos, self.rect.top, 0, -self.BULLET_SPEED, self.attack_power)
            bullets.append(bullet)
        
        return bullets
    
    def draw(self, screen):
        """绘制玩家和血条"""
        screen.blit(self.image, self.rect)
        self._draw_health_bar(screen)
    
    def _draw_health_bar(self, screen):
        """绘制血条（带数值）"""
        health_ratio = self.health / self.max_health if self.max_health > 0 else 0
        bar_x = self.rect.centerx - self.HEALTH_BAR_WIDTH // 2
        # 血条放在头顶上方
        bar_y = self.rect.top - 18
        
        # 血条背景（深色）
        pygame.draw.rect(screen, (40, 40, 40), 
                        (bar_x, bar_y, self.HEALTH_BAR_WIDTH, self.HEALTH_BAR_HEIGHT))
        
        # 血条填充（根据血量比例变色）
        if health_ratio > 0.6:
            bar_color = (0, 200, 0)  # 绿色
        elif health_ratio > 0.3:
            bar_color = (200, 200, 0)  # 黄色
        else:
            bar_color = (200, 0, 0)  # 红色
        
        fill_width = int(self.HEALTH_BAR_WIDTH * health_ratio)
        if fill_width > 0:
            pygame.draw.rect(screen, bar_color, 
                            (bar_x + 1, bar_y + 1, fill_width - 2, self.HEALTH_BAR_HEIGHT - 2))
        
        # 边框
        pygame.draw.rect(screen, (255, 255, 255), 
                        (bar_x, bar_y, self.HEALTH_BAR_WIDTH, self.HEALTH_BAR_HEIGHT), 1)
        
        # 显示数值（血条上方，不重叠）
        health_font = get_chinese_font(12)
        health_text = f'{int(self.health)}/{int(self.max_health)}'
        
        # 添加文字阴影（血条上方10像素）
        show_text(screen, health_text, (0, 0, 0), health_font, 
                 self.rect.centerx + 1, bar_y - 12 + 1, center=True)
        show_text(screen, health_text, (255, 255, 255), health_font, 
                 self.rect.centerx, bar_y - 12, center=True)
