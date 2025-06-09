# Copyright (c) 2025 An Hongxu
# Peking University - School of Software and Microelectronics
# Email: anhongxu@stu.pku.edu.cn
#
# For academic use only. Commercial usage is prohibited without authorization.

import threading

class Timer:
    def __init__(self, interval, callback, repeat=1, *args, **kwargs):
        """
        初始化定时器

        :param interval: 定时器间隔时间（秒）
        :param callback: 回调函数
        :param repeat: 重复次数，-1 表示无限次，默认为 1
        :param args: 回调函数的位置参数
        :param kwargs: 回调函数的关键字参数
        """
        self.interval = interval
        self.callback = callback
        self.repeat = repeat  # -1 表示无限循环
        self.args = args
        self.kwargs = kwargs
        self.timer = None
        self.counter = 0
        self.running = False


    def _run(self):
        if not self.running:
            return

        try:
            self.callback(*self.args, **self.kwargs)
        except Exception as e:
            import traceback
            print(f"Error in timer callback: {e}")
            traceback.print_exc()

        self.counter += 1

        if self.repeat == -1 or self.counter < self.repeat:
            self.timer = threading.Timer(self.interval, self._run)
            self.timer.start()
        else:
            self.running = False

    def start(self):
        """启动定时器"""
        if self.running:
            return

        self.running = True
        self.counter = 0
        self.timer = threading.Timer(self.interval, self._run)
        self.timer.start()

    def stop(self):
        """停止定时器"""
        self.running = False
        if self.timer:
            self.timer.cancel()