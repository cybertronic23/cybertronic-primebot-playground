# 工具脚本

计划存放环境检查、依赖准备与诊断工具。每个脚本注明用途、适用系统、参数及执行影响；涉及系统设置的修改应显式说明。

| 脚本 | 用途 | 依赖 |
| --- | --- | --- |
| [mock_t1_robot.py](mock_t1_robot.py) | 本地假机器人：提供 T1 问候技能所需的 Topic 与服务，用于无真机联调 | `aimdk_msgs`、ROS2 Humble |

## mock_t1_robot.py

只打印收到的请求并返回成功，**不执行任何真实动作**，不能替代真机验证。

提供：

- Topic：`/aima/hal/touch/state`、`/aima/agent/asr_result`
- Service：`GetMcAction`、`SetMcAction`、`SetMcPresetMotion`、`PlayTts`、`PlayEmotion`、`LedStripCommand`

交互模式（终端直接运行）：

```text
t              发送一次单击触摸
d              发送一次双击触摸
a <文本>        发送一条 ASR 最终结果
q              退出
```

自动模式：

```bash
python3 scripts/mock_t1_robot.py --ros-args \
  -p auto_touch_sec:=2.0 -p auto_touch_event:=1 \
  -p auto_asr_sec:=5.0 -p auto_asr_text:="你好启元"
```

参数：

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `initial_action` | `BIPED_LOCOMOTION_DEFAULT` | 起始 MC 动作，用于验证状态切换 |
| `auto_touch_sec` | `0`（关闭） | 自动发送触摸的周期 |
| `auto_touch_event` | `1` | 自动触摸的事件类型 |
| `auto_touch_sensor` | `1` | 自动触摸的传感器 ID |
| `auto_asr_sec` | `0`（关闭） | 自动发送 ASR 的周期 |
| `auto_asr_text` | `你好启元` | 自动发送的识别文本 |
| `interactive` | `true` | 是否启用终端交互（非 TTY 时自动跳过） |
