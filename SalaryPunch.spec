# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('assets', 'assets')]
binaries = []
hiddenimports = ['salary_punch', 'salary_punch.config', 'salary_punch.config_ui', 'salary_punch.engine', 'salary_punch.phrases', 'salary_punch._period', 'salary_punch.games', 'salary_punch.games.ttt', 'salary_punch.games.gomoku', 'salary_punch.games.shooter', 'salary_punch.games.advice', 'salary_punch.games.novel', 'salary_punch.games.memo', 'salary_punch.games.video', 'salary_punch.games.market', 'cv2', 'salary_punch.games.muyu', 'salary_punch.games.coin', 'salary_punch.games.dice', 'salary_punch.reminders', 'salary_punch.fish', 'salary_punch.dark_menu', 'salary_punch.ui', 'salary_punch.tray_win', 'salary_punch.punch_ui', 'salary_punch.autostart']
tmp_ret = collect_all('cv2')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('win32com')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('pythonwin')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SalaryPunch',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['D:/ieswork/salary-punch/assets/tray.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SalaryPunch',
)
