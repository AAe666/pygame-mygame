'''子弹精灵类'''
import pygame


class Bullet(pygame.sprite.Sprite):
    """子弹精灵类"""
    
    # 常量配置
    ENEMY_SIZE = (6, 6)
    ENEMY_COLOR = (255, 255, 0)  # 黄色
    PLAYER_SIZE = (4, 12)
    PLAYER_COLOR = (0, 255, 255)  # 青色
    SCREEN_WIDTH = 800
    SCREEN_HEIGHT = 600
    
    def __init__(self, x, y, dx=0, dy=-8, power=10, is_enemy=False):
        pygame.sprite.Sprite.__init__(self)
        self.is_enemy = is_enemy
        self.power = power
        self.dx = dx
        self.dy = dy
        
        # 根据类型设置外观
        if is_enemy:
            self.size = self.ENEMY_SIZE
            self.color = self.ENEMY_COLOR
        else:
            self.size = self.PLAYER_SIZE
            self.color = self.PLAYER_COLOR
        
        self.image = pygame.Surface(self.size)
        self.image.fill(self.color)
        self.rect = self.image.get_rect()
        self.rect.centerx = x
        self.rect.centery = y
    
    def update(self):
        """更新子弹位置"""
        self.rect.x += self.dx
        self.rect.y += self.dy
        
        # 检查是否超出屏幕
        return not (self.rect.bottom < 0 or 
                   self.rect.top > self.SCREEN_HEIGHT or 
                   self.rect.right < 0 or 
                   self.rect.left > self.SCREEN_WIDTH)
    
    def draw(self, screen):
        """绘制子弹"""
        screen.blit(self.image, self.rect)
