import tkinter as tk
from tkinter import ttk
from keyboard_layout import KEYBOARD_LAYOUT

def round_rect(canvas, x1, y1, x2, y2, radius=8, **kwargs):
    points = [
        x1 + radius, y1,
        x2 - radius, y1,
        x2, y1,
        x2, y1 + radius,
        x2, y2 - radius,
        x2, y2,
        x2 - radius, y2,
        x1 + radius, y2,
        x1, y2,
        x1, y2 - radius,
        x1, y1 + radius,
        x1, y1
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


def format_duration(seconds):
    """将秒数转换为 时/分/秒 字符串，秒保留1位小数"""
    if seconds <= 0:
        return "0秒"
    s = float(seconds)
    h = int(s // 3600)
    m = int((s % 3600) // 60)
    sec = s % 60
    parts = []
    if h > 0:
        parts.append(f"{h}时")
    if m > 0:
        parts.append(f"{m}分")
    if sec > 0 or not parts:  # 保证至少显示秒
        parts.append(f"{sec:.1f}秒")
    return "".join(parts)


class StatsWindow:
    def __init__(self, master, data_manager, settings, get_available_dates, on_close, icon_path=None, save_callback=None):
        self.master = master
        self.data_manager = data_manager
        self.settings = settings
        self.get_available_dates = get_available_dates
        self.on_close = on_close
        self.save_callback = save_callback

        self.current_date = None
        self.stats = None
        self.total_stats = self.data_manager.load_total_stats()
        self.available_dates = get_available_dates()
        self.mode = tk.StringVar(value='count')

        self.win_width = settings.get('stats_window_width', 1200)
        self.win_height = settings.get('stats_window_height', 700)

        self.win = tk.Toplevel(master)
        self.win.title("Key Mouse Counter - 按键统计")
        self.win.protocol("WM_DELETE_WINDOW", self.close)
        self.win.geometry(f"{self.win_width}x{self.win_height}")

        if icon_path:
            try:
                img = tk.PhotoImage(file=icon_path)
                self.win.iconphoto(False, img)
            except:
                pass

        # 顶部导航 + 模式切换
        top_frame = ttk.Frame(self.win)
        top_frame.pack(fill='x', padx=5, pady=5)
        ttk.Label(top_frame, text="日期：", font=('', 10, 'bold')).pack(side='left')
        self.date_var = tk.StringVar(value='今天')
        ttk.Label(top_frame, textvariable=self.date_var, width=15, anchor='center').pack(side='left', padx=10)

        mode_frame = ttk.Frame(top_frame)
        mode_frame.pack(side='right', padx=10)
        ttk.Radiobutton(mode_frame, text="次数", variable=self.mode, value='count', command=self._on_mode_change).pack(side='left', padx=5)
        ttk.Radiobutton(mode_frame, text="时长", variable=self.mode, value='duration', command=self._on_mode_change).pack(side='left', padx=5)

        # 键盘画布
        canvas_frame = ttk.Frame(self.win)
        canvas_frame.pack(fill='both', expand=True, padx=10, pady=(0, 5))
        self.canvas = tk.Canvas(canvas_frame, bg='white', highlightthickness=1, highlightbackground='#aaa')
        self.canvas.pack(fill='both', expand=True)
        self.canvas.bind('<Configure>', self._on_canvas_configure)

        # 底部信息表格
        bottom_frame = ttk.Frame(self.win, padding=10)
        bottom_frame.pack(fill='x')
        self._build_summary_table(bottom_frame)

        # 按钮区域（包含导航和刷新）
        btn_frame = ttk.Frame(self.win, padding=5)
        btn_frame.pack()
        self.prev_btn = ttk.Button(btn_frame, text='◀ 前一天', command=self._go_prev)
        self.prev_btn.pack(side='left', padx=5)
        self.total_btn = ttk.Button(btn_frame, text='总计数据', command=self._show_total)
        self.total_btn.pack(side='left', padx=5)
        self.next_btn = ttk.Button(btn_frame, text='后一天 ▶', command=self._go_next)
        self.next_btn.pack(side='left', padx=5)
        self.refresh_btn = ttk.Button(btn_frame, text='刷新', command=self._refresh_data)
        self.refresh_btn.pack(side='left', padx=20)

        self._load_today()

    def _build_summary_table(self, parent):
        headers = ['项目', '当前日期统计', '总计']
        for col, text in enumerate(headers):
            ttk.Label(parent, text=text, font=('', 10, 'bold')).grid(row=0, column=col, padx=15, pady=2, sticky='w')

        # 保存每个项目的描述标签、当前值标签、总计值标签
        self.summary_labels = {}
        self.mouse_desc_labels = {}   # 用于动态修改鼠标按键的描述标签
        items = [
            ('mouse_dist', '鼠标移动距离'),
            ('key_count', '键盘敲击次数'),
            ('left', '左键点击'),
            ('right', '右键点击'),
            ('middle', '中键点击'),
            ('x1', '侧键1（返回）'),
            ('x2', '侧键2（前进）'),
            ('screen', '屏幕尺寸 (mm)'),
        ]
        mouse_keys = {'left', 'right', 'middle', 'x1', 'x2'}
        for i, (key, desc) in enumerate(items):
            row = i + 1
            desc_lbl = ttk.Label(parent, text=desc, font=('', 10))
            desc_lbl.grid(row=row, column=0, padx=15, sticky='w')
            cur_lbl = ttk.Label(parent, text='-', font=('', 10))
            cur_lbl.grid(row=row, column=1, padx=15, sticky='w')
            total_lbl = ttk.Label(parent, text='-', font=('', 10))
            total_lbl.grid(row=row, column=2, padx=15, sticky='w')
            self.summary_labels[key] = (desc_lbl, cur_lbl, total_lbl)
            if key in mouse_keys:
                self.mouse_desc_labels[key] = desc_lbl

        # 初始更新鼠标描述（默认次数模式）
        self._update_mouse_descriptions()

    def _update_mouse_descriptions(self):
        """根据当前模式更新鼠标按键的描述文本"""
        suffix = '时长' if self.mode.get() == 'duration' else ''
        base = {
            'left': '左键点击',
            'right': '右键点击',
            'middle': '中键点击',
            'x1': '侧键1（返回）',
            'x2': '侧键2（前进）'
        }
        for key, desc_lbl in self.mouse_desc_labels.items():
            desc_lbl.config(text=base[key] + suffix)

    def _update_summary(self):
        if self.stats is None:
            return
        distance_px = self.stats.get('__mouse_distance__', 0.0)
        screen_w_mm = self.settings.get('screen_width_mm', 532)
        screen_h_mm = self.settings.get('screen_height_mm', 299)
        screen_w_px = self.master.winfo_screenwidth()
        screen_h_px = self.master.winfo_screenheight()
        mm_per_px = ((screen_w_mm / screen_w_px) + (screen_h_mm / screen_h_px)) / 2
        distance_m = distance_px * mm_per_px / 1000.0

        keyboard_count = sum(
            v['count'] for k, v in self.stats.items()
            if k != '__mouse_distance__' and isinstance(v, dict) and 'count' in v
        )

        mode = self.mode.get()
        # 鼠标按键数据
        mouse_keys = {
            'left': 'Mouse.left',
            'right': 'Mouse.right',
            'middle': 'Mouse.middle',
            'x1': 'Mouse.x1',
            'x2': 'Mouse.x2'
        }
        cur_mouse_vals = []
        total_mouse_vals = []
        for key in ['left', 'right', 'middle', 'x1', 'x2']:
            data_key = mouse_keys[key]
            if mode == 'duration':
                cur_val = self.stats.get(data_key, {}).get('duration', 0.0)
                total_val = self.total_stats.get(data_key, {}).get('duration', 0.0)
                cur_mouse_vals.append(format_duration(cur_val))
                total_mouse_vals.append(format_duration(total_val))
            else:
                cur_val = self.stats.get(data_key, {}).get('count', 0)
                total_val = self.total_stats.get(data_key, {}).get('count', 0)
                cur_mouse_vals.append(str(cur_val))
                total_mouse_vals.append(str(total_val))

        cur_values = [
            f'{distance_m:.2f} 米',    # 单位改为米
            str(keyboard_count),
            *cur_mouse_vals,
            f'{screen_w_mm}×{screen_h_mm}',
        ]

        total_px = self.total_stats.get('__mouse_distance__', 0.0)
        total_m = total_px * mm_per_px / 1000.0
        total_keyboard = sum(
            v['count'] for k, v in self.total_stats.items()
            if k != '__mouse_distance__' and isinstance(v, dict) and 'count' in v
        )
        total_values = [
            f'{total_m:.2f} 米',
            str(total_keyboard),
            *total_mouse_vals,
            f'{screen_w_mm}×{screen_h_mm}',
        ]

        keys = ['mouse_dist', 'key_count', 'left', 'right', 'middle', 'x1', 'x2', 'screen']
        for i, key in enumerate(keys):
            _, cur_lbl, total_lbl = self.summary_labels[key]
            cur_lbl.config(text=cur_values[i])
            total_lbl.config(text=total_values[i])

    def _load_today(self):
        today = self.data_manager.current_date
        self.current_date = today
        self.date_var.set(today)
        self.stats = self.data_manager.load_daily_stats(today)
        self.total_stats = self.data_manager.load_total_stats()
        self._refresh()

    def _show_total(self):
        self.current_date = None
        self.date_var.set('总计')
        self.stats = self.data_manager.load_total_stats()
        self.total_stats = self.stats
        self._refresh()

    def _go_prev(self):
        if self.current_date is None:
            if self.available_dates:
                self.current_date = self.available_dates[-1]
            else:
                return
        else:
            idx = self.available_dates.index(self.current_date)
            if idx > 0:
                self.current_date = self.available_dates[idx-1]
            else:
                return
        self.date_var.set(self.current_date)
        self.stats = self.data_manager.load_daily_stats(self.current_date)
        self.total_stats = self.data_manager.load_total_stats()
        self._refresh()

    def _go_next(self):
        if self.current_date is None:
            return
        idx = self.available_dates.index(self.current_date)
        if idx < len(self.available_dates)-1:
            self.current_date = self.available_dates[idx+1]
        else:
            return
        self.date_var.set(self.current_date)
        self.stats = self.data_manager.load_daily_stats(self.current_date)
        self.total_stats = self.data_manager.load_total_stats()
        self._refresh()

    def _refresh_data(self):
        """刷新按钮：先保存最新数据，再重新加载并刷新界面"""
        # 1. 如果有保存回调，强制保存当前计数器的最新数据
        if self.save_callback:
            try:
                self.save_callback()
            except Exception as e:
                print(f"刷新时保存数据出错: {e}")
        
        # 2. 更新可用日期列表（可能因为新数据产生了新日期）
        self.available_dates = self.get_available_dates()
        
        # 3. 根据当前视图重新加载数据
        if self.current_date is None:      # 总计视图
            self.stats = self.data_manager.load_total_stats()
            self.total_stats = self.stats
            self.date_var.set('总计')
        else:
            # 如果当前日期已不在可用列表中（比如数据被清理），回退到最新日期或总计
            if self.current_date not in self.available_dates:
                if self.available_dates:
                    self.current_date = self.available_dates[-1]
                else:
                    self.current_date = None
                    self.stats = self.data_manager.load_total_stats()
                    self.total_stats = self.stats
                    self.date_var.set('总计')
                    self._refresh()
                    return
            self.date_var.set(self.current_date)
            self.stats = self.data_manager.load_daily_stats(self.current_date)
            self.total_stats = self.data_manager.load_total_stats()
        
        # 4. 重绘键盘和更新底部汇总
        self._refresh()

    def _on_mode_change(self):
        self._update_mouse_descriptions()   # 切换描述后缀
        self._refresh()

    def _refresh(self):
        self._draw_keyboard()
        self._update_summary()

    def _draw_keyboard(self):
        self.canvas.delete('all')
        if self.stats is None:
            return

        mode = self.mode.get()
        # 只绘制主键盘区（col_start < 19.0）
        main_keys = [k for k in KEYBOARD_LAYOUT if k[1] < 19.0]

        layout_codes = {code for *_, code in main_keys if code is not None}

        max_val = 0
        for code in layout_codes:
            key_data = self.stats.get(code)
            if isinstance(key_data, dict):
                val = key_data.get(mode, 0)
                if isinstance(val, (int, float)) and val > max_val:
                    max_val = val
        if max_val == 0:
            max_val = 1

        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        if width < 50 or height < 50:
            return

        max_row = 0
        max_col_float = 0.0
        for row, col_start, key_width, rs, cs, _, _ in main_keys:
            max_row = max(max_row, row + rs)
            max_col_float = max(max_col_float, col_start + key_width)

        margin = 4
        cell_w = (width - margin * 2) / max_col_float
        cell_h = (height - margin * 2) / max_row

        heat_color = self.settings.get('heatmap_color', '#8B0000')
        try:
            hex_color = heat_color.lstrip('#')
            tr, tg, tb = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        except:
            tr, tg, tb = 139, 0, 0

        name_font_size = max(8, int(cell_h * 0.35 * 0.5))
        count_font_size = max(8, int(name_font_size * 0.6))
        gap = 2
        radius = max(3, min(cell_w, cell_h) * 0.2)
        shadow_offset = 2

        for row, col_start, key_width, rs, cs, display, code in main_keys:
            if code is None:
                val = 0
            else:
                key_data = self.stats.get(code, None)
                if key_data is None:
                    val = 0
                elif isinstance(key_data, dict):
                    val = key_data.get(mode, 0)
                else:
                    val = 0

            ratio = val / max_val
            ratio = min(ratio, 1.0)

            r = int(255 * (1 - ratio) + tr * ratio)
            g = int(255 * (1 - ratio) + tg * ratio)
            b = int(255 * (1 - ratio) + tb * ratio)
            fill = f'#{r:02x}{g:02x}{b:02x}'

            x1 = margin + col_start * cell_w + gap
            y1 = margin + row * cell_h + gap
            x2 = x1 + key_width * cell_w - gap * 2
            y2 = y1 + rs * cell_h - gap * 2

            if radius > 0:
                round_rect(self.canvas, x1 + shadow_offset, y1 + shadow_offset,
                           x2 + shadow_offset, y2 + shadow_offset,
                           radius=radius, fill='#cccccc', outline='')
            else:
                self.canvas.create_rectangle(x1 + shadow_offset, y1 + shadow_offset,
                                             x2 + shadow_offset, y2 + shadow_offset,
                                             fill='#cccccc', outline='')

            if radius > 0:
                round_rect(self.canvas, x1, y1, x2, y2, radius=radius, fill=fill, outline='#999', width=1)
            else:
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=fill, outline='#999', width=1)

            display_val = f"{val:.1f}" if mode == 'duration' else str(int(val))
            self.canvas.create_text((x1+x2)/2, y1 + cell_h*0.25,
                                    text=display, font=('', name_font_size, 'bold'),
                                    fill='black')
            self.canvas.create_text((x1+x2)/2, y2 - cell_h*0.2,
                                    text=display_val, font=('', count_font_size),
                                    fill='#555555')

    def _on_canvas_configure(self, event):
        self._draw_keyboard()

    def close(self):
        try:
            if self.win.winfo_exists():
                self.win_width = self.win.winfo_width()
                self.win_height = self.win.winfo_height()
                settings = self.data_manager.load_settings()
                settings['stats_window_width'] = self.win_width
                settings['stats_window_height'] = self.win_height
                self.data_manager.save_settings(settings)
        except:
            pass
        self.win.destroy()
        self.on_close()