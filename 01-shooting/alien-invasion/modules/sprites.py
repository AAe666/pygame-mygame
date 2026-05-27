'''游戏精灵类'''
import pygame
import random


'''敌方精灵'''
class enemySprite(pygame.sprite.Sprite):
    def __init__(self, enemy_type, number, color, bullet_color):
        pygame.sprite.Sprite.__init__(self)
        self.type = enemy_type
        self.number = number
        self.color = color
        self.bullet_color = bullet_color
        
        # 根据类型设置大小和奖励
        if enemy_type == 'small':
            self.size = (20, 20)
            self.reward = 30
        elif enemy_type == 'medium':
            self.size = (30, 30)
            self.reward = 20
        else:  # large
            self.size = (40, 40)
            self.reward = 10
        
        self.image = pygame.Surface(self.size)
        self.image.fill(color)
        self.rect = self.image.get_rect()
        
        # 移动相关
        self.speed = 2
        self.change_count = 6
        self.one_dead = False
        
    def shot(self):
        '''射击'''
        bullet = bulletSprite(self.bullet_color, 'enemy')
        bullet.rect.centerx = self.rect.centerx
        bullet.rect.centery = self.rect.bottom
        return bullet
    
    def update(self, direction, screen_height):
        '''更新位置'''
        if direction == 'right':
            self.rect.x += self.speed
        elif direction == 'left':
            self.rect.x -= self.speed
        elif direction == 'down':
            self.rect.y += 20
            if self.rect.bottom > screen_height - 50:
                return True
        return False
    
    def boom(self, screen):
        '''爆炸效果'''
        if not self.one_dead:
            self.one_dead = True
            self.change_count = 6
        
        if self.change_count > 0:
            # 简单的爆炸动画效果
            alpha = int(255 * (self.change_count / 6))
            self.image.set_alpha(alpha)
            self.change_count -= 1
            return False
        else:
            return True
    
    def draw(self, screen):
        '''绘制精灵'''
        screen.blit(self.image, self.rect)


'''UFO精灵'''
class ufoSprite(pygame.sprite.Sprite):
    def __init__(self, color):
        pygame.sprite.Sprite.__init__(self)
        self.color = color
        self.size = (50, 25)
        self.image = pygame.Surface(self.size)
        self.image.fill(color)
        self.rect = self.image.get_rect()
        self.rect.y = 50
        self.reward = 100
        
        self.speed = 3
        self.is_dead = False
        self.has_boomed = False
        self.one_dead = False
        self.change_count = 10
    
    def update(self, screen_width):
        '''更新位置'''
        self.rect.x += self.speed
        if self.rect.left > screen_width:
            self.rect.x = -self.rect.width
    
    def boom(self, screen):
        '''爆炸效果'''
        if not self.one_dead:
            self.one_dead = True
            self.change_count = 10
        
        if self.change_count > 0:
            alpha = int(255 * (self.change_count / 10))
            self.image.set_alpha(alpha)
            self.change_count -= 1
            return False
        else:
            return True
    
    def draw(self, screen):
        '''绘制精灵'''
        screen.blit(self.image, self.rect)


'''我方飞船精灵'''
class aircraftSprite(pygame.sprite.Sprite):
    def __init__(self, color, bullet_color):
        pygame.sprite.Sprite.__init__(self)
        self.color = color
        self.bullet_color = bullet_color
        self.size = (40, 40)
        self.image = pygame.Surface(self.size)
        self.image.fill(color)
        self.rect = self.image.get_rect()
        self.rect.bottom = 580
        self.rect.centerx = 400
        
        self.speed = 5
        self.score = 0
        self.old_score = 0
        self.num_life = 3
        self.max_num_life = 5
        self.one_dead = False
        self.change_count = 10
    
    def shot(self):
        '''射击'''
        bullet = bulletSprite(self.bullet_color, 'my')
        bullet.rect.centerx = self.rect.centerx
        bullet.rect.top = self.rect.top
        return bullet
    
    def update(self, screen_width):
        '''更新位置(跟随鼠标)'''
        pos = pygame.mouse.get_pos()
        self.rect.centerx = pos[0]
        # 限制在屏幕范围内
        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > screen_width:
            self.rect.right = screen_width
    
    def boom(self, screen):
        '''爆炸效果'''
        if not self.one_dead:
            self.one_dead = True
            self.change_count = 10
        
        if self.change_count > 0:
            alpha = int(255 * (self.change_count / 10))
            self.image.set_alpha(alpha)
            self.change_count -= 1
            return False
        else:
            return True
    
    def resetBoom(self):
        '''重置爆炸状态'''
        self.one_dead = False
        self.change_count = 10
        self.image.set_alpha(255)
        self.rect.centerx = 400
    
    def draw(self, screen):
        '''绘制精灵'''
        screen.blit(self.image, self.rect)


'''子弹精灵'''
class bulletSprite(pygame.sprite.Sprite):
    def __init__(self, color, bullet_type):
        pygame.sprite.Sprite.__init__(self)
        self.color = color
        self.type = bullet_type
        self.size = (4, 10)
        self.image = pygame.Surface(self.size)
        self.image.fill(color)
        self.rect = self.image.get_rect()
        self.speed = 8 if bullet_type == 'my' else -5
    
    def update(self, screen_height=None):
        '''更新位置'''
        if self.type == 'my':
            self.rect.y -= self.speed
            if self.rect.bottom < 0:
                return True
        else:
            self.rect.y -= self.speed
            if screen_height and self.rect.top > screen_height:
                return True
        return False
    
    def draw(self, screen):
        '''绘制子弹'''
        screen.blit(self.image, self.rect)
