# T1 语音问候技能

听到关键词后，自动完成「表情 → 灯效 → 语音 → 挥手」的组合动作。

| 项目 | 内容 |
| --- | --- |
| 适用机型 | T1（`sdk_t1-v1.0.0.0`） |
| 开发语言 | Python 3.10 |
| 依赖 | 已编译 `aimdk_msgs`；不需要 OpenCV、Ruckig |
| 开发模式 | **基础开发模式**即可，不触碰关节指令 |
| 验证状态 | 已通过本地假机器人端到端联调；**尚未上机验证** |

动作序列实现在 [`../skill_lib/greeting_actions.py`](../skill_lib/greeting_actions.py)，与[触摸触发版本](../touch-greeting/README.md)共用。

## 功能

```text
/aima/agent/asr_result  (is_final=true, confidence >= 0.5, 命中关键词)
        │
        ├── SetMcAction        → BIPED_LOCOMOTION_WBC（预设动作前置状态）
        ├── PlayEmotion        → 表情（默认 90，失败回退 3003）
        ├── LedStripCommand    → 呼吸灯效
        ├── PlayTts            → 语音播报
        └── SetMcPresetMotion  → 右手挥手（1001）
```

过滤逻辑：

- 只处理 `is_final = true` 的结果，忽略中间识别片段，避免一句话触发多次
- 置信度低于 `min_confidence` 丢弃
- 关键词**包含匹配**，不区分英文大小写
- `cooldown_sec` 冷却，避免连续命中

## 本地联调（不需要真机）

```bash
export PRIMEBOT_REPO="$HOME/Documents/workspace/embodied-ai/my-repo/cybertronic-primebot-playground"
source /opt/ros/humble/setup.bash
source "$PRIMEBOT_REPO/third_party/primebot/sdk_t1-v1.0.0.0/install/setup.bash"

# 终端 1：每 2 秒发一条「你好启元」
python3 scripts/mock_t1_robot.py --ros-args \
  -p auto_asr_sec:=2.0 -p auto_asr_text:="你好启元"

# 终端 2：运行技能
python3 examples/t1/voice-greeting/voice_greeting.py
```

预期：终端 2 打印「命中关键词」并完整下发五个步骤。

## 真机运行

```bash
export PRIMEBOT_REPO="$HOME/Documents/workspace/embodied-ai/my-repo/cybertronic-primebot-playground"
export PRIMEBOT_MODEL=t1
export PRIMEBOT_SDK="$PRIMEBOT_REPO/third_party/primebot/sdk_${PRIMEBOT_MODEL}-v1.0.0.0"

source /opt/ros/humble/setup.bash
source "$PRIMEBOT_SDK/install/setup.bash"

python3 "$PRIMEBOT_REPO/examples/t1/voice-greeting/voice_greeting.py"
```

## 参数

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `keywords` | `你好,启元,hello,hi` | 逗号分隔的关键词列表，包含匹配 |
| `min_confidence` | `0.5` | ASR 最低置信度 |
| `cooldown_sec` | `5.0` | 触发冷却时间 |
| `greeting_text` | `我在呢，有什么可以帮你` | TTS 文本 |
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

示例：换关键词与台词

```bash
python3 examples/t1/voice-greeting/voice_greeting.py --ros-args \
  -p keywords:="启动,表演" \
  -p greeting_text:="马上为你表演"
```

## 预期结果

```text
T1 语音问候技能已启动：keywords=['你好', '启元', 'hello', 'hi'] min_confidence=0.5 cooldown=5.0s
等待语音识别结果，Ctrl+C 退出。
命中关键词「你好」：text='你好启元' confidence=0.95
开始执行问候技能
已进入 BIPED_LOCOMOTION_WBC
表情已下发：90
灯效已下发：mode=254 rgb=(0,120,255) period=800
语音已下发：我在呢，有什么可以帮你
预设动作已入队：1001 task_id=...
问候技能下发完成
```

## 停止方式

- `Ctrl+C` 退出，不会改变机器人当前动作状态。
- 语音识别依赖机器人 ASR 服务，若话题静默，先用 SDK 的 `get_asr_result.py` 确认 ASR 是否工作。

## 验证记录

| 检查项 | 结果 |
| --- | --- |
| 语法 / 导入 | ✅ |
| 消息与服务字段 | ✅ 用真实 `aimdk_msgs` 逐个构造请求 |
| 本地端到端（假机器人） | ✅ 关键词触发、状态切换、四个服务调用全部通过 |
| 反例：文本不含关键词 | ✅ 不触发 |
| 参数覆盖（台词） | ✅ 生效 |
| **真机** | ❌ 未验证 |

## 已知限制与注意

- 机器人的 ASR 是否返回、何时返回由设备端决定；本脚本只做消费与过滤。
- 关键词是**包含匹配**，如「你好」会命中「你好呀」「今天你好吗」。需要精确匹配时改 `on_asr` 逻辑。
- 与触摸版本共用同一套动作序列，注意两个技能同时运行时 `PlayTts` 的打断关系（默认 `is_interrupted=true`）。
- 其余接口限制见[触摸版本 README](../touch-greeting/README.md#已知限制与注意)。
