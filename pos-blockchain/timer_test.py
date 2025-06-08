# Copyright (c) 2025 An Hongxu
# Peking University - School of Software and Microelectronics
# Email: anhongxu@stu.pku.edu.cn
#
# For academic use only. Commercial usage is prohibited without authorization.

import unittest
import time
from timer import Timer


class TestRepeatTimer(unittest.TestCase):
    def test_run_once(self):
        """测试只运行一次"""
        counter = [0]

        def callback():
            counter[0] += 1

        timer = Timer(0.5, callback, repeat=1)
        timer.start()
        time.sleep(0.6)  # 等待足够时间让定时器触发

        self.assertEqual(counter[0], 1)
        timer.stop()

    def test_run_n_times(self):
        """测试运行3次"""
        counter = [0]

        def callback():
            counter[0] += 1

        timer = Timer(0.3, callback, repeat=3)
        timer.start()
        time.sleep(1.2)  # 足够时间触发3次（0.3 * 3 = 0.9）

        self.assertEqual(counter[0], 3)
        timer.stop()

    def test_run_infinite(self):
        """测试无限运行并手动停止"""
        counter = [0]

        def callback():
            counter[0] += 1

        timer = Timer(0.2, callback, repeat=-1)
        timer.start()
        time.sleep(1.0)  # 运行5次左右
        timer.stop()

        # 至少触发了几次？
        self.assertGreaterEqual(counter[0], 4)
        self.assertLessEqual(counter[0], 6)

    def test_callback_with_args_kwargs(self):
        """测试带参数的回调函数"""
        result = []

        def callback(*args, **kwargs):
            result.extend(args)
            result.extend(kwargs.values())

        timer = Timer(0.5, callback, 1, "hello", 42, key="value")
        timer.start()
        time.sleep(0.6)

        self.assertIn("hello", result)
        self.assertIn(42, result)
        self.assertIn("value", result)
        timer.stop()

    def test_stop_before_trigger(self):
        """测试在启动后立即停止"""
        counter = [0]

        def callback():
            counter[0] += 1

        timer = Timer(0.5, callback, repeat=3)
        timer.start()
        timer.stop()

        time.sleep(0.6)
        self.assertEqual(counter[0], 0)


if __name__ == '__main__':
    unittest.main()