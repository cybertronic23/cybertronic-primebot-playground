# cybertronic-primebot-playground

启元机器人 Q1/T1 开发实践与活动记录。以仓库内两套 ROS2 SDK 为基础，整理环境搭建、接口验证、交互应用与运动实验，持续沉淀可复现的代码、技术笔记和活动成果。

Personal playground for Primebot Q1 and T1 robots, featuring ROS2 SDK tutorials, interactive demos, experiments, technical notes, and community event recaps.

**第一次开发请阅读 [Q1 / T1 SDK 二次开发操作手册](docs/development-guide.md)。** 手册包含环境准备、机型选择、分阶段编译、真实数据验证、Python/C++ 开发示例、板载部署和故障排查。

> 当前状态：已收录两个完整 SDK，完成资料与源码核对，整理开发手册。尚未在本项目完成 Ubuntu/ROS2 编译、仿真或真机验证；文档中的代码与命令属于待实机验证的操作指导。

## SDK 与开发环境

| 项目 | 当前基线 |
| --- | --- |
| Q1 SDK | [sdk_q1-v1.0.0.0](third_party/primebot/sdk_q1-v1.0.0.0/README.md) |
| T1 SDK | [sdk_t1-v1.0.0.0](third_party/primebot/sdk_t1-v1.0.0.0/README.md) |
| 开发系统 | 本地 SDK 指南推荐 Ubuntu 22.04 + ROS2 Humble |
| 通信方式 | ROS2 + FastDDS，开发 PC 与机器人接入同一局域网 |
| 开发语言 | Python / C++ |
| 版本追溯 | [原始文件 SHA-256 清单](manifests/primebot-sdk-files.json)与[兼容记录](docs/compatibility.md) |

两个 SDK 完整保存官方指南、接口定义、消息包、Python/C++ 示例，以及 OpenCV、Ruckig 等随包源码。它们提供同名 ROS2 包，**必须按机型隔离构建和加载环境**，不要在本仓库根目录直接运行无范围限制的 `colcon build`。

Mac 可用于编辑和资料整理；本地 SDK 指南暂不支持 Mac/Windows 原生 SDK 开发。桌面调试工具的跨平台支持与 ROS2 SDK 开发环境是两回事。

## 从零开始：建议操作顺序

| 阶段 | 操作 | 验收目标 |
| --- | --- | --- |
| 1. 环境 | Ubuntu 22.04、ROS2 Humble、colcon 与消息生成依赖 | 能加载 ROS2，导入 rclpy |
| 2. 选择 SDK | Q1 或 T1 二选一，先只编译 aimdk_msgs | 能显示 Bms 定义，包前缀指向所选机型 |
| 3. 连接 | 开发者模式、重启、网线与同网段地址、DDS 配置 | 不仅 Ping 通，还能发现机器人节点 |
| 4. 数据 | 订阅电池和真实触摸事件 | 收到实际传感器数据 |
| 5. 交互 | 分别验证语音、表情或灯光 | 业务响应与真机表现一致 |
| 6. 自有应用 | 在 examples/projects 开发 Python 或独立 C++ 包 | 在新终端可重复运行，并记录结果 |
| 7. 部署 | 按需板载部署，再考虑自启动和运动实验 | 架构、依赖、日志及停止恢复通过验证 |

详细步骤见[完整手册](docs/development-guide.md)。开启开发者功能前阅读设备 APP 启用须知与对应 SDK 使用声明；运动实验另需满足机型、模式、控制权和现场防护要求。

## 最小起步命令

以下在**已安装 ROS2 Humble 及公共依赖的 Ubuntu Bash 终端**执行。先进入本仓库实际目录；首次安装、网络、DDS 缓冲区配置和每个新终端的环境加载步骤见手册。

```bash
export PRIMEBOT_REPO="$PWD"
export PRIMEBOT_MODEL=q1  # 使用 T1 时改为 t1
export PRIMEBOT_SDK="$PRIMEBOT_REPO/third_party/primebot/sdk_${PRIMEBOT_MODEL}-v1.0.0.0"
source /opt/ros/humble/setup.bash
cd "$PRIMEBOT_SDK"
colcon build --base-paths aimdk_msgs --symlink-install \
  --cmake-args -DCMAKE_BUILD_TYPE=Release
source "$PRIMEBOT_SDK/install/setup.bash"
ros2 interface show aimdk_msgs/msg/Bms
```

本机消息包构建成功后，完成手册中的机器人连接与 DDS 配置，再读取真实电池状态：

```bash
ros2 node list
timeout 10 ros2 topic echo /aima/hal/bms/state --once
python3 "$PRIMEBOT_SDK/examples/python/get_bms_state.py"
```

切换机型使用新终端。只读取状态无需先编译整套 OpenCV/Ruckig。原指南中的 `demo.py` 是占位名称，实际运行使用 `get_bms_state.py` 等真实文件。

## 可以基于 SDK 开发什么

| 方向 | SDK 示例与建议 |
| --- | --- |
| 状态监控 | 电量、温度、触摸、音频设备；适合第一个只读应用 |
| 互动展示 | TTS、表情、灯光、音量；可以组合为触摸触发互动 |
| 语音与视觉 | ASR 结果、音频播放/录制、拍照和视频流；按需补充依赖 |
| 高层运动 | 动作模式、预设动作与速度控制；逐机型验证控制权和状态切换 |
| 低层控制 | 关节指令与 Ruckig 轨迹；先满足官方规定的模式和防护条件 |

手册提供最小 Python/C++ 电量节点的编写步骤，并列出 18 个随包示例入口。高级功能按需引入依赖，不将编译全套示例作为所有业务的前置条件。

**已知差异：**Q1 的 C++ 示例包含源码目录库路径和 RPATH 设置，与指南的源码构建路线存在不一致；完整构建尚待验证。详见手册第 3 节。两个机型的动作枚举、关节名称及部分示例也不同，不能直接交换控制参数。

## 仓库组织

```text
cybertronic-primebot-playground/
├── docs/                    # 开发手册、资源、兼容与问题排查
├── events/                  # 按日期组织的活动笔记与复盘
├── tutorials/               # 从实践提炼出的教程
├── examples/
│   ├── common/              # 分别在两个机型验证后提炼的共用示例
│   ├── q1/                  # Q1 自有示例
│   └── t1/                  # T1 自有示例
├── projects/                # 自有完整应用与演示
├── experiments/             # 实验步骤、环境、结果与失败记录
├── scripts/                 # 后续环境检查与诊断工具
├── configs/                 # 可共享配置模板
├── third_party/primebot/    # 两个完整 SDK，默认保留原始基线
│   ├── sdk_q1-v1.0.0.0/
│   └── sdk_t1-v1.0.0.0/
├── manifests/               # 上游来源、依赖版本及原始文件校验
└── .github/                 # 反馈模板与仓库维护约定
```

新功能优先写在自有目录，并依赖选定 SDK；修改第三方源码时单独说明原因。活动记录链接已有项目或实验，避免维护多份重复代码。

## 文档导航

- [完整开发操作手册](docs/development-guide.md)：从环境到应用与部署。
- [入门路线](docs/getting-started.md)、[官方资源](docs/resources.md)、[版本兼容记录](docs/compatibility.md)。
- [问题排查记录约定](docs/troubleshooting.md)、[真机操作约定](docs/robot-operation.md)。
- [活动档案](events/README.md)、[示例约定](examples/README.md)、[实验记录](experiments/README.md)、[作品目录](projects/README.md)。

官方入口：[开发者社区与下载](https://dev.primebot.com/download) · [Q1 上游](https://github.com/PrimebotTech/primebot-q1-sdk) · [T1 上游](https://github.com/PrimebotTech/primebot-t1-sdk) · [活动中心](https://dev.primebot.com/events)。本仓库操作手册针对已收录版本，不自动等同于上游最新版本。

## 建设进度

- [x] 建立活动、实验与应用目录。
- [x] 完整收录 Q1/T1 SDK v1.0.0.0，保存逐文件校验清单。
- [x] 整理开发手册与独立应用开发路线。
- [ ] 在 Ubuntu 22.04 / ROS2 Humble 完成构建验证。
- [ ] 登记真机固件并完成状态、交互接口验证。
- [ ] 发布首个经过验证的自有应用与活动复盘。

## 内容与许可

这是 cybertronic23 的个人实践仓库，非启元官方项目。仓库原创内容遵循 [MIT License](LICENSE)。第三方 SDK、随包依赖和引用资料遵循原有许可及使用声明，不因收录而改变许可。

构建产物、设备私钥、个人配置与原始音视频不提交。大型演示或数据以外部链接管理；实验结果注明本机、仿真或真机验证范围。
