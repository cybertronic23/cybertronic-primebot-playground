"""T1 问候动作序列的共享实现。

触摸触发（touch-greeting）与语音触发（voice-greeting）两个示例复用本模块，
避免动作序列代码重复。这里只调用交互类服务，不发送关节指令。
"""

from __future__ import annotations

import sys
import time
import uuid
from pathlib import Path

import rclpy

from aimdk_msgs.msg import (
    CommonRequest,
    McControlArea,
    McPresetMotion,
    PlayTtsRequest,
    RequestHeader,
    TtsPriorityLevel,
)
from aimdk_msgs.srv import (
    LedStripCommand,
    PlayEmotion,
    PlayTts,
    SetMcPresetMotion,
)

# 复用 SDK 示例里的动作切换状态机（会规划合法的动作转换路径）。
SDK_PYTHON_DIR = (
    Path(__file__).resolve().parents[3]
    / "third_party"
    / "primebot"
    / "sdk_t1-v1.0.0.0"
    / "examples"
    / "python"
)
if not SDK_PYTHON_DIR.is_dir():
    sys.exit(f"找不到 T1 SDK 的 Python 示例目录：{SDK_PYTHON_DIR}")
if str(SDK_PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(SDK_PYTHON_DIR))

from common.mc_action_switcher import (  # noqa: E402
    McActionSwitchOptions,
    McActionSwitcher,
)

# 预设动作要求先进入全身控制模式。
READY_ACTION = "BIPED_LOCOMOTION_WBC"

SERVICE_PREFIX = "/aimdk_5Fmsgs/srv"
SERVICE_CALL_TIMEOUT_SEC = 3.0
SERVICE_CALL_ATTEMPTS = 3


class GreetingActions:
    """「表情 -> 灯效 -> 语音 -> 挥手」动作序列。"""

    def __init__(
        self,
        node,
        *,
        source: str = "t1_greeting_skill",
        preset_motion: int = int(McPresetMotion.RIGHT_ARM_WAVE),
        greeting_text: str = "你好呀，我是启元机器人",
        emotion_id: int = 90,
        enable_motion: bool = True,
        enable_tts: bool = True,
        enable_emotion: bool = True,
        enable_light: bool = True,
        led_mode: int = 254,
        led_r: int = 0,
        led_g: int = 120,
        led_b: int = 255,
        led_period: int = 800,
        dry_run: bool = False,
    ) -> None:
        self.node = node
        self.source = source
        self.preset_motion = preset_motion
        self.greeting_text = greeting_text
        self.emotion_id = emotion_id
        self.enable_motion = enable_motion
        self.enable_tts = enable_tts
        self.enable_emotion = enable_emotion
        self.enable_light = enable_light
        self.led_mode = led_mode
        self.led_r = led_r
        self.led_g = led_g
        self.led_b = led_b
        self.led_period = led_period
        self.dry_run = dry_run

        self._switcher = McActionSwitcher(node)
        self.preset_client = node.create_client(
            SetMcPresetMotion, f"{SERVICE_PREFIX}/SetMcPresetMotion"
        )
        self.tts_client = node.create_client(PlayTts, f"{SERVICE_PREFIX}/PlayTts")
        self.emotion_client = node.create_client(
            PlayEmotion, f"{SERVICE_PREFIX}/PlayEmotion"
        )
        self.led_client = node.create_client(
            LedStripCommand, f"{SERVICE_PREFIX}/LedStripCommand"
        )

    # ---------------------------------------------------------------- 总流程

    def run(self) -> bool:
        """执行一次完整问候；返回是否有致命失败。"""
        log = self.node.get_logger()

        if self.dry_run:
            log.info("[dry_run] 将依次执行：切换 WBC -> 表情 -> 灯效 -> 语音 -> 挥手")
            return True

        if self.enable_motion and not self.ensure_ready_state():
            log.error("进入全身控制模式失败，技能中止")
            return False

        if self.enable_emotion:
            self.play_emotion()
        if self.enable_light:
            self.play_light()
        if self.enable_tts:
            self.play_tts()
        if self.enable_motion:
            self.play_wave()

        log.info("问候技能下发完成")
        return True

    # ---------------------------------------------------------------- 各步骤

    def ensure_ready_state(self) -> bool:
        options = McActionSwitchOptions(source=self.source, total_timeout=30.0)
        result = self._switcher.switch_to(READY_ACTION, options)
        if not result.success:
            self.node.get_logger().error(
                f"切换到 {READY_ACTION} 失败：{result.message}"
                f"（当前 {result.current_action or '未知'}）"
            )
            return False
        self.node.get_logger().info(f"已进入 {READY_ACTION}")
        return True

    def play_emotion(self) -> bool:
        ok = self._send_emotion(self.emotion_id)
        # T 系列默认 90，失败时回退到官方示例里的保底 ID 3003。
        if not ok and self.emotion_id == 90:
            self.node.get_logger().warning("表情 90 失败，回退到 3003")
            ok = self._send_emotion(3003)
        return ok

    def _send_emotion(self, emotion_id: int) -> bool:
        request = PlayEmotion.Request()
        request.header = CommonRequest()
        request.header.header.stamp = self.node.get_clock().now().to_msg()
        request.type = "emotion"
        request.emotion_ids = [int(emotion_id)]
        request.file_paths = []
        request.priority = 0
        request.loop_count = 1

        response = self._call(
            self.emotion_client, request, f"PlayEmotion({emotion_id})"
        )
        if response is None:
            return False

        code = response.header.header.code
        if code != 0:
            self.node.get_logger().error(
                f"PlayEmotion 失败：code={code} "
                f"status={response.header.status.value} "
                f"msg={response.header.message}"
            )
            return False

        self.node.get_logger().info(f"表情已下发：{emotion_id}")
        return True

    def play_light(self) -> bool:
        request = LedStripCommand.Request()
        request.request = CommonRequest()
        request.request.header.stamp = self.node.get_clock().now().to_msg()
        request.led_strip_mode = self.led_mode
        request.r = self.led_r
        request.g = self.led_g
        request.b = self.led_b
        request.period = self.led_period

        response = self._call(self.led_client, request, "LedStripCommand")
        if response is None:
            return False

        code = response.header.header.code
        status = response.header.status.value
        if code != 0:
            self.node.get_logger().error(
                f"LedStripCommand 失败：code={code} status={status} "
                f"msg={response.header.message}"
            )
            return False

        self.node.get_logger().info(
            f"灯效已下发：mode={self.led_mode} "
            f"rgb=({self.led_r},{self.led_g},{self.led_b}) period={self.led_period}"
        )
        return True

    def play_tts(self, text: str = None) -> bool:
        request = PlayTts.Request()
        request.header = CommonRequest()
        request.header.header.stamp = self.node.get_clock().now().to_msg()

        request.tts_req = PlayTtsRequest()
        request.tts_req.text = text or self.greeting_text
        request.tts_req.priority_level = TtsPriorityLevel()
        request.tts_req.priority_level.value = TtsPriorityLevel.INTERACTION_L6
        request.tts_req.priority_weight = 0
        request.tts_req.domain = self.source
        request.tts_req.trace_id = uuid.uuid4().hex
        request.tts_req.is_interrupted = True

        response = self._call(self.tts_client, request, "PlayTts")
        if response is None:
            return False

        code = response.header.header.code
        if code != 0 or not response.tts_resp.is_success:
            self.node.get_logger().error(
                f"PlayTts 失败：code={code} "
                f"is_success={response.tts_resp.is_success} "
                f"error={response.tts_resp.error_message}"
            )
            return False

        self.node.get_logger().info(f"语音已下发：{request.tts_req.text}")
        return True

    def play_wave(self) -> bool:
        request = SetMcPresetMotion.Request()
        request.header = RequestHeader()
        request.header.stamp = self.node.get_clock().now().to_msg()
        request.source = self.source
        request.area = McControlArea()
        request.area.value = McControlArea.RIGHT_HAND
        request.motion = McPresetMotion()
        request.motion.value = self.preset_motion
        request.interrupt = True
        request.ani_path = ""

        response = self._call(self.preset_client, request, "SetMcPresetMotion")
        if response is None:
            return False

        code = response.response.header.code
        # code == 1 表示被当前动画拦截丢弃，状态仍是 RUNNING，必须靠 code 判断。
        if code != 0:
            self.node.get_logger().error(
                f"SetMcPresetMotion 被拒绝或失败：code={code} "
                f"reason={response.response.state.reason}"
            )
            return False

        self.node.get_logger().info(
            f"预设动作已入队：{self.preset_motion} "
            f"task_id={response.response.task_id}"
        )
        return True

    # ------------------------------------------------------------------ 工具

    def _call(self, client, request, label: str, timeout_sec: float = None):
        """带超时与重试的同步服务调用；未就绪时立即返回 None。"""
        timeout_sec = timeout_sec or SERVICE_CALL_TIMEOUT_SEC

        if not client.service_is_ready():
            self.node.get_logger().warning(f"{label} 服务不可用，跳过该步骤")
            return None

        for attempt in range(1, SERVICE_CALL_ATTEMPTS + 1):
            future = client.call_async(request)
            rclpy.spin_until_future_complete(
                self.node, future, timeout_sec=timeout_sec
            )
            if future.done():
                return future.result()
            self.node.get_logger().warning(
                f"{label} 第 {attempt}/{SERVICE_CALL_ATTEMPTS} 次调用超时"
            )
            time.sleep(0.2)

        self.node.get_logger().error(f"{label} 重试后仍未返回")
        return None
