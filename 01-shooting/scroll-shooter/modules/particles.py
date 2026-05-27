'''粒子系统和爆炸效果'''
import pygame
import random
import math


class Particle:
    """单个粒子"""
    
    def __init__(self, x, y, color, speed, angle, lifetime, size=3, gravity=0.1):
        self.x = x
        self.y = y
        self.color = color
        self.speed = speed
        self.angle = angle
        self.lifetime = lifetime  # 存活帧数
        self.max_lifetime = lifetime
        self.size = size
        self.gravity = gravity
        
        # 计算速度分量
        self.vx = math.cos(math.radians(angle)) * speed
        self.vy = math.sin(math.radians(angle)) * speed
        
        self.alpha = 255  # 透明度
    
    def update(self):
        """更新粒子状态"""
        self.x += self.vx
        self.y += self.vy
        self.vy += self.gravity  # 重力
        self.lifetime -= 1
        
        # 淡出效果
        self.alpha = int(255 * (self.lifetime / self.max_lifetime))
        self.size = max(1, int(self.size * (self.lifetime / self.max_lifetime)))
        
        return self.lifetime > 0
    
    def draw(self, screen):
        """绘制粒子"""
        if self.alpha > 0 and self.size > 0:
            # 创建带透明度的表面
            particle_surface = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
            particle_surface.set_alpha(self.alpha)
            pygame.draw.circle(particle_surface, self.color, 
                             (self.size, self.size), self.size)
            screen.blit(particle_surface, 
                       (int(self.x - self.size), int(self.y - self.size)))


class Explosion:
    """爆炸效果"""
    
    # 爆炸颜色配置
    EXPLOSION_COLORS = [
        (255, 100, 0),   # 橙色
        (255, 200, 0),   # 黄色
        (255, 50, 0),    # 红色
        (255, 150, 50),  # 浅橙
        (255, 255, 100)  # 亮黄
    ]
    
    SPARK_COLORS = [
        (255, 255, 255),  # 白色火花
        (255, 255, 200),  # 淡黄火花
        (200, 200, 255)   # 淡蓝火花
    ]
    
    def __init__(self, x, y, size='medium'):
        self.particles = []
        self.done = False
        
        # 根据爆炸大小配置
        if size == 'small':
            particle_count = 15
            speed_range = (2, 5)
            size_range = (2, 4)
        elif size == 'medium':
            particle_count = 25
            speed_range = (3, 7)
            size_range = (3, 6)
        elif size == 'large':
            particle_count = 40
            speed_range = (4, 10)
            size_range = (4, 8)
        else:  # boss
            particle_count = 60
            speed_range = (5, 12)
            size_range = (5, 10)
        
        self._create_explosion(x, y, particle_count, speed_range, size_range)
    
    def _create_explosion(self, x, y, count, speed_range, size_range):
        """创建爆炸粒子"""
        # 主爆炸粒子
        for _ in range(count):
            angle = random.uniform(0, 360)
            speed = random.uniform(*speed_range)
            color = random.choice(self.EXPLOSION_COLORS)
            size = random.randint(*size_range)
            lifetime = random.randint(20, 40)
            
            self.particles.append(Particle(x, y, color, speed, angle, lifetime, size))
        
        # 火花效果
        spark_count = count // 2
        for _ in range(spark_count):
            angle = random.uniform(0, 360)
            speed = random.uniform(speed_range[1], speed_range[1] * 1.5)
            color = random.choice(self.SPARK_COLORS)
            lifetime = random.randint(10, 20)
            
            self.particles.append(Particle(x, y, color, speed, angle, lifetime, 2, 0.05))
    
    def update(self):
        """更新所有粒子"""
        active_particles = []
        
        for particle in self.particles:
            if particle.update():
                active_particles.append(particle)
        
        self.particles = active_particles
        self.done = len(self.particles) == 0
    
    def draw(self, screen):
        """绘制所有粒子"""
        for particle in self.particles:
            particle.draw(screen)


class ParticleSystem:
    """粒子系统管理器"""
    
    def __init__(self):
        self.explosions = []
    
    def add_explosion(self, x, y, size='medium'):
        """添加爆炸效果"""
        self.explosions.append(Explosion(x, y, size))
    
    def update(self):
        """更新所有爆炸效果"""
        active_explosions = []
        
        for explosion in self.explosions:
            explosion.update()
            if not explosion.done:
                active_explosions.append(explosion)
        
        self.explosions = active_explosions
    
    def draw(self, screen):
        """绘制所有爆炸效果"""
        for explosion in self.explosions:
            explosion.draw(screen)
    
    def clear(self):
        """清除所有粒子"""
        self.explosions.clear()
