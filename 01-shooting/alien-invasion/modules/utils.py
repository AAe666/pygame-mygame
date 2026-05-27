'''工具函数'''
import pygame


'''显示文字'''
def showText(screen, text, color, font, x, y):
    text_render = font.render(text, True, color)
    screen.blit(text_render, (x, y))


'''显示生命值'''
def showLife(screen, num_life, color):
    size = (20, 20)
    for i in range(num_life):
        life_image = pygame.Surface(size)
        life_image.fill(color)
        life_rect = life_image.get_rect()
        life_rect.left = 10 + i * 25
        life_rect.top = 40
        screen.blit(life_image, life_rect)


'''结束界面'''
def endInterface(screen, bg_color, is_win):
    clock = pygame.time.Clock()
    font = pygame.font.SysFont('arial', 30)
    
    running = True
    while running:
        screen.fill(bg_color)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                running = False
        
        # 显示胜利或失败信息
        if is_win:
            text1 = showText(screen, 'YOU WIN!', (255, 255, 0), font, 300, 250)
        else:
            text1 = showText(screen, 'GAME OVER!', (255, 0, 0), font, 270, 250)
        
        text2 = showText(screen, 'Click to Restart', (255, 255, 255), font, 280, 320)
        text3 = showText(screen, 'Press ESC to Quit', (255, 255, 255), font, 280, 370)
        
        pygame.display.update()
        clock.tick(30)


import sys
