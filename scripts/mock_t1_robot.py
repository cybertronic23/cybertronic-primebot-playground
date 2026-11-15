#!/usr/bin/env python3
"""T1 本地假机器人。

提供问候类技能所需的 Topic 与服务，用于在没有真机的情况下做端到端联调：

  Topic:
    /aima/hal/touch/state        触摸事件（可自动或手动触发）
    /aima/agent/asr_result       语音识别结果（可自动或手动触发）

  Service:
    /aimdk_5Fmsgs/srv/GetMcAction
    /aimdk_5Fmsgs/srv/SetMcAction
    /aimdk_5Fmsgs/srv/SetMcPresetMotion
    /aimdk_5Fmsgs/srv/PlayTts
    /aimdk_5Fmsgs/srv/PlayEmotion
    /aimdk_5Fmsgs/srv/LedStripCommand

它不会执行任何真实动作，只打印收到的请求并返回成功。仅用于逻辑与链路验证，
不能替代真机验证。

用法：
  # 手动触发（终端交互：t=单击 d=双击 a <文本>=语音 q=退出）
  python3 scripts/mock_t1_robot.py

  # 每 3 秒自动发一次触摸，每 5 秒自动发一条语音
  python3 scripts/mock_t1_robot.py --ros-args \
    -p auto_touch_sec:=3.0 -p auto_asr_sec:=5.0 \
    -p auto_asr_text:="你好启元"
"""

from __future__ import annotations

import sys
import threading
import uuid

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node

from aimdk_msgs.msg import (
    AsrResult,
    CommonResponse,
    CommonState,
    CommonTaskResponse,
    McAction,
    McActionInfo,
    McActionStatus,
    McPresetMotion,
    MessageHeader,
    PlayTtsResponse,
    ResponseHeader,
    TouchState,
    TtsPriorityLevel,
)
from aimdk_msgs.srv import (
    GetMcAction,
    LedStripCommand,
    PlayEmotion,
    PlayTts,
    SetMcAction,
    SetMcPresetMotion,
)

SERVICE_PREFIX = "/aimdk_5Fmsgs/srv"


def _action_enum_map() -> dict[str, int]:
    return {
        name: getattr(McAction, name)
        for name in dir(McAction)
        if name.isupper() and isinstance(getattr(McAction, name), int)
    }


class MockT1Robot(Node):
    """最小可用的假机器人，仅覆盖问候技能的接口。"""

    def __init__(self) -> None:
        super().__init__("mock_t1_robot")

        self.current_action = str(
            self.declare_parameter(
                "initial_action", "BIPED_LOCOMOTION_DEFAULT"
            ).value
        )
        self.auto_touch_sec = float(
            self.declare_parameter("auto_touch_sec", 0.0).value
        )
        self.auto_touch_event = int(
            self.declare_parameter(
                "auto_touch_event", int(TouchState.TOUCH_EVENT_SINGLE_CLICK)
            ).value
        )
        self.auto_touch_sensor = int(
            self.declare_parameter("auto_touch_sensor", 1).value
        )
        self.auto_asr_sec = float(
            self.declare_parameter("auto_asr_sec", 0.0).value
        )
        self.auto_asr_text = str(
            self.declare_parameter("auto_asr_text", "你好启元").value
        )
        self.interactive = bool(self.declare_parameter("interactive", True).value)

        self._action_enums = _action_enum_map()
        self._task_id = 0

        self.touch_pub = self.create_publisher(
            TouchState, "/aima/hal/touch/state", 10
        )
        self.asr_pub = self.create_publisher(
            AsrResult, "/aima/agent/asr_result", 10
        )

        self.create_service(
            GetMcAction, f"{SERVICE_PREFIX}/GetMcAction", self.on_get_action
        )
        self.create_service(
            SetMcAction, f"{SERVICE_PREFIX}/SetMcAction", self.on_set_action
        )
        self.create_service(
            SetMcPresetMotion,
            f"{SERVICE_PREFIX}/SetMcPresetMotion",
            self.on_preset_motion,
        )
        self.create_service(PlayTts, f"{SERVICE_PREFIX}/PlayTts", self.on_tts)
        self.create_service(
            PlayEmotion, f"{SERVICE_PREFIX}/PlayEmotion", self.on_emotion
        )
        self.create_service(
            LedStripCommand, f"{SERVICE_PREFIX}/LedStripCommand", self.on_led
        )

        self.get_logger().info(
            f"假机器人已启动：initial_action={self.current_action}"
        )

        if self.auto_touch_sec > 0:
            self.create_timer(self.auto_touch_sec, self._auto_touch)
            self.get_logger().info(
                f"每 {self.auto_touch_sec}s 自动发送触摸："
                f"sensor_id={self.auto_touch_sensor} "
                f"event_type={self.auto_touch_event}"
            )
        if self.auto_asr_sec > 0:
            self.create_timer(self.auto_asr_sec, self._auto_asr)
            self.get_logger().info(
                f"每 {self.auto_asr_sec}s 自动发送语音：{self.auto_asr_text}"
            )

        if self.interactive and sys.stdin.isatty():
            threading.Thread(target=self._stdin_loop, daemon=True).start()
            self.get_logger().info(
                "交互命令：t=单击  d=双击  a <文本>=语音  q=退出"
            )

    # ------------------------------------------------------------ 响应构造

    def _next_task_id(self) -> int:
        self._task_id += 1
        return self._task_id

    def _response_header(self) -> ResponseHeader:
        header = ResponseHeader()
        header.stamp = self.get_clock().now().to_msg()
        header.code = 0
        return header

    def _common_response(self) -> CommonResponse:
        response = CommonResponse()
        response.header = self._response_header()
        response.status = CommonState()
        response.status.value = CommonState.SUCCESS
        response.message = "mock ok"
        return response

    def _task_response(self) -> CommonTaskResponse:
        response = CommonTaskResponse()
        response.header = self._response_header()
        response.task_id = self._next_task_id()
        response.state = CommonState()
        response.state.value = CommonState.SUCCESS
        return response

    # -------------------------------------------------------------- 服务回调

    def on_get_action(self, request, response):
        response.header = self._response_header()
        response.info = McActionInfo()
        response.info.current_action = McAction()
        response.info.current_action.value = self._action_enums.get(
            self.current_action, 0
        )
        response.info.action_desc = self.current_action
        response.info.source = "mock"
        response.info.status = McActionStatus()
        response.info.status.value = McActionStatus.RUNNING
        response.info.switch_ready = True
        return response

    def on_set_action(self, request, response):
        target = request.command.action_desc
        self.get_logger().info(f"[SetMcAction] {self.current_action} -> {target}")
        self.current_action = target
        response.response = self._task_response()
        return response

    def on_preset_motion(self, request, response):
        motion = request.motion.value
        self.get_logger().info(
            f"[SetMcPresetMotion] motion={motion} area={request.area.value} "
            f"interrupt={request.interrupt} ani_path={request.ani_path!r}"
        )
        response.response = self._task_response()
        return response

    def on_tts(self, request, response):
        req = request.tts_req
        self.get_logger().info(
            f"[PlayTts] text={req.text!r} "
            f"priority={req.priority_level.value} "
            f"interrupted={req.is_interrupted}"
        )
        response.header = self._common_response()
        response.tts_resp = PlayTtsResponse()
        response.tts_resp.text = req.text
        response.tts_resp.priority_level = TtsPriorityLevel()
        response.tts_resp.priority_level.value = req.priority_level.value
        response.tts_resp.priority_weight = req.priority_weight
        response.tts_resp.domain = req.domain
        response.tts_resp.trace_id = req.trace_id
        response.tts_resp.is_success = True
        response.tts_resp.error_message = ""
        response.tts_resp.estimated_duration = 0
        return response

    def on_emotion(self, request, response):
        self.get_logger().info(
            f"[PlayEmotion] type={request.type!r} ids={list(request.emotion_ids)} "
            f"priority={request.priority} loop={request.loop_count}"
        )
        response.header = self._common_response()
        return response

    def on_led(self, request, response):
        self.get_logger().info(
            f"[LedStripCommand] mode={request.led_strip_mode} "
            f"rgb=({request.r},{request.g},{request.b}) period={request.period}"
        )
        response.header = self._common_response()
        return response

    # -------------------------------------------------------------- 事件触发

    def publish_touch(self, event_type: int = 1, sensor_id: int = 1) -> None:
        msg = TouchState()
        msg.header = MessageHeader()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.sensor_id = sensor_id
        msg.event_type = event_type
        self.touch_pub.publish(msg)
        self.get_logger().info(
            f"[touch] 已发送 sensor_id={sensor_id} event_type={event_type}"
        )

    def publish_asr(self, text: str, confidence: float = 0.95) -> None:
        msg = AsrResult()
        msg.header = MessageHeader()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.text = text
        msg.event_id = uuid.uuid4().hex
        msg.is_final = True
        msg.confidence = confidence
        msg.language = "zh"
        self.asr_pub.publish(msg)
        self.get_logger().info(f"[asr] 已发送 text={text!r} confidence={confidence}")

    def _auto_touch(self) -> None:
        self.publish_touch(
            event_type=self.auto_touch_event, sensor_id=self.auto_touch_sensor
        )

    def _auto_asr(self) -> None:
        self.publish_asr(self.auto_asr_text)

    def _stdin_loop(self) -> None:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            if line in ("q", "quit", "exit"):
                self.get_logger().info("收到退出命令")
                rclpy.shutdown()
                return
            if line == "t":
                self.publish_touch(event_type=TouchState.TOUCH_EVENT_SINGLE_CLICK)
            elif line == "d":
                self.publish_touch(event_type=TouchState.TOUCH_EVENT_DOUBLE_CLICK)
            elif line.startswith("a "):
                self.publish_asr(line[2:].strip())
            else:
                self.get_logger().warning(f"未知命令：{line!r}")


def main() -> int:
    rclpy.init()
    node = MockT1Robot()
    try:
        rclpy.spin(node)
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
