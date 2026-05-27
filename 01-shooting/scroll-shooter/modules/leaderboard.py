"""排行榜系统"""
import json
import os
import sys


def get_user_data_dir():
    """获取用户数据目录（跨平台兼容，支持打包后运行）
    
    Returns:
        str: 用户数据目录路径
    """
    # 获取用户文档目录
    if sys.platform == 'win32':
        # Windows: C:\Users\用户名\Documents\ScrollShooter
        user_home = os.path.expanduser('~')
        data_dir = os.path.join(user_home, 'Documents', 'ScrollShooter')
    elif sys.platform == 'darwin':
        # macOS: /Users/用户名/Documents/ScrollShooter
        user_home = os.path.expanduser('~')
        data_dir = os.path.join(user_home, 'Documents', 'ScrollShooter')
    else:
        # Linux: /home/用户名/.local/share/ScrollShooter
        user_home = os.path.expanduser('~')
        data_dir = os.path.join(user_home, '.local', 'share', 'ScrollShooter')
    
    # 确保目录存在
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


class Leaderboard:
    """排行榜管理类"""
    
    def __init__(self, filename='leaderboard.json'):
        """初始化排行榜"""
        # 使用用户数据目录，确保打包后也能正常保存
        user_data_dir = get_user_data_dir()
        self.filepath = os.path.join(user_data_dir, filename)
        self.max_entries = 3  # 每种模式只保留前3名
        self.data = self._load()
    
    def _load(self):
        """从文件加载排行榜数据"""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        
        # 默认数据结构
        return {
            'normal': [],  # 普通模式
            'boss': []     # BOSS战模式
        }
    
    def save(self):
        """保存排行榜数据到文件"""
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存排行榜失败: {e}")
    
    def add_score(self, mode, score, wave_num):
        """添加新成绩
        
        Args:
            mode: 游戏模式 ('normal' 或 'boss')
            score: 分数
            wave_num: 到达波数
            
        Returns:
            int: 排名（1-3），如果未进入前3则返回None
        """
        if mode not in self.data:
            self.data[mode] = []
        
        # 添加新成绩
        new_entry = {
            'score': score,
            'wave': wave_num,
            'timestamp': self._get_timestamp()
        }
        
        self.data[mode].append(new_entry)
        
        # 按分数排序（降序）
        self.data[mode].sort(key=lambda x: x['score'], reverse=True)
        
        # 只保留前3名
        if len(self.data[mode]) > self.max_entries:
            self.data[mode] = self.data[mode][:self.max_entries]
        
        # 保存
        self.save()
        
        # 返回排名
        for i, entry in enumerate(self.data[mode]):
            if entry == new_entry:
                return i + 1
        
        return None
    
    def get_leaderboard(self, mode):
        """获取指定模式的排行榜
        
        Args:
            mode: 游戏模式 ('normal' 或 'boss')
            
        Returns:
            list: 排行榜数据列表
        """
        if mode not in self.data:
            return []
        
        return self.data[mode][:self.max_entries]
    
    def get_all_leaderboards(self):
        """获取所有模式的排行榜
        
        Returns:
            dict: {'normal': [...], 'boss': [...]}
        """
        return {
            'normal': self.get_leaderboard('normal'),
            'boss': self.get_leaderboard('boss')
        }
    
    def _get_timestamp(self):
        """获取时间戳字符串"""
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d %H:%M')
    
    def clear(self, mode=None):
        """清空排行榜
        
        Args:
            mode: 指定模式（None表示清空所有）
        """
        if mode:
            self.data[mode] = []
        else:
            self.data = {'normal': [], 'boss': []}
        self.save()
