import time
import math
from threading import Lock

class KeyCounter:
    def __init__(self, data_manager):
        self.data_manager = data_manager
        self.lock = Lock()
        self.active_keys = {}
        self.today_stats = self.data_manager.load_today_stats()
        self.total_stats = self.data_manager.load_total_stats()

    def press(self, key_name):
        with self.lock:
            now = time.time()
            if key_name not in self.active_keys:
                self.active_keys[key_name] = now

    def release(self, key_name):
        with self.lock:
            press_time = self.active_keys.pop(key_name, None)
            if press_time is None:
                return None
            duration = time.time() - press_time

            if key_name not in self.today_stats:
                self.today_stats[key_name] = {'count': 0, 'duration': 0.0}
            self.today_stats[key_name]['count'] += 1
            self.today_stats[key_name]['duration'] += duration

            if key_name not in self.total_stats:
                self.total_stats[key_name] = {'count': 0, 'duration': 0.0}
            self.total_stats[key_name]['count'] += 1
            self.total_stats[key_name]['duration'] += duration

            return duration

    def move(self, dx, dy):
        """累积鼠标移动距离（像素），线程安全"""
        if dx == 0 and dy == 0:
            return
        dist = math.hypot(dx, dy)
        with self.lock:
            key = '__mouse_distance__'
            self.today_stats.setdefault(key, 0)
            self.today_stats[key] += dist
            self.total_stats.setdefault(key, 0)
            self.total_stats[key] += dist

    def check_date_change(self):
        current_date = time.strftime('%Y-%m-%d')
        with self.lock:
            if self.data_manager.current_date != current_date:
                self.data_manager.save_daily_stats(
                    self.data_manager.current_date, self.today_stats
                )
                self.today_stats = {'__mouse_distance__': 0.0}  # 重置当天统计，保留鼠标距离字段
                self.data_manager.current_date = current_date
                self.data_manager.save_total_stats(self.total_stats)

    def get_save_data(self):
        with self.lock:
            return {
                'today': self.today_stats.copy(),
                'total': self.total_stats.copy(),
            }