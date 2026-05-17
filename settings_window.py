import tkinter as tk
from tkinter import ttk
from tkinter import colorchooser

class SettingsWindow:
    def __init__(self, master, data_manager, on_close, is_startup_enabled, set_startup, icon_path=None):
        self.master = master
        self.data_manager = data_manager
        self.on_close = on_close
        self._is_startup_enabled = is_startup_enabled
        self._set_startup = set_startup
        self.win = tk.Toplevel(master)
        self.win.title("Key Mouse Counter - 设置")
        self.win.resizable(False, False)
        self.win.protocol("WM_DELETE_WINDOW", self.close)

        if icon_path:
            try:
                img = tk.PhotoImage(file=icon_path)
                self.win.iconphoto(False, img)
            except:
                pass

        settings = data_manager.load_settings()
        self.retention_days = tk.IntVar(value=settings.get('retention_days', 0))
        self.auto_start = tk.BooleanVar(value=self._is_startup_enabled())
        self.screen_w_mm = tk.IntVar(value=settings.get('screen_width_mm', 532))
        self.screen_h_mm = tk.IntVar(value=settings.get('screen_height_mm', 299))
        self.heat_color = tk.StringVar(value=settings.get('heatmap_color', '#8B0000'))

        # 历史保留天数
        frame1 = ttk.Frame(self.win, padding=15)
        frame1.pack(fill='x')
        ttk.Label(frame1, text="历史数据保留天数（0 = 永久）：").grid(row=0, column=0, sticky='w', pady=5)
        spin = ttk.Spinbox(frame1, from_=0, to=3650, textvariable=self.retention_days, width=8)
        spin.grid(row=0, column=1, sticky='w', padx=10, pady=5)
        self.retention_days.trace_add('write', self._on_retention_changed)

        # 开机自启
        frame2 = ttk.Frame(self.win, padding=15)
        frame2.pack(fill='x')
        cb = ttk.Checkbutton(frame2, text="开机自启动", variable=self.auto_start)
        cb.grid(row=0, column=0, sticky='w', pady=5)
        self.auto_start.trace_add('write', self._on_autostart_changed)

        # 屏幕尺寸
        frame3 = ttk.LabelFrame(self.win, text="设置屏幕尺寸记录鼠标移动距离", padding=15)
        frame3.pack(fill='x', padx=10, pady=5)
        ttk.Label(frame3, text="显示器宽度 (mm)：").grid(row=0, column=0, sticky='e', pady=5)
        w_entry = ttk.Entry(frame3, textvariable=self.screen_w_mm, width=10)
        w_entry.grid(row=0, column=1, sticky='w', padx=5)
        ttk.Label(frame3, text="显示器高度 (mm)：").grid(row=1, column=0, sticky='e', pady=5)
        h_entry = ttk.Entry(frame3, textvariable=self.screen_h_mm, width=10)
        h_entry.grid(row=1, column=1, sticky='w', padx=5)
        self.screen_w_mm.trace_add('write', self._on_screen_size_changed)
        self.screen_h_mm.trace_add('write', self._on_screen_size_changed)

        # 热力图颜色
        frame4 = ttk.LabelFrame(self.win, text="按键热力图颜色", padding=15)
        frame4.pack(fill='x', padx=10, pady=5)
        ttk.Entry(frame4, textvariable=self.heat_color, width=10).grid(row=0, column=0, padx=5)
        ttk.Button(frame4, text="选择颜色", command=self._choose_color).grid(row=0, column=1, padx=5)
        self.color_preview = tk.Canvas(frame4, width=30, height=20, bg=self.heat_color.get(), highlightthickness=0)
        self.color_preview.grid(row=0, column=2, padx=10)
        self.heat_color.trace_add('write', self._on_color_changed)

        self.win.update_idletasks()
        w = self.win.winfo_width()
        h = self.win.winfo_height()
        x = (self.win.winfo_screenwidth() - w) // 2
        y = (self.win.winfo_screenheight() - h) // 2
        self.win.geometry(f'+{x}+{y}')

    def _choose_color(self):
        color = colorchooser.askcolor(title="选择热力图颜色", initialcolor=self.heat_color.get())
        if color and color[1]:
            self.heat_color.set(color[1])

    def _on_retention_changed(self, *args):
        days = self.retention_days.get()
        settings = self.data_manager.load_settings()
        settings['retention_days'] = days
        self.data_manager.save_settings(settings)
        self.data_manager.cleanup_old_data(days)

    def _on_autostart_changed(self, *args):
        self._set_startup(self.auto_start.get())

    def _on_screen_size_changed(self, *args):
        try:
            w = self.screen_w_mm.get()
            h = self.screen_h_mm.get()
            if w > 0 and h > 0:
                settings = self.data_manager.load_settings()
                settings['screen_width_mm'] = w
                settings['screen_height_mm'] = h
                self.data_manager.save_settings(settings)
        except tk.TclError:
            pass

    def _on_color_changed(self, *args):
        color = self.heat_color.get()
        try:
            if color.startswith('#') and len(color) == 7:
                int(color[1:], 16)
            else:
                raise ValueError
        except:
            color = '#8B0000'
            self.heat_color.set(color)
        settings = self.data_manager.load_settings()
        settings['heatmap_color'] = color
        self.data_manager.save_settings(settings)
        self.color_preview.config(bg=color)

    def close(self):
        self.win.destroy()
        self.on_close()