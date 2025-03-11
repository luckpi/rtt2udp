# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_all

block_cipher = None

# 获取Python路径
python_path = os.path.dirname(sys.executable)

# 收集所有依赖项
datas = [('config.json', '.')]
binaries = []

# 添加Python DLL
python_dlls = []
for file in os.listdir(python_path):
    if file.lower().endswith('.dll'):
        python_dlls.append((os.path.join(python_path, file), '.'))

# 添加pylink-square依赖
pylink_datas = []
pylink_binaries = []
try:
    from pylink import __path__ as pylink_path
    pylink_dir = pylink_path[0]
    for root, dirs, files in os.walk(pylink_dir):
        for file in files:
            if file.lower().endswith(('.dll', '.so', '.dylib')):
                rel_dir = os.path.relpath(root, pylink_dir)
                if rel_dir == '.':
                    rel_dir = 'pylink'
                else:
                    rel_dir = os.path.join('pylink', rel_dir)
                pylink_binaries.append((os.path.join(root, file), rel_dir))
except ImportError:
    pass

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries + python_dlls + pylink_binaries,
    datas=datas + pylink_datas,
    hiddenimports=['tkinter', 'tkinter.ttk', 'tkinter.messagebox', 'pylink', 'pylink.jlink'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='RTT2UDP',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 设置为False以隐藏控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='NONE',
)
