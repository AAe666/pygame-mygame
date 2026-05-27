'''精灵类模块（已拆分为独立文件）'''
# 本文件用于兼容旧代码，实际类已拆分到独立模块
from modules.player import Player
from modules.enemy import Enemy, Boss
from modules.bullet import Bullet

__all__ = ['Player', 'Enemy', 'Boss', 'Bullet']
