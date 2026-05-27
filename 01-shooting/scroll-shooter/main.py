import os
import sys
import cfg
import pygame
from modules import *


def reset_game_state(game_mode, cdk_effects):
    """重置游戏状态（开始新游戏时调用）"""
    player = Player()
    
    # 应用CDK效果（只影响初始值）
    if cdk_effects['health_10x']:
        player.health = player.max_health * 10
        player.max_health *= 10
        print(f"  🎯 初始生命值：{player.max_health}（后续奖励在此基础上叠加）")
    if cdk_effects['attack_10x']:
        player.attack_power *= 10
        print(f"  🎯 初始攻击力：{player.attack_power}（后续奖励在此基础上叠加）")
    if cdk_effects['speed_10x']:
        player.attack_speed = max(10, player.attack_speed // 10)
        print(f"  🎯 初始攻击速度：{player.attack_speed}ms（后续奖励在此基础上叠加）")
    
    return {
        'player': player,
        'player_bullets': [],
        'enemy_bullets': [],
        'enemies': [],
        'wave_num': 1,
        'scroll_offset': 0,
        'distance_traveled': cfg.WAVE_DISTANCE,
        'score': 0,
        'wave_cleared': True,
        'reward': None,
        'wave_total_enemies': 0,
        'wave_killed_enemies': 0,
        'boss_active': False,
        'boss_defeated_count': 1,
        'particle_system': ParticleSystem(),
        'player_stats': {
            'multi_shot_count': 0,
            'has_bullet_tracking': False,
            'has_attack_power_double': False,
            'has_attack_speed_double': False,
            'has_max_health_double': False,
            'has_bullet_clear': False,
            'bullet_clear_available': False
        }
    }


def start_game(screen):
    """开始游戏"""
    clock = pygame.time.Clock()
    # 使用支持中文的字体
    from modules.utils import get_chinese_font
    font = get_chinese_font(18)
    
    # CDK输入相关
    cdk_input_active = False  # 输入框是否激活
    cdk_text = ''  # 输入的CDK文本
    cdk_effects = {  # CDK效果
        'health_10x': False,  # 十倍生命值
        'attack_10x': False,  # 十倍攻击力
        'speed_10x': False  # 十倍攻击速度
    }
    
    # 玩法说明相关
    show_help = False  # 是否显示玩法说明
    first_login = True  # 是否首次登录
    help_scroll_offset = 0  # 玩法说明滚动偏移量
    
    # 排行榜相关
    show_leaderboard = False  # 是否显示排行榜
    from modules.leaderboard import Leaderboard
    leaderboard = Leaderboard()
    
    # CDK消息提示
    cdk_message = ''  # CDK消息文本
    cdk_message_success = False  # 消息是否成功
    cdk_message_timer = 0  # 消息显示计时器
    
    # 游戏状态
    STATE_START = 0
    STATE_PLAYING = 1
    STATE_REWARD = 2
    STATE_GAME_OVER = 3
    STATE_PAUSED = 4
    
    game_state = STATE_START
    game_mode = 'normal'  # 游戏模式：'normal' 或 'boss'
    
    # 游戏对象
    player = Player()
    player_bullets = []
    enemy_bullets = []
    enemies = []
    particle_system = ParticleSystem()  # 粒子系统
    
    # 游戏进度
    wave_num = 1
    scroll_offset = 0
    distance_traveled = 0
    score = 0
    
    # 玩家统计信息（用于奖励系统）
    player_stats = {
        'multi_shot_count': 0,  # 多段攻击获取次数
        'has_bullet_tracking': False,  # 是否有子弹追踪
        'has_attack_power_double': False,  # 是否有攻击力翻倍
        'has_attack_speed_double': False,  # 是否有攻速翻倍
        'has_max_health_double': False,  # 是否有生命翻倍
        'has_bullet_clear': False,  # 是否有子弹清除道具
        'bullet_clear_available': False  # 子弹清除是否可用
    }
    
    # 波次管理
    wave_cleared = True
    reward = None
    wave_total_enemies = 0  # 本波总敌人数
    wave_killed_enemies = 0  # 本波消灭敌人数
    boss_active = False  # BOSS是否激活
    boss_defeated_count = 1  # 击败BOSS的数量（从1开始）
    
    # 主循环
    while True:
        mouse_pos = pygame.mouse.get_pos()
        current_time = pygame.time.get_ticks()
        
        # 事件处理
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            if event.type == pygame.KEYDOWN:
                # CDK输入处理
                if game_state == STATE_START and cdk_input_active:
                    if event.key == pygame.K_RETURN:
                        # 回车确认CDK
                        cdk_input_active = False
                        # 验证CDK（改为英文代码）
                        if cdk_text == 'health_10x':
                            cdk_effects['health_10x'] = True
                            cdk_message = '✅ CDK激活：初始生命值×10'
                            cdk_message_success = True
                            cdk_message_timer = 180  # 显示3秒（60帧/秒）
                            print("  ✅ CDK激活：初始生命值×10")
                        elif cdk_text == 'attack_10x':
                            cdk_effects['attack_10x'] = True
                            cdk_message = '✅ CDK激活：初始攻击力×10'
                            cdk_message_success = True
                            cdk_message_timer = 180
                            print("  ✅ CDK激活：初始攻击力×10")
                        elif cdk_text == 'speed_10x':
                            cdk_effects['speed_10x'] = True
                            cdk_message = '✅ CDK激活：初始攻击速度×10'
                            cdk_message_success = True
                            cdk_message_timer = 180
                            print("  ✅ CDK激活：初始攻击速度×10")
                        elif cdk_text:
                            cdk_message = f'❌ CDK不存在：{cdk_text}'
                            cdk_message_success = False
                            cdk_message_timer = 180
                            print(f"  ❌ CDK不存在：{cdk_text}")
                        cdk_text = ''  # 清空输入
                    elif event.key == pygame.K_BACKSPACE:
                        # 删除最后一个字符
                        cdk_text = cdk_text[:-1]
                    elif event.key == pygame.K_ESCAPE:
                        # ESC关闭输入框
                        cdk_input_active = False
                        cdk_text = ''
                    else:
                        # 添加字符（允许字母、数字、下划线）
                        if len(cdk_text) < 20:  # 限制长度
                            char = event.unicode
                            # 只允许小写字母、数字和下划线
                            if char.isalnum() or char == '_':
                                cdk_text += char.lower()
                    continue
                
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_RETURN:
                    # ESC或Enter键：暂停/继续游戏
                    if game_state == STATE_PLAYING:
                        game_state = STATE_PAUSED
                    elif game_state == STATE_PAUSED:
                        game_state = STATE_PLAYING
                
                # 玩法说明滚动（上下键）
                if show_help:
                    if event.key == pygame.K_UP:
                        help_scroll_offset = max(0, help_scroll_offset - 30)
                    elif event.key == pygame.K_DOWN:
                        help_scroll_offset += 30
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                # 鼠标滚轮滚动（玩法说明）
                if show_help and event.button == 4:  # 滚轮向上
                    help_scroll_offset = max(0, help_scroll_offset - 30)
                elif show_help and event.button == 5:  # 滚轮向下
                    help_scroll_offset += 30
                
                # 暂停状态下点击
                if game_state == STATE_PAUSED:
                    # 检测点击继续按钮
                    if (300 <= mouse_pos[0] <= 500 and 280 <= mouse_pos[1] <= 330):
                        game_state = STATE_PLAYING
                        continue
                    # 检测点击返回主界面按钮
                    if (300 <= mouse_pos[0] <= 500 and 360 <= mouse_pos[1] <= 410):
                        game_state = STATE_START
                        continue
                    continue
                
                # 检查是否点击暂停按钮（只在游戏进行中有效）
                if game_state == STATE_PLAYING:
                    pause_button_x = 10
                    pause_button_y = 10
                    pause_button_width = 60
                    pause_button_height = 25
                    
                    if (pause_button_x <= mouse_pos[0] <= pause_button_x + pause_button_width and
                        pause_button_y <= mouse_pos[1] <= pause_button_y + pause_button_height):
                        game_state = STATE_PAUSED
                        continue
                
                # 关闭玩法说明
                if show_help:
                    # 关闭按钮位置（与draw_help_screen中一致）
                    close_button_x = 350
                    close_button_y = 510  # box_y(40) + box_height(450) + 20
                    close_button_width = 100
                    close_button_height = 40
                    
                    if (close_button_x <= mouse_pos[0] <= close_button_x + close_button_width and
                        close_button_y <= mouse_pos[1] <= close_button_y + close_button_height):
                        show_help = False
                        help_scroll_offset = 0  # 重置滚动位置
                        first_login = False  # 标记为已看过
                        continue
                    else:
                        # 如果点击了其他地方，不执行任何操作（阻止穿透）
                        continue
                
                # 关闭排行榜
                if show_leaderboard and leaderboard_button_rect:
                    # 使用draw_leaderboard_screen返回的按钮坐标
                    btn = leaderboard_button_rect
                    if (btn['x'] <= mouse_pos[0] <= btn['x'] + btn['width'] and
                        btn['y'] <= mouse_pos[1] <= btn['y'] + btn['height']):
                        show_leaderboard = False
                        continue
                    else:
                        # 阻止穿透
                        continue
                
                # 游戏进行中，如果有子弹清除道具，使用它（任意位置点击）
                if game_state == STATE_PLAYING:
                    if player_stats.get('has_bullet_clear', False) and player_stats.get('bullet_clear_available', False):
                        # 清除所有敌人子弹
                        enemy_bullets.clear()
                        player_stats['bullet_clear_available'] = False  # 标记为已使用
                        print("  💫 使用子弹清除！已清除所有敌人子弹")
                        # 添加清除特效
                        particle_system.add_explosion(400, 300, 'large')
                
                if game_state == STATE_START:
                    # 检测CDK输入框点击
                    input_box_x = 250
                    input_box_y = 520
                    input_box_width = 300
                    input_box_height = 40
                    
                    if (input_box_x <= mouse_pos[0] <= input_box_x + input_box_width and
                        input_box_y <= mouse_pos[1] <= input_box_y + input_box_height):
                        cdk_input_active = True  # 激活输入框
                        continue
                    
                    # 检测玩法说明按钮点击
                    help_button_width = 180
                    help_button_height = 40
                    help_button_x = 310
                    help_button_y = 300
                    
                    if (help_button_x <= mouse_pos[0] <= help_button_x + help_button_width and
                        help_button_y <= mouse_pos[1] <= help_button_y + help_button_height):
                        show_help = True
                        first_login = False  # 不再是首次登录
                        continue
                    
                    # 检测排行榜按钮点击
                    leaderboard_button_width = 180
                    leaderboard_button_height = 40
                    leaderboard_button_x = 310
                    leaderboard_button_y = 350
                    
                    if (leaderboard_button_x <= mouse_pos[0] <= leaderboard_button_x + leaderboard_button_width and
                        leaderboard_button_y <= mouse_pos[1] <= leaderboard_button_y + leaderboard_button_height):
                        show_leaderboard = True
                        continue
                    
                    # 检测点击哪个模式按钮
                    button_width = 200
                    button_height = 50
                    button_y = 200
                    
                    # 普通模式按钮
                    normal_button_x = 150
                    if (normal_button_x <= mouse_pos[0] <= normal_button_x + button_width and
                        button_y <= mouse_pos[1] <= button_y + button_height):
                        # 开始普通模式游戏
                        game_mode = 'normal'
                        game_state = STATE_PLAYING
                        
                        # 重置游戏状态
                        state = reset_game_state(game_mode, cdk_effects)
                        player = state['player']
                        player_bullets = state['player_bullets']
                        enemy_bullets = state['enemy_bullets']
                        enemies = state['enemies']
                        wave_num = state['wave_num']
                        scroll_offset = state['scroll_offset']
                        distance_traveled = state['distance_traveled']
                        score = state['score']
                        wave_cleared = state['wave_cleared']
                        reward = state['reward']
                        wave_total_enemies = state['wave_total_enemies']
                        wave_killed_enemies = state['wave_killed_enemies']
                        boss_active = state['boss_active']
                        boss_defeated_count = state['boss_defeated_count']
                        particle_system = state['particle_system']
                        player_stats = state['player_stats']
                        print("\n开始普通模式")
                    
                    # BOSS战模式按钮
                    boss_button_x = 450
                    if (boss_button_x <= mouse_pos[0] <= boss_button_x + button_width and
                        button_y <= mouse_pos[1] <= button_y + button_height):
                        # 开始BOSS战模式游戏
                        game_mode = 'boss'
                        game_state = STATE_PLAYING
                        
                        # 重置游戏状态
                        state = reset_game_state(game_mode, cdk_effects)
                        player = state['player']
                        player_bullets = state['player_bullets']
                        enemy_bullets = state['enemy_bullets']
                        enemies = state['enemies']
                        wave_num = state['wave_num']
                        scroll_offset = state['scroll_offset']
                        distance_traveled = state['distance_traveled']
                        score = state['score']
                        wave_cleared = state['wave_cleared']
                        reward = state['reward']
                        wave_total_enemies = state['wave_total_enemies']
                        wave_killed_enemies = state['wave_killed_enemies']
                        boss_active = state['boss_active']
                        boss_defeated_count = state['boss_defeated_count']
                        particle_system = state['particle_system']
                        player_stats = state['player_stats']
                        print("\n开始BOSS战模式")
                elif game_state == STATE_GAME_OVER:
                    # 记录成绩到排行榜
                    rank = leaderboard.add_score(game_mode, score, wave_num)
                    if rank:
                        print(f"\n🏆 新成绩进入排行榜第 {rank} 名！")
                    
                    # 重新开始
                    game_state = STATE_PLAYING
                    state = reset_game_state(game_mode, cdk_effects)
                    player = state['player']
                    player_bullets = state['player_bullets']
                    enemy_bullets = state['enemy_bullets']
                    enemies = state['enemies']
                    wave_num = state['wave_num']
                    scroll_offset = state['scroll_offset']
                    distance_traveled = state['distance_traveled']
                    score = state['score']
                    wave_cleared = state['wave_cleared']
                    reward = state['reward']
                    wave_total_enemies = state['wave_total_enemies']
                    wave_killed_enemies = state['wave_killed_enemies']
                    boss_active = state['boss_active']
                    boss_defeated_count = state['boss_defeated_count']
                    particle_system = state['particle_system']
                    player_stats = state['player_stats']
                elif game_state == STATE_REWARD:
                    # 选择奖励
                    if reward:
                        option_index = reward.check_click(mouse_pos)
                        if option_index >= 0:
                            reward.apply_reward(player, option_index, player_stats)
                            
                            # 如果还有奖励次数，继续显示奖励选择
                            if reward.current_reward < reward.reward_count:
                                reward.current_reward += 1
                                reward.player = player  # 更新玩家对象
                                reward.player_stats = player_stats  # 更新玩家统计
                                reward.options = reward.generate_options()  # 生成新选项
                                reward.selected = -1
                            elif reward.is_boss_reward:
                                # BOSS奖励选择完毕，继续显示普通奖励
                                reward.is_boss_reward = False
                                reward.reward_count = reward_count  # 设置普通奖励次数
                                reward.current_reward = 1
                                reward.player = player
                                reward.player_stats = player_stats
                                reward.options = reward.generate_options()
                                reward.selected = -1
                                print("  继续普通奖励选择")
                            else:
                                # 所有奖励选择完毕，继续游戏
                                game_state = STATE_PLAYING
                                wave_cleared = False
                                # 生成下一波敌人
                                wave_num += 1
                                wave_killed_enemies = 0  # 重置消灭计数
                                boss_active = False  # 确保BOSS状态重置
                                # BOSS战模式每波都是BOSS
                                if game_mode == 'boss':
                                    new_enemies = generate_wave_enemies(wave_num, cfg.SCREENSIZE[0], boss_defeated_count, force_boss=True)
                                else:
                                    new_enemies = generate_wave_enemies(wave_num, cfg.SCREENSIZE[0], boss_defeated_count)
                                wave_total_enemies = len(new_enemies)
                                enemies.extend(new_enemies)
                                
                                # 检查是否是BOSS波
                                if game_mode == 'boss' or wave_num % cfg.BOSS_WAVE_INTERVAL == 0:
                                    boss_active = True
                                    if game_mode == 'boss':
                                        print(f"\n波次 {wave_num} 开始，BOSS战模式！卷轴停止 (第{boss_defeated_count}个BOSS)")
                                    else:
                                        print(f"\n波次 {wave_num} 开始，BOSS战！卷轴停止 (第{boss_defeated_count}个BOSS)")
                                else:
                                    print(f"\n波次 {wave_num} 开始，敌人数量: {wave_total_enemies}")
        
        # 根据状态渲染
        if game_state == STATE_START:
            from modules.utils import draw_start_screen, draw_cdk_input, draw_help_screen, draw_cdk_message, draw_leaderboard_screen
            draw_start_screen(screen, font)
            # 绘制CDK输入框
            draw_cdk_input(screen, font, cdk_text, cdk_input_active)
            
            # 绘制CDK消息提示
            if cdk_message and cdk_message_timer > 0:
                draw_cdk_message(screen, cdk_message, cdk_message_success)
                cdk_message_timer -= 1  # 每帧递减
                if cdk_message_timer <= 0:
                    cdk_message = ''  # 清除消息
            
            # 首次登录自动显示玩法说明
            if first_login and not show_help:
                show_help = True
            
            # 绘制玩法说明
            if show_help:
                help_scroll_offset = draw_help_screen(screen, help_scroll_offset)
            
            # 绘制排行榜
            leaderboard_button_rect = None
            if show_leaderboard:
                leaderboard_data = leaderboard.get_all_leaderboards()
                leaderboard_button_rect = draw_leaderboard_screen(screen, leaderboard_data)
            
            pygame.display.update()
            clock.tick(cfg.FPS)
            continue
        
        elif game_state == STATE_GAME_OVER:
            draw_game_over_screen(screen, font, score, wave_num)
            pygame.display.update()
            clock.tick(cfg.FPS)
            continue
        
        elif game_state == STATE_REWARD:
            # 绘制游戏背景
            draw_background(screen, scroll_offset)
            
            # 绘制玩家
            player.draw(screen)
            
            # 绘制子弹
            for bullet in player_bullets:
                bullet.draw(screen)
            for bullet in enemy_bullets:
                bullet.draw(screen)
            
            # 绘制敌人
            for enemy in enemies:
                enemy.draw(screen)
            
            # 绘制粒子效果
            particle_system.draw(screen)
            
            # 绘制奖励选择
            if reward:
                reward.draw(screen)
            
            pygame.display.update()
            clock.tick(cfg.FPS)
            continue
        
        elif game_state == STATE_PAUSED:
            # 绘制暂停界面
            overlay = pygame.Surface(cfg.SCREENSIZE)
            overlay.set_alpha(180)
            overlay.fill((0, 0, 0))
            screen.blit(overlay, (0, 0))
            
            # 暂停文字
            from modules.utils import get_chinese_font
            pause_font = get_chinese_font(48)
            show_text(screen, '游戏暂停', (255, 255, 255), pause_font, 400, 200, center=True)
            
            # 继续按钮
            button_width = 200
            button_height = 50
            continue_button_y = 280
            
            pygame.draw.rect(screen, (0, 100, 0), 
                            (300, continue_button_y, button_width, button_height))
            pygame.draw.rect(screen, (0, 255, 0), 
                            (300, continue_button_y, button_width, button_height), 3)
            show_text(screen, '继续游戏', (255, 255, 255), font, 
                     400, continue_button_y + button_height // 2, center=True)
            
            # 返回主界面按钮
            return_button_y = 360
            pygame.draw.rect(screen, (100, 0, 0), 
                            (300, return_button_y, button_width, button_height))
            pygame.draw.rect(screen, (255, 0, 0), 
                            (300, return_button_y, button_width, button_height), 3)
            show_text(screen, '返回主界面', (255, 255, 255), font, 
                     400, return_button_y + button_height // 2, center=True)
            
            pygame.display.update()
            clock.tick(cfg.FPS)
            continue
        
        # 游戏进行中
        # 更新粒子系统
        particle_system.update()
        
        # 更新卷轴（BOSS激活时停止）
        if not boss_active:
            scroll_offset += cfg.SCROLL_SPEED
            distance_traveled += cfg.SCROLL_SPEED
        
        # 生成新波次
        if distance_traveled >= cfg.WAVE_DISTANCE and wave_cleared and len(enemies) == 0:
            distance_traveled = 0
            wave_cleared = False
            wave_killed_enemies = 0  # 重置消灭计数
            # BOSS战模式每波都是BOSS
            if game_mode == 'boss':
                new_enemies = generate_wave_enemies(wave_num, cfg.SCREENSIZE[0], boss_defeated_count, force_boss=True, is_boss_mode=True)
            else:
                new_enemies = generate_wave_enemies(wave_num, cfg.SCREENSIZE[0], boss_defeated_count)
            wave_total_enemies = len(new_enemies)  # 记录本波总敌人数
            enemies.extend(new_enemies)
            
            # 检查是否是BOSS波
            if game_mode == 'boss' or wave_num % cfg.BOSS_WAVE_INTERVAL == 0:
                boss_active = True
                if game_mode == 'boss':
                    print(f"\n波次 {wave_num} 开始，BOSS战模式！卷轴停止 (第{boss_defeated_count}个BOSS)")
                else:
                    print(f"\n波次 {wave_num} 开始，BOSS战！卷轴停止 (第{boss_defeated_count}个BOSS)")
            else:
                print(f"\n波次 {wave_num} 开始，敌人数量: {wave_total_enemies}")
        
        # 玩家自动射击
        new_bullets = player.shoot(current_time)
        player_bullets.extend(new_bullets)
        
        # 更新玩家
        player.update(mouse_pos, cfg.SCREENSIZE[0], cfg.SCREENSIZE[1])
        
        # 更新玩家子弹
        # 如果有子弹追踪能力，更新子弹方向
        if player_stats.get('has_bullet_tracking', False) and enemies:
            for bullet in player_bullets:
                # 找到最近的敌人
                closest_enemy = None
                min_distance = float('inf')
                
                for enemy in enemies:
                    dx = enemy.rect.centerx - bullet.rect.centerx
                    dy = enemy.rect.centery - bullet.rect.centery
                    distance = dx**2 + dy**2  # 不需要开方，比较平方即可
                    
                    if distance < min_distance:
                        min_distance = distance
                        closest_enemy = enemy
                
                # 调整子弹方向追踪敌人
                if closest_enemy:
                    dx = closest_enemy.rect.centerx - bullet.rect.centerx
                    dy = closest_enemy.rect.centery - bullet.rect.centery
                    distance = max(1, (dx**2 + dy**2) ** 0.5)
                    
                    # 追踪速度（每次调整的幅度）
                    tracking_speed = 0.3
                    bullet.dx = bullet.dx * (1 - tracking_speed) + (dx / distance * 9) * tracking_speed
                    bullet.dy = bullet.dy * (1 - tracking_speed) + (dy / distance * 9) * tracking_speed
        
        player_bullets = [bullet for bullet in player_bullets if bullet.update()]
        
        # 更新敌人子弹
        enemy_bullets = [bullet for bullet in enemy_bullets if bullet.update()]
        
        # 更新敌人
        enemies_to_remove = []
        for enemy in enemies:
            if not enemy.update(scroll_offset, cfg.SCREENSIZE[1], cfg.SCREENSIZE[0]):
                enemies_to_remove.append(enemy)
                continue
            
            # 敌人射击（传递玩家位置）
            new_bullets = enemy.shoot(current_time, player_pos=(player.rect.centerx, player.rect.centery))
            enemy_bullets.extend(new_bullets)
        
        for enemy in enemies_to_remove:
            if enemy in enemies:
                enemies.remove(enemy)
        
        # 碰撞检测：玩家子弹 vs 敌人
        for bullet in player_bullets[:]:
            for enemy in enemies[:]:
                if pygame.sprite.collide_rect(bullet, enemy):
                    if bullet in player_bullets:
                        player_bullets.remove(bullet)
                    
                    # 敌人受伤
                    if enemy.take_damage(bullet.power):
                        # 敌人死亡
                        if enemy in enemies:
                            # 添加爆炸效果
                            explosion_size = 'large' if enemy.type == 'boss' else 'medium'
                            particle_system.add_explosion(enemy.rect.centerx, enemy.rect.centery, explosion_size)
                            
                            enemies.remove(enemy)
                            wave_killed_enemies += 1  # 增加消灭计数
                        score += enemy.score_value
        
        # 碰撞检测：敌人子弹 vs 玩家
        for bullet in enemy_bullets[:]:
            if pygame.sprite.collide_rect(bullet, player):
                if bullet in enemy_bullets:
                    enemy_bullets.remove(bullet)
                player.health -= bullet.power
                
                if player.health <= 0:
                    game_state = STATE_GAME_OVER
        
        # 碰撞检测：敌人 vs 玩家
        for enemy in enemies[:]:
            if pygame.sprite.collide_rect(enemy, player):
                player.health -= 20
                if enemy in enemies:
                    enemies.remove(enemy)
                
                if player.health <= 0:
                    game_state = STATE_GAME_OVER
        
        # 检查波次是否清除
        if len(enemies) == 0 and not wave_cleared:
            wave_cleared = True
            
            # 如果是BOSS波，清除BOSS激活状态并增加击败计数
            is_boss_wave = boss_active
            if boss_active:
                boss_active = False
                boss_defeated_count += 1  # 击败BOSS次数+1
                print(f"BOSS被消灭！卷轴恢复 (已击败{boss_defeated_count - 1}个BOSS)")
            
            # 根据消灭比例决定奖励次数
            if wave_total_enemies > 0:
                kill_ratio = wave_killed_enemies / wave_total_enemies
            else:
                kill_ratio = 0
            
            # 调试信息
            print(f"波次 {wave_num} 清除:")
            print(f"  总敌人: {wave_total_enemies}")
            print(f"  消灭: {wave_killed_enemies}")
            print(f"  比例: {kill_ratio:.2%}")
            
            if kill_ratio >= 1.0:  # 100%消灭
                reward_count = 3
                print(f"  奖励次数: 3 (100%消灭)")
            elif kill_ratio >= 0.8:  # 80%以上
                reward_count = 2
                print(f"  奖励次数: 2 (80%以上消灭)")
            else:
                reward_count = 1
                print(f"  奖励次数: 1 (低于80%)")
            
            # 显示奖励选择（带奖励次数）
            # 如果是BOSS波，先显示BOSS奖励
            if is_boss_wave:
                # 检查还有多少个BOSS奖励可选
                boss_rewards_available = sum([
                    not player_stats.get('has_bullet_tracking', False),
                    not player_stats.get('has_attack_power_double', False),
                    not player_stats.get('has_attack_speed_double', False),
                    not player_stats.get('has_max_health_double', False),
                    not player_stats.get('has_bullet_clear', False)
                ])
                
                if boss_rewards_available > 0:
                    # 还有BOSS奖励可选，显示BOSS奖励
                    reward = Reward(cfg.SCREENSIZE[0], cfg.SCREENSIZE[1], 1, player, is_boss_reward=True, player_stats=player_stats)
                    print(f"  显示BOSS奖励！（还有{boss_rewards_available}个可选）")
                else:
                    # 所有BOSS奖励都已获得，直接显示普通奖励
                    reward_count = 3  # BOSS战模式：给3个普通奖励
                    reward = Reward(cfg.SCREENSIZE[0], cfg.SCREENSIZE[1], reward_count, player, player_stats=player_stats)
                    print(f"  BOSS奖励已全部获得，直接显示3个普通奖励")
            else:
                reward = Reward(cfg.SCREENSIZE[0], cfg.SCREENSIZE[1], reward_count, player, player_stats=player_stats)
            
            # 清除场上的敌人子弹
            enemy_bullets.clear()
            print(f"  已清除敌人子弹")
            
            game_state = STATE_REWARD
        
        # 绘制
        draw_background(screen, scroll_offset)
        
        # 绘制玩家
        player.draw(screen)
        
        # 绘制子弹
        for bullet in player_bullets:
            bullet.draw(screen)
        for bullet in enemy_bullets:
            bullet.draw(screen)
        
        # 绘制敌人
        for enemy in enemies:
            enemy.draw(screen)
        
        # 绘制粒子效果
        particle_system.draw(screen)
        
        # 绘制HUD
        draw_hud(screen, player, wave_num, score, boss_active, player_stats)
        
        pygame.display.update()
        clock.tick(cfg.FPS)


def main():
    """主函数"""
    # 初始化
    pygame.init()
    pygame.display.set_caption('卷轴射击游戏')
    screen = pygame.display.set_mode(cfg.SCREENSIZE)
    pygame.mixer.init()
    
    # 游戏主循环
    while True:
        start_game(screen)


if __name__ == '__main__':
    main()
