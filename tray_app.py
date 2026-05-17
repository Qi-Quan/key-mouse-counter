import os
import queue
import pystray
from PIL import Image, ImageDraw

def create_default_icon():
    img = Image.new('RGB', (32, 32), 'white')
    draw = ImageDraw.Draw(img)
    draw.ellipse((4, 4, 28, 28), fill='red')
    return img

def load_icon_image(path):
    if path and os.path.isfile(path):
        try:
            img = Image.open(path)
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            return img
        except Exception:
            pass
    return create_default_icon()

class TrayApp:
    def __init__(self, command_queue, icon_path=None):
        self.command_queue = command_queue
        self.icon = None
        self.icon_image = load_icon_image(icon_path)

    def _on_stats(self, icon, item):
        self.command_queue.put('stats')

    def _on_settings(self, icon, item):
        self.command_queue.put('settings')

    def _on_exit(self, icon, item):
        self.command_queue.put('exit')
        # pystray 的 stop 由 command 处理，这里不直接 stop

    def run(self):
        menu = pystray.Menu(
            pystray.MenuItem('统计', self._on_stats),
            pystray.MenuItem('设置', self._on_settings),
            pystray.MenuItem('退出', self._on_exit)
        )
        self.icon = pystray.Icon(
            "key-mouse-counter",
            self.icon_image,
            "Key Mouse Counter",
            menu
        )
        self.icon.run()