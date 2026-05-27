# 外星人入侵游戏

这是一个使用 Pygame 开发的经典射击游戏 - 外星人入侵。

## 项目结构

```
project/
├── main.py              # 游戏主程序
├── cfg.py               # 游戏配置文件(颜色、屏幕尺寸等)
├── modules/             # 游戏模块包
│   ├── __init__.py
│   ├── sprites.py       # 游戏精灵类(敌人、UFO、飞船、子弹)
│   └── utils.py         # 工具函数(显示文字、生命值、结束界面)
├── resources/           # 游戏资源目录
│   └── bgm.mp3          # 背景音乐(可选)
├── requirements.txt     # Python 依赖
└── venv312/             # Python 3.12 虚拟环境
```

## 环境要求

- Python 3.12
- pygame 2.6.1

## 安装步骤

1. 激活虚拟环境:
```powershell
.\venv312\Scripts\activate
```

2. 安装依赖(如果需要):
```powershell
pip install -r requirements.txt
```

## 运行游戏

```powershell
python main.py
```

## 游戏操作

- **鼠标移动**: 控制飞船左右移动
- **鼠标点击**: 发射子弹
- **ESC键**: 退出游戏

## 游戏规则

- 消灭所有外星人即可获胜
- 不同类型的外星人有不同的分数值
- UFO 出现时击落可获得高分(100分)
- 每获得2000分增加一条生命
- 最多拥有5条生命

## 注意事项

- 背景音乐文件 `resources/bgm.mp3` 是可选的
- 如果文件不存在,游戏将静音运行
- 你可以添加自己的音乐文件到 resources 目录


## 许可证

MIT License
