from pynput import keyboard, mouse
from pynput.keyboard import Key, KeyCode
from pynput.mouse import Button

class InputListener:
    def __init__(self, counter, debug=False):
        self.counter = counter
        self.debug = debug
        self.keyboard_listener = None
        self.mouse_listener = None
        self._last_mouse_pos = None

    @staticmethod
    def _key_name(key):
        if isinstance(key, Key):
            # 特殊处理左右 Win 键
            if key in (Key.cmd, Key.cmd_l, Key.cmd_r):
                if hasattr(key, 'vk'):
                    if key.vk == 0x5B:   # VK_LWIN
                        return 'Key.cmd_l'
                    elif key.vk == 0x5C: # VK_RWIN
                        return 'Key.cmd_r'
                return 'Key.cmd'          # 回退（通常不会发生）
            return f'Key.{key.name}'
        elif isinstance(key, KeyCode):
            if key.char and key.char.isprintable():
                return key.char
            return f'KeyCode(vk={key.vk})'
        return str(key)

    @staticmethod
    def _mouse_button_name(button):
        if button == Button.left:
            return 'Mouse.left'
        elif button == Button.right:
            return 'Mouse.right'
        elif button == Button.middle:
            return 'Mouse.middle'
        else:
            return f'Mouse.{button.name}'

    def on_press(self, key):
        try:
            name = self._key_name(key)
            self.counter.press(name)
            if self.debug:
                print(f"按下: {name}")
        except Exception:
            if self.debug:
                import traceback
                print("on_press 异常:")
                traceback.print_exc()

    def on_release(self, key):
        try:
            name = self._key_name(key)
            duration = self.counter.release(name)
            if self.debug:
                if duration is not None:
                    print(f"释放: {name}，按住 {duration:.2f} 秒")
        except Exception:
            if self.debug:
                import traceback
                print("on_release 异常:")
                traceback.print_exc()

    def on_mouse_click(self, x, y, button, pressed):
        try:
            name = self._mouse_button_name(button)
            if pressed:
                self.counter.press(name)
                if self.debug:
                    print(f"按下: {name}")
            else:
                duration = self.counter.release(name)
                if self.debug and duration is not None:
                    print(f"释放: {name}，按住 {duration:.2f} 秒")
        except Exception:
            if self.debug:
                import traceback
                print("on_mouse_click 异常:")
                traceback.print_exc()

    def on_move(self, x, y):
        try:
            if self._last_mouse_pos is not None:
                dx = x - self._last_mouse_pos[0]
                dy = y - self._last_mouse_pos[1]
                if dx != 0 or dy != 0:
                    self.counter.move(dx, dy)
            self._last_mouse_pos = (x, y)
        except Exception:
            if self.debug:
                import traceback
                print("on_move 异常:")
                traceback.print_exc()

    def start(self):
        self.keyboard_listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release
        )
        self.mouse_listener = mouse.Listener(
            on_click=self.on_mouse_click,
            on_move=self.on_move
        )
        self.keyboard_listener.start()
        self.mouse_listener.start()

    def stop(self):
        if self.keyboard_listener:
            self.keyboard_listener.stop()
        if self.mouse_listener:
            self.mouse_listener.stop()