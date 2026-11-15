# T1 触摸问候技能

触摸机器人后，自动完成「表情 → 灯效 → 语音 → 挥手」的组合动作，用于现场演示与二次开发起步。

| 项目 | 内容 |
| --- | --- |
| 适用机型 | T1（`sdk_t1-v1.0.0.0`） |
| 开发语言 | Python 3.10 |
| 依赖 | 已编译 `aimdk_msgs`；不需要 OpenCV、Ruckig |
| 开发模式 | **基础开发模式**即可，不触碰关节指令 |
| 验证状态 | 已通过本地假机器人端到端联调；**尚未上机验证** |

动作序列实现在 [`../skill_lib/greeting_actions.py`](../skill_lib/greeting_actions.py)，与[语音触发版本](../voice-greeting/README.md)共用。

## 功能

```text
/aima/hal/touch/state  (sensor_id=1 背部, event_type=1 单击)
        │
        ├── SetMcAction        → BIPED_LOCOMOTION_WBC（预设动作前置状态）
        ├── PlayEmotion        → 表情（默认 90，失败回退 3003）
        ├── LedStripCommand    → 呼吸灯效
        ├── PlayTts            → 语音播报
        └── SetMcPresetMotion  → 右手挥手（1001）
```

## 前置条件

1. 已按 `docs/development-guide.md` 完成 `aimdk_msgs` 编译。
2. 手机 APP 已开启**开发者模式**，机器人重新上下电。
3. PC 与机器人同网段（默认 `10.1.1.99` ↔ `10.1.1.100/101`）。
4. 内核 UDP 缓冲区已按 SDK 要求调大（≥ 24 MB）。
5. 只连一个网卡，或按 SDK 文档绑定 FastDDS 网卡 IP。

## 本地联调（不需要真机）

仓库提供假机器人节点 [`scripts/mock_t1_robot.py`](../../../scripts/mock_t1_robot.py)，可提供同名 Topic 与服务。

```bash
export PRIMEBOT_REPO="$HOME/Documents/workspace/embodied-ai/my-repo/cybertronic-primebot-playground"
source /opt/ros/humble/setup.bash
source "$PRIMEBOT_REPO/third_party/primebot/sdk_t1-v1.0.0.0/install/setup.bash"

# 终端 1：每 2 秒自动发一次单击触摸
python3 scripts/mock_t1_robot.py --ros-args -p auto_touch_sec:=2.0

# 终端 2：运行技能
python3 examples/t1/touch-greeting/touch_greeting.py
```

预期：终端 2 打印完整的下发日志，终端 1 打印收到的 SetMcAction / PlayEmotion / LedStripCommand / PlayTts / SetMcPresetMotion 请求。

## 真机运行

```bash
export PRIMEBOT_REPO="$HOME/Documents/workspace/embodied-ai/my-repo/cybertronic-primebot-playground"
export PRIMEBOT_MODEL=t1
export PRIMEBOT_SDK="$PRIMEBOT_REPO/third_party/primebot/sdk_${PRIMEBOT_MODEL}-v1.0.0.0"

source /opt/ros/humble/setup.bash
source "$PRIMEBOT_SDK/install/setup.bash"

python3 "$PRIMEBOT_REPO/examples/t1/touch-greeting/touch_greeting.py"
```

只验证逻辑、不调用服务：

```bash
python3 examples/t1/touch-greeting/touch_greeting.py --ros-args -p dry_run:=true
```

## 参数

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `sensor_id` | `1` | 触摸传感器：T1 中 1=背部，2=胸部 |
| `event_type` | `1` | 事件类型：1=单击、2=双击……见 `TouchState.msg` |
| `cooldown_sec` | `3.0` | 触发冷却时间，防止连续触摸叠加动作 |
| `greeting_text` | `你好呀，我是启元机器人` | TTS 文本，建议 100 字以内 |
| `emotion_id` | `90` | T 系列默认表情；失败自动回退 3003 |
| `preset_motion` | `1001` | 预设动作编号，`1001`=右手挥手 |
| `enable_motion` | `true` | 是否切换状态并播放动作 |
| `enable_tts` | `true` | 是否播报语音 |
| `enable_emotion` | `true` | 是否播放表情 |
| `enable_light` | `true` | 是否设置灯效 |
| `led_mode` | `254` | 254=自定义呼吸、255=自定义闪烁 |
| `led_r/g/b` | `0/120/255` | 仅自定义模式生效 |
| `led_period` | `800` | 呼吸周期（ms），0 表示常亮 |
| `dry_run` | `false` | 只打印执行计划，不调用服务 |

示例：改成双击触发、说别的话：

```bash
python3 examples/t1/touch-greeting/touch_greeting.py --ros-args \
  -p event_type:=2 \
  -p greeting_text:="欢迎来到启元展台"
```

## 预期结果

```text
T1 触摸问候技能已启动：sensor_id=1 event_type=1 cooldown=3.0s
等待触摸事件，Ctrl+C 退出。
检测到触摸：sensor_id=1 event_type=1
开始执行问候技能
Requesting MC action: BIPED_LOCOMOTION_WBC
MC reached action: BIPED_LOCOMOTION_WBC (status=100)
已进入 BIPED_LOCOMOTION_WBC
表情已下发：90
灯效已下发：mode=254 rgb=(0,120,255) period=800
语音已下发：你好呀，我是启元机器人
预设动作已入队：1001 task_id=...
问候技能下发完成
```

机器人表现为：屏幕换表情、灯带呼吸、说话、同时右手挥手。

## 停止方式

- `Ctrl+C` 退出。脚本**不会**改变机器人当前动作状态，挥手会自然播完。
- 异常情况在另一个终端执行 `ros2 node list` 确认进程，必要时 `kill <pid>`。

## 验证记录

| 检查项 | 结果 |
| --- | --- |
| 语法 / 导入 | ✅ |
| 消息与服务字段 | ✅ 用真实 `aimdk_msgs` 逐个构造请求 |
| 本地端到端（假机器人） | ✅ 触摸触发、状态切换、四个服务调用全部通过 |
| 反例：sensor_id 不匹配 | ✅ 不触发 |
| 反例：双击设为单击 | ✅ 不触发 |
| 参数覆盖（双击、台词） | ✅ 生效 |
| **真机** | ❌ 未验证 |

## 已知限制与注意

- 触摸话题按事件触发，没有触摸时不产生数据；监听静默属于正常现象。
- `SetMcPresetMotion` 的 `interrupt=false` 且正在播放其他动画时会被**静默拒绝**，返回 `state` 仍是 `RUNNING`，只能靠 `header.code` 判定（本脚本检查了 `code`）。
- `area` 字段仅作上层标识，系统不会据此过滤动作。
- TTS 是异步调度，`is_success=true` 只代表入队成功。
- 表情 ID 必须来自内置表情库，不支持自定义。
- 预设动作前必须先进入 `BIPED_LOCOMOTION_WBC`，由 SDK 的 `McActionSwitcher` 自动完成。
