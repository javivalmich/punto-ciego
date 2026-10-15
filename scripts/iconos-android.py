"""Genera los iconos y la pantalla de inicio de Android a partir de los logos del repo (assets/icons/).
Uso: python -I scripts/iconos-android.py   (necesita Pillow). Fondo del logo: #050504."""
from PIL import Image, ImageDraw
from pathlib import Path
raiz = Path(__file__).resolve().parent.parent
res = raiz / 'android/app/src/main/res'
BG = (5, 5, 4)
mask = Image.open(raiz / 'assets/icons/icon-maskable-1024.png').convert('RGB')
full = Image.open(raiz / 'assets/icons/icon-1024.png').convert('RGB')
dens = {'mdpi': 1, 'hdpi': 1.5, 'xhdpi': 2, 'xxhdpi': 3, 'xxxhdpi': 4}
for d, k in dens.items():
    c = res / f'mipmap-{d}'
    n = int(48 * k); f = int(108 * k)
    ic = full.resize((n, n), Image.LANCZOS)
    ic.save(c / 'ic_launcher.png')
    m = Image.new('L', (n * 4, n * 4), 0); ImageDraw.Draw(m).ellipse((0, 0, n * 4 - 1, n * 4 - 1), fill=255)
    r = ic.convert('RGBA'); r.putalpha(m.resize((n, n), Image.LANCZOS)); r.save(c / 'ic_launcher_round.png')
    mask.resize((f, f), Image.LANCZOS).save(c / 'ic_launcher_foreground.png')   # el logo ya cabe en la zona segura (66 %)
# icono de la pantalla de inicio (Android 12+): lienzo de 288 dp, círculo visible de 192 dp
(res / 'drawable-nodpi').mkdir(exist_ok=True)
mask.resize((960, 960), Image.LANCZOS).save(res / 'drawable-nodpi/splash_icon.png')
# pantalla de inicio clásica (Android < 12): fondo oscuro con el logo centrado, como en iOS
sp = {'': (480, 800), 'port-mdpi': (320, 480), 'port-hdpi': (480, 800), 'port-xhdpi': (720, 1280), 'port-xxhdpi': (960, 1600), 'port-xxxhdpi': (1280, 1920),
      'land-mdpi': (480, 320), 'land-hdpi': (800, 480), 'land-xhdpi': (1280, 720), 'land-xxhdpi': (1600, 960), 'land-xxxhdpi': (1920, 1280)}
for suf, (w, h) in sp.items():
    t = int(min(w, h) * 0.55)
    im = Image.new('RGB', (w, h), BG); im.paste(mask.resize((t, t), Image.LANCZOS), ((w - t) // 2, (h - t) // 2))
    im.save(res / ('drawable' + ('-' + suf if suf else '')) / 'splash.png')
print('iconos y splash de Android listos')
