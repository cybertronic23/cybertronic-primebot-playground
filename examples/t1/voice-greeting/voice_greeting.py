#!/usr/bin/env python3
"""T1 语音问候技能。

订阅语音识别结果，命中关键词（且为最终结果、置信度达标）后，执行共享的
问候动作序列：表情 -> 灯效 -> 语音 -> 挥手。

动作序列实现在 examples/t1/skill_lib/greeting_actions.py，与触摸触发版本共用。

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

from aimdk_msgs.msg import AsrResult, McPresetMotion

EXAMPLES_T1_DIR = Path(__file__).resolve().parents[1]
if str(EXAMPLES_T1_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_T1_DIR))

from skill_lib.greeting_actions import GreetingActions  # noqa: E402


class VoiceGreetingSkill(Node):
    """ASR 关键词触发的一次性问候动作序列。"""

    def __init__(self) -> None:
        super().__init__("t1_voice_greeting")

        raw_keywords = str(
            self.declare_parameter(
                "keywords", "你好,启元,hello,hi"
            ).value
        )
        self.keywords = [k.strip() for k in raw_keywords.split(",") if k.strip()]
        self.min_confidence = float(
            self.declare_parameter("min_confidence", 0.5).value
        )
        self.cooldown_sec = float(self.declare_parameter("cooldown_sec", 5.0).value)

        self.actions = GreetingActions(
            self,
            source="t1_voice_greeting",
            preset_motion=int(
                self.declare_parameter(
                    "preset_motion", int(McPresetMotion.RIGHT_ARM_WAVE)
                ).value
            ),
            greeting_text=str(
                self.declare_parameter(
                    "greeting_text", "我在呢，有什么可以帮你"
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
            AsrResult,
            "/aima/agent/asr_result",
            self.on_asr,
            qos_profile_sensor_data,
        )

        self.get_logger().info(
            "T1 语音问候技能已启动："
            f"keywords={self.keywords} min_confidence={self.min_confidence} "
            f"cooldown={self.cooldown_sec}s"
        )
        self.get_logger().info("等待语音识别结果，Ctrl+C 退出。")

    def on_asr(self, msg: AsrResult) -> None:
        if self._busy:
            return
        # 只处理最终结果，忽略中间识别片段，避免一句话触发多次。
        if not msg.is_final:
            return
        if msg.confidence < self.min_confidence:
            return

        text = msg.text.strip()
        lowered = text.casefold()
        matched = next(
            (k for k in self.keywords if k.casefold() in lowered), None
        )
        if matched is None:
            return

        now = time.monotonic()
        if now - self._last_trigger < self.cooldown_sec:
            return

        self._last_trigger = now
        self.trigger_pending = True
        self.get_logger().info(
            f"命中关键词「{matched}」：text={text!r} "
            f"confidence={msg.confidence:.2f}"
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
    node = VoiceGreetingSkill()
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
