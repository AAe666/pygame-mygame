# -*- mode: python ; coding: utf-8 -*-
r"""
Greedy Dash - PyInstaller 打包配置文件
使用方法（与同目录 scroll-shooter 保持一致）：
    cd D:\TYW\Code\Games\01-shooting\greedy-dash
    venv\Scripts\python.exe -m PyInstaller GreedyDash.spec
"""

import sys
import os
import re

block_cipher = None

# 从 README.md 提取最新版本号，生成带后缀的 exe 名，如 "贪逼牛逼v3.1.0.exe"
_BASE_NAME = "贪逼牛逼"
_VERSION = "dev"
_readme = os.path.join(SPECPATH, "README.md")
try:
    with open(_readme, encoding="utf-8") as _f:
        _txt = _f.read()
    _m = re.search(r"v(\d+\.\d+\.\d+)", _txt)
    if _m:
        _VERSION = _m.group(1)
except FileNotFoundError:
    pass
_EXE_NAME = "%sv%s" % (_BASE_NAME, _VERSION)

# 分析主程序
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        # Pygame 相关
        'pygame',
        'pygame.locals',
        # 游戏模块
        'settings',
        'player',
        'enemy',
        'particle',
        'ui',
        # Python 标准库
        'math',
        'random',
        'ctypes',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除不需要的模块，减小文件大小
        'tkinter',
        'unittest',
        'email',
        'xml',
        'pydoc',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# 创建 PYZ 归档
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# 创建 exe 文件
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=_EXE_NAME,  # exe 文件名（自动带版本后缀，如 "贪逼牛逼v3.1.0"）
    debug=False,  # 调试模式（发布时设为 False）
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # 使用 UPX 压缩
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # False=不显示控制台窗口（游戏推荐）
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',  # exe 图标（v3.1.0 由 make_icon.py 生成）
)
