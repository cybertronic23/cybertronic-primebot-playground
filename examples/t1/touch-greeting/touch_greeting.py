#!/usr/bin/env python3
"""T1 触摸问候技能。

监听触摸话题，命中指定传感器与事件后，执行共享的问候动作序列：

    表情 -> 灯效 -> 语音 -> 挥手

动作序列实现在 examples/t1/skill_lib/greeting_actions.py，语音触发版本复用同一份逻辑。

适用机型：T1（SDK v1.0.0.0）。
验证状态：已用本地假机器人和真实 aimdk_msgs 完成端到端联调，尚未上机验证。
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from aimdk_msgs.msg import McPresetMotion, TouchState

EXAMPLES_T1_DIR = Path(__file__).resolve().parents[1]
if str(EXAMPLES_T1_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_T1_DIR))

from skill_lib.greeting_actions import GreetingActions  # noqa: E402


class TouchGreetingSkill(Node):
    """触摸触发的一次性问候动作序列。"""

    def __init__(self) -> None:
        super().__init__("t1_touch_greeting")

        self.sensor_id = int(self.declare_parameter("sensor_id", 1).value)
        self.event_type = int(
            self.declare_parameter(
                "event_type", int(TouchState.TOUCH_EVENT_SINGLE_CLICK)
            ).value
        )
        self.cooldown_sec = float(self.declare_parameter("cooldown_sec", 3.0).value)

        self.actions = GreetingActions(
            self,
            source="t1_touch_greeting",
            preset_motion=int(
                self.declare_parameter(
                    "preset_motion", int(McPresetMotion.RIGHT_ARM_WAVE)
                ).value
            ),
            greeting_text=str(
                self.declare_parameter(
                    "greeting_text", "你好呀，我是启元机器人"
                ).value
            ),
            emotion_id=int(self.declare_parameter("emotion_id", 90).value),
            enable_motion=bool(self.declare_parameter("enable_motion", True).value),
            enable_tts=bool(self.declare_parameter("enable_tts", True).value),
            enable_emotion=bool(
                self.declare_parameter("enable_emotion", True).value
            ),
            enable_light=bool(self.declare_parameter("enable_light", True).value),
            led_mode=int(self.declare_parameter("led_mode", 254).value),
            led_r=int(self.declare_parameter("led_r", 0).value),
            led_g=int(self.declare_parameter("led_g", 120).value),
            led_b=int(self.declare_parameter("led_b", 255).value),
            led_period=int(self.declare_parameter("led_period", 800).value),
            dry_run=bool(self.declare_parameter("dry_run", False).value),
        )

        self.trigger_pending = False
        self._busy = False
        self._last_trigger = 0.0

        self.create_subscription(
            TouchState,
            "/aima/hal/touch/state",
            self.on_touch,
            qos_profile_sensor_data,
        )

        self.get_logger().info(
            "T1 触摸问候技能已启动："
            f"sensor_id={self.sensor_id} event_type={self.event_type} "
            f"cooldown={self.cooldown_sec}s"
        )
        self.get_logger().info("等待触摸事件，Ctrl+C 退出。")

    def on_touch(self, msg: TouchState) -> None:
        if self._busy:
            return
        if msg.sensor_id != self.sensor_id:
            return
        if msg.event_type != self.event_type:
            return

        now = time.monotonic()
        if now - self._last_trigger < self.cooldown_sec:
            return

        self._last_trigger = now
        self.trigger_pending = True
        self.get_logger().info(
            f"检测到触摸：sensor_id={msg.sensor_id} event_type={msg.event_type}"
        )

    def run_skill(self) -> None:
        self._busy = True
        try:
            self.get_logger().info("开始执行问候技能")
            self.actions.run()
        finally:
            self._busy = False


def main() -> int:
    rclpy.init()
    node = TouchGreetingSkill()
    try:
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.2)
            if node.trigger_pending:
                node.trigger_pending = False
                node.run_skill()
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        try:
            rclpy.shutdown()
        except Exception:  # noqa: BLE001
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
