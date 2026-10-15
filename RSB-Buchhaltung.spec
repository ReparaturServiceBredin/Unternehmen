# PyInstaller-Bauplan für RSB-Buchhaltung.exe (eine einzige Datei)
# Bauen:  pyinstaller RSB-Buchhaltung.spec   -> dist/RSB-Buchhaltung(.exe)
from PyInstaller.utils.hooks import collect_all

datas = [
    ("rsb/templates", "rsb/templates"),
    ("rsb/static", "rsb/static"),
    ("rsb/schema.sql", "rsb"),
    ("docs/AENDERUNGEN.md", "docs"),
]
binaries = []
hiddenimports = ["waitress", "pystray._win32"]
for paket in ("reportlab", "tzdata"):  # tzdata: deutsche Zeitzone für Foto-Zeitstempel unter Windows
    d, b, h = collect_all(paket)
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis(
    ["start_exe.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "pytest", "playwright", "aiosmtpd"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="RSB-Buchhaltung",
    console=False,         # kein schwarzes Fenster; Bedienung über das Symbol neben der Uhr
    icon="rsb/static/bilder/programm.ico",
    upx=False,
    version="version_info.txt" if __import__("os").path.exists("version_info.txt") else None,
)
