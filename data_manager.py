import os
import json
import time
from threading import Lock

class DataManager:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.current_date = time.strftime('%Y-%m-%d')
        self.lock = Lock()
        self._settings_path = os.path.join(data_dir, 'settings.json')
        self._default_settings = {
            'retention_days': 0,
            'screen_width_mm': 532,
            'screen_height_mm': 299,
            'heatmap_color': '#8B0000',
            'stats_window_width': 1958,
            'stats_window_height': 735,
        }

    def _get_daily_path(self, date_str):
        return os.path.join(self.data_dir, f'{date_str}.json')

    def _get_total_path(self):
        return os.path.join(self.data_dir, 'total.json')

    def load_today_stats(self):
        path = self._get_daily_path(self.current_date)
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if '__mouse_distance__' not in data:
                    data['__mouse_distance__'] = 0.0
                return data
            except (json.JSONDecodeError, IOError):
                pass
        return {'__mouse_distance__': 0.0}

    def load_total_stats(self):
        path = self._get_total_path()
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if '__mouse_distance__' not in data:
                    data['__mouse_distance__'] = 0.0
                return data
            except (json.JSONDecodeError, IOError):
                pass
        return {'__mouse_distance__': 0.0}

    def load_daily_stats(self, date_str):
        path = self._get_daily_path(date_str)
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if '__mouse_distance__' not in data:
                    data['__mouse_distance__'] = 0.0
                return data
            except (json.JSONDecodeError, IOError):
                pass
        return {'__mouse_distance__': 0.0}

    def save_daily_stats(self, date_str, stats):
        path = self._get_daily_path(date_str)
        with self.lock:
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(stats, f, indent=2, ensure_ascii=False)
            except IOError as e:
                print(f"保存每日数据失败: {e}")

    def save_total_stats(self, stats):
        path = self._get_total_path()
        with self.lock:
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(stats, f, indent=2, ensure_ascii=False)
            except IOError as e:
                print(f"保存总数据失败: {e}")

    def save_all(self, today_stats, total_stats):
        self.save_daily_stats(self.current_date, today_stats)
        self.save_total_stats(total_stats)

    def get_available_dates(self):
        dates = []
        for fname in os.listdir(self.data_dir):
            if fname.endswith('.json') and len(fname) == 15 and fname[4] == '-' and fname[7] == '-':
                try:
                    date_str = fname[:10]
                    time.strptime(date_str, '%Y-%m-%d')
                    dates.append(date_str)
                except ValueError:
                    pass
        dates.sort()
        return dates

    def load_settings(self):
        if os.path.exists(self._settings_path):
            try:
                with open(self._settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                for k, v in self._default_settings.items():
                    if k not in settings:
                        settings[k] = v
                return settings
            except (json.JSONDecodeError, IOError):
                pass
        return self._default_settings.copy()

    def save_settings(self, settings):
        with self.lock:
            try:
                with open(self._settings_path, 'w', encoding='utf-8') as f:
                    json.dump(settings, f, indent=2, ensure_ascii=False)
            except IOError as e:
                print(f"保存设置失败: {e}")

    def cleanup_old_data(self, retention_days):
        if retention_days <= 0:
            return
        cutoff = time.time() - retention_days * 86400
        try:
            for fname in os.listdir(self.data_dir):
                if fname.endswith('.json') and fname != 'total.json' and fname != 'settings.json':
                    if len(fname) == 15 and fname[4] == '-' and fname[7] == '-':
                        try:
                            file_date = fname[:10]
                            t = time.mktime(time.strptime(file_date, '%Y-%m-%d'))
                            if t < cutoff:
                                os.remove(os.path.join(self.data_dir, fname))
                        except (ValueError, OSError):
                            pass
        except Exception as e:
            print(f"清理过期数据出错: {e}")