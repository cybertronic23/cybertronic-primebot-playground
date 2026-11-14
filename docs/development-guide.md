# Q1 / T1 SDK 二次开发操作手册

本手册针对仓库内 `third_party/primebot/sdk_q1-v1.0.0.0` 与 `sdk_t1-v1.0.0.0`，结合两份官方入门指南、消息定义、示例源码与 CMake 配置整理。路径和工作区组织按本仓库调整，不能据此认定支持其他 SDK 或固件版本。

**验证范围：**已核对源码中的包名、文件名、接口和配置，并对文中独立代码片段作静态检查；未在 Ubuntu/ROS2 环境编译，未连接真机。示例中的命令输出是验收目标，不是已完成的测试结果。

## 目录

1. [开发路径与系统结构](#1-开发路径与系统结构)
2. [开发机准备](#2-开发机准备)
3. [选择机型与编译](#3-选择机型与编译)
4. [机器人接入与通信](#4-机器人接入与通信)
5. [分阶段验证](#5-分阶段验证)
6. [Python 二次开发](#6-python-二次开发)
7. [C++ 二次开发](#7-c-二次开发)
8. [交互、音视频与运动开发](#8-交互音视频与运动开发)
9. [板载部署与自启动](#9-板载部署与自启动)
10. [故障排查](#10-故障排查)
11. [实验与提交规范](#11-实验与提交规范)
12. [依据与已知差异](#12-依据与已知差异)

## 1. 开发路径与系统结构

推荐第一条路径：**Ubuntu 开发 PC → 编译一个机型的消息包 → 读取电池状态 → 运行交互示例 → 在仓库自有目录编写应用 → 按需板载部署**。

SDK 是 ROS2 消息、服务及示例的集合，不是一个通过 `pip install primebot` 安装的 Python 产品。消息包经 `colcon` 构建后，Python/C++ 程序通过 ROS2 + FastDDS 接入机器人局域网。

| 位置 | 角色 | 适合放什么 |
| --- | --- | --- |
| 开发 PC | Ubuntu 22.04 + ROS2 Humble | 编译、业务开发、调试与数据分析 |
| 运控板 | HAL、MC、基础交互等服务；指南默认 IP `10.1.1.100` | 优先保障实时控制，不作为首选业务部署位置 |
| 大脑板 | 高阶感知、规划及应用；指南默认 IP `10.1.1.101` | 按资源与架构条件部署业务 |

IP 以设备实际配置为准。PC 可以直接通过 DDS 调用接口，不需要先把所有代码传进机器人，也不需要为每个 ROS2 请求建立 SSH 连接。SSH 主要用于板载部署、文件传输和诊断。

两套 SDK 均提供 `aimdk_msgs`、`aimdk_examples_cpp`、`aimdk_opencv`、`ruckig_for_primebot` 等同名包。**不要在仓库根目录直接执行不限制范围的 `colcon build`，不要在同一个终端同时叠加 Q1 与 T1 的安装环境。**切换机型时打开新终端。

## 2. 开发机准备

### 2.1 操作系统与 ROS2

下面的开发命令统一在 **Ubuntu 22.04 的 Bash 终端**执行，使用系统 Python。Mac 可整理资料和编辑代码；本地 SDK 指南不支持 Mac/Windows 原生开发。虚拟机或容器的网络发现能力也需要额外验证。

先根据 [ROS2 Humble 官方 Ubuntu 安装说明](https://docs.ros.org/en/humble/Installation/Ubuntu-Install-Debs.html)配置软件源并安装 ROS2。不要在未配置 ROS 软件源时直接复制后面的安装命令。

```bash
lsb_release -d
source /opt/ros/humble/setup.bash
echo "$ROS_DISTRO"
python3 --version
```

目标：Ubuntu 22.04，`ROS_DISTRO=humble`。推荐系统 Python 3.10，避免首先引入 Conda 或跨版本 Python 环境，防止 `rclpy` 扩展 ABI 不匹配。

### 2.2 公共依赖

```bash
sudo apt update
sudo apt install -y \
  git cmake build-essential pkg-config \
  python3-colcon-common-extensions python3-dev python3-pip \
  ros-humble-rosidl-default-generators ros-humble-rosidl-default-runtime \
  ros-humble-rmw-fastrtps-cpp
```

检查：

```bash
colcon --help
python3 -c 'import rclpy; print(rclpy.__file__)'
```

### 2.3 按功能补充依赖

只读取 BMS/触摸状态，不需要先编译 OpenCV 或 Ruckig。

| 功能 | 额外依赖 |
| --- | --- |
| Python 图像、音频处理 | `numpy`，视频脚本还使用 `opencv-python` |
| Ruckig Python 模块 | `nanobind`，需编译随包 Ruckig 源码 |
| 完整 C++ 示例 | 随包 OpenCV 4.13.0、Ruckig，以及下述开发库 |

```bash
# 需要 Python 图像、音频或轨迹规划时安装
python3 -m pip install --user numpy opencv-python nanobind

# 需要完整 C++ 示例及视频能力时安装
sudo apt install -y \
  libavcodec-dev libavformat-dev libavutil-dev libswscale-dev \
  libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev \
  libyaml-cpp-dev ffmpeg
```

这些是原指南的依赖路线，未提供经过验证的精确 Python 版本锁定。首次成功运行后，应保存实际安装版本，而不是把未来的最新版视作固定依赖。C++ 示例要求 **OpenCV 4.13.0 EXACT**，单独安装系统 `libopencv-dev` 不一定满足版本。

## 3. 选择机型与编译

### 3.1 获取仓库并设置路径

```bash
mkdir -p "$HOME/workspace"
cd "$HOME/workspace"
git clone https://github.com/cybertronic23/cybertronic-primebot-playground.git
cd cybertronic-primebot-playground
export PRIMEBOT_REPO="$PWD"

# 二选一：当前连接 Q1 时用 q1；连接 T1 时用 t1
export PRIMEBOT_MODEL=q1
export PRIMEBOT_SDK="$PRIMEBOT_REPO/third_party/primebot/sdk_${PRIMEBOT_MODEL}-v1.0.0.0"
test -d "$PRIMEBOT_SDK/aimdk_msgs"
```

已有克隆直接 `cd` 到实际仓库目录并设置变量，不要重复克隆。后文的 `$PRIMEBOT_REPO`、`$PRIMEBOT_MODEL`、`$PRIMEBOT_SDK` 只在当前终端有效。代码路径使用英文且不带空格。

### 3.2 路线 A：先构建消息包（推荐首次使用）

```bash
source /opt/ros/humble/setup.bash
cd "$PRIMEBOT_SDK"
colcon list --base-paths aimdk_msgs
colcon build --base-paths aimdk_msgs --symlink-install \
  --cmake-args -DCMAKE_BUILD_TYPE=Release
source "$PRIMEBOT_SDK/install/setup.bash"

ros2 interface show aimdk_msgs/msg/Bms
python3 -c 'from aimdk_msgs.msg import Bms; print(Bms)'
ros2 pkg prefix aimdk_msgs
```

验收：构建 Summary 无失败；能显示 Bms 字段；包前缀指向**所选机型**的 `install` 目录。此步骤只验证本机消息生成，不证明与机器人通信成功。

### 3.3 路线 B：按需构建轨迹库

```bash
cd "$PRIMEBOT_SDK"
colcon build --base-paths aimdk_msgs examples/ruckig_for_primebot \
  --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release
source "$PRIMEBOT_SDK/install/setup.bash"
cd "$PRIMEBOT_SDK/examples/python"
python3 -c 'import ruckig_for_primebot; print(ruckig_for_primebot.__file__)'
```

Ruckig 的 CMake 默认开启 Python 模块构建，会将模块复制到 `examples/python/`。这些 `.so` 属于本机构建产物，不提交 Git，也不能跨 CPU 架构或 Python ABI 直接复用。从自有项目运行时，还需处理模块搜索路径和动态库路径，见第 6 节。

### 3.4 路线 C：完整 C++ 示例

```bash
cd "$PRIMEBOT_SDK"
colcon list --base-paths aimdk_msgs examples/opencv \
  examples/ruckig_for_primebot examples/cpp
colcon build --base-paths aimdk_msgs examples/opencv \
  examples/ruckig_for_primebot examples/cpp \
  --packages-up-to aimdk_examples_cpp --symlink-install \
  --cmake-args -DCMAKE_BUILD_TYPE=Release
source "$PRIMEBOT_SDK/install/setup.bash"
ros2 pkg executables aimdk_examples_cpp
```

OpenCV 源码编译可能耗时较长、占用较多内存。资源不足时可加 `--executor sequential`，并使用 `CMAKE_BUILD_PARALLEL_LEVEL=2 colcon build ...` 限制单包构建并行度。

**Q1 包的已知配置差异：**`examples/cpp/CMakeLists.txt` 将 `OpenCV_DIR`、`ruckig_for_primebot_DIR` 指向 `examples/*/lib/cmake/`，同时存在源码目录库文件拷贝及 RPATH 设置。本仓库保留原包，没有修改这些配置，也未验证完整构建。如遇找包错误，先单独构建三个依赖包：

```bash
cd "$PRIMEBOT_SDK"
colcon build --base-paths aimdk_msgs examples/opencv examples/ruckig_for_primebot \
  --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release
source "$PRIMEBOT_SDK/install/setup.bash"
find "$PRIMEBOT_SDK/install" \( -name OpenCVConfig.cmake -o -name ruckig_for_primebot-config.cmake \) -print
```

后续处理应依据实际生成路径：调整自有构建配置，或以独立提交修正 SDK 的硬编码路径和运行时库查找；不要从其他机器复制任意 `.so` 来填目录。若只需业务开发，可先走消息包 + 自有 C++ 包路线，避开完整示例的 OpenCV/Ruckig 强制依赖。

### 3.5 每个新终端加载环境

```bash
# 先重新设置第 3.1 节的三个路径变量，再执行
source /opt/ros/humble/setup.bash
source "$PRIMEBOT_SDK/install/setup.bash"
ros2 pkg prefix aimdk_msgs
printenv RMW_IMPLEMENTATION FASTRTPS_DEFAULT_PROFILES_FILE FASTDDS_DEFAULT_PROFILES_FILE
```

SDK 环境钩子只在相关变量尚未设置时注入默认值，不会无条件覆盖旧值。如果变量指向另一机型或旧安装目录，在新终端清理相关旧配置后重新加载；不要编辑生成的 `install/setup.bash`。首次构建也建议使用只加载 ROS2、未加载其他机型 SDK 的干净终端。

## 4. 机器人接入与通信

### 4.1 开启开发者模式

本地指南流程：手机 PrimeBot APP 连接机器人 → 设置 → 开发者功能 → 阅读启用须知 → 开发者模式 → 选择基础或高级层级 → 保存配置 → 按提示重新上下电。

指南明确提示启用二次开发功能涉及维保条款，现场操作前阅读设备 APP 中的实际须知。首次状态读取、基础交互优先使用基础开发模式；低层运控需要按官方说明进入对应高级能力并处理控制权。

当前本地版本以 ROS2 为开发入口；指南中的 REST/gRPC API 开发方式标记为暂未支持，不据此设计 HTTP 控制程序。

### 4.2 有线网络

推荐开发 PC 网线直连。Ubuntu 设置 → Network → Wired → IPv4 → Manual：

| 项目 | 指南建议值 |
| --- | --- |
| PC 地址 | `10.1.1.99`，先确认无冲突 |
| 子网掩码 | `255.255.255.0` |
| 网关 | 留空 |
| 运控板 / 大脑板 | `10.1.1.100` / `10.1.1.101`，以实际为准 |

```bash
ip -br addr
ping -c 3 10.1.1.100
ping -c 3 10.1.1.101
```

多网卡、VPN、虚拟网卡和热点可能干扰 DDS 选路。先检查路由，必要时暂时断开无关网络。Ping 成功只证明 IP 可达。

### 4.3 DDS 环境与缓冲区

```bash
source /opt/ros/humble/setup.bash
source "$PRIMEBOT_SDK/install/setup.bash"
printenv ROS_DOMAIN_ID ROS_LOCALHOST_ONLY RMW_IMPLEMENTATION
sysctl net.core.rmem_max net.core.wmem_max
```

`ROS_DOMAIN_ID` 必须与目标机器人一致，指南默认通常为 0；多机活动需由现场统一分配并同步配置机器人，不能只修改 PC。`ROS_LOCALHOST_ONLY=1` 会阻止跨机器发现。修改 DDS 环境后停止旧节点，重启 ROS2 daemon 再测试：

```bash
# 单机、且已确认机器人使用域 0 时的示例
export ROS_DOMAIN_ID=0
export ROS_LOCALHOST_ONLY=0
ros2 daemon stop
ros2 daemon start
```

随包 profile 默认 UDPv4，收发 buffer 均为 `20971520` 字节。若内核上限较小，按指南临时设置 24 MiB；已有更大配置时不必调低：

```bash
sudo sysctl -w net.core.rmem_max=25165824
sudo sysctl -w net.core.wmem_max=25165824
```

确认适合当前开发机后，可持久化：

```bash
sudo tee /etc/sysctl.d/99-primebot-sdk.conf >/dev/null <<'EOF'
net.core.rmem_max = 25165824
net.core.wmem_max = 25165824
EOF
sudo sysctl --system
```

以上仅用于 Ubuntu/Linux。profile 自动加载不会替你修改内核参数。

多网卡仍有问题时，在**所选机型**的 `aimdk_msgs/config/fastdds_profiles.xml` 中按原说明启用 `interfaceWhiteList`，填写 PC 的通信网卡地址（例如 `10.1.1.99`），不是机器人地址；重新构建消息包，重新加载环境并重启节点。个人 IP 修改不要直接混入可共享配置。

## 5. 分阶段验证

### 5.1 发现服务

```bash
ros2 node list
ros2 topic list -t
ros2 service list -t
```

预期能看到机器人节点、`/aima/...` Topic 和对应服务。未构建消息包时也可能发现节点，但解析 `aimdk_msgs` 数据必须加载已构建环境。

### 5.2 读取真实电池状态

```bash
timeout 10 ros2 topic echo /aima/hal/bms/state --once
# 或运行随包脚本（持续输出，Ctrl+C 结束订阅）
python3 "$PRIMEBOT_SDK/examples/python/get_bms_state.py"
```

应看到真实电池数据。原始 `Bms` 中电压/电流/功率分别使用 mV/mA/mW；脚本显示时转换为 V/A/W。不要误用原始数值单位。超时没有数据不能判定成功。

### 5.3 触摸事件

```bash
python3 "$PRIMEBOT_SDK/examples/python/get_touch_state.py"
```

监听后实际触摸设备，观察事件。事件型 Topic 在没有事件时不输出是可能的正常情况。

原指南还给出模拟发布触摸数据的方法。若用于验证本机消息收发，应在**不连接真实机器人、无业务订阅者的独立测试域**进行；模拟事件成功不等于真实传感器工作正常，不应向活动现场机器人域不断注入伪造触摸事件。

### 5.4 TTS 服务

先核对现场是否存在该服务及类型：

```bash
ros2 service type /aimdk_5Fmsgs/srv/PlayTts
ros2 interface show aimdk_msgs/srv/PlayTts
ros2 service call /aimdk_5Fmsgs/srv/PlayTts aimdk_msgs/srv/PlayTts \
  '{header: {}, tts_req: {text: "你好，我是启元机器人", priority_level: {value: 6}, domain: "sdk_test", is_interrupted: true}}'
```

`/aimdk_5Fmsgs/srv/PlayTts` 是服务名称，`aimdk_msgs/srv/PlayTts` 是服务类型，拼写不能互换。响应中的业务结果应检查 `tts_resp.is_success`、`error_message`，同时确认实际播报；仅看到 ROS2 请求发送成功不足以判断业务成功。

## 6. Python 二次开发

### 6.1 自有代码位置

简单、可复用示例放 `examples/q1/<name>/` 或 `examples/t1/<name>/`；独立完整应用放 `projects/<name>/`。确认两个机型都验证通过后，再提炼到 `examples/common/`。

避免首先修改第三方代码。Python 业务只需加载选定 SDK 的 install 环境，再导入 `rclpy`、`aimdk_msgs`。不需要为一个只读订阅程序复制整个 SDK。

### 6.2 最小业务节点：读取电量

在仓库创建 `projects/battery-monitor/main.py`，内容如下。这是供开发者创建的示范片段，当前仓库尚未附带该程序文件：

```python
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from aimdk_msgs.msg import Bms


class BatteryMonitor(Node):
    def __init__(self):
        super().__init__("cybertronic_battery_monitor")
        self.subscription = self.create_subscription(
            Bms, "/aima/hal/bms/state", self.on_bms, qos_profile_sensor_data
        )

    def on_bms(self, msg):
        self.get_logger().info(
            f"Battery {msg.remaining_capacity_percentage}% | "
            f"{msg.voltage / 1000.0:.2f} V | {msg.temperature:.1f} C"
        )


def main():
    rclpy.init()
    node = BatteryMonitor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
```

运行：

```bash
source /opt/ros/humble/setup.bash
source "$PRIMEBOT_SDK/install/setup.bash"
python3 "$PRIMEBOT_REPO/projects/battery-monitor/main.py"
```

验收：可导入消息类，节点能发现真实发布者，输出实际电量，退出后无后台残留。程序启动却没有消息时，回到网络、QoS 和设备发布状态排查。

### 6.3 组合交互逻辑

例如“触摸 → 播报 → 表情”的开发步骤：

1. 先独立验证真实触摸、TTS、表情三个接口。
2. 订阅 TouchState，根据所选机型的事件定义判断触发条件。
3. 使用异步 service client，避免在订阅回调内阻塞等待服务。
4. 添加去抖、冷却时间和任务并发约束，避免连续触摸产生播报队列。
5. 对请求超时、业务失败和设备断连分别记录结果。
6. 将机型、服务名、表情 ID、音量等写入应用配置模板。

使用实际 `msg/srv` 定义构造请求，不根据自然语言描述猜字段或资源 ID。

### 6.4 依赖环境与 Ruckig

优先系统 Python。确需 venv 时，使用同一系统解释器并允许访问系统 ROS2 包，例如 `python3 -m venv --system-site-packages .venv`（需安装 `python3-venv`），激活后重新验证 `import rclpy` 和 `aimdk_msgs`。

从自有目录使用随包 Ruckig 模块时，可在已成功构建后按当前终端配置：

```bash
export PYTHONPATH="$PRIMEBOT_SDK/examples/python${PYTHONPATH:+:$PYTHONPATH}"
# 检查实际动态库依赖；仅导入测试，不下发运动指令
ldd "$PRIMEBOT_SDK"/examples/python/ruckig_for_primebot*.so
python3 -c 'import ruckig_for_primebot; print(ruckig_for_primebot.__file__)'
```

若提示共享库 `not found`，查明 `install` 中实际库目录，再为应用启动环境配置对应 `LD_LIBRARY_PATH` 或正确的 RPATH。不要把 Linux 扩展模块复制回 Mac 使用。复制运动示例时还要保留 `common/mc_action_switcher.py` 等本地模块依赖。

## 7. C++ 二次开发

### 7.1 首选独立 ROS2 包

推荐将自有包置于仓库 `projects/`，在仓库外建立 overlay 工作区，选定一个已构建 SDK 作为 underlay。这样不混入另一机型，也不修改上游示例 CMake。

下面创建一个只依赖 `rclcpp` 和 `aimdk_msgs` 的包；在尚未创建同名包时执行：

```bash
source /opt/ros/humble/setup.bash
source "$PRIMEBOT_SDK/install/setup.bash"
mkdir -p "$PRIMEBOT_REPO/projects/cpp-battery"
cd "$PRIMEBOT_REPO/projects/cpp-battery"
ros2 pkg create --build-type ament_cmake --license MIT \
  cybertronic_battery --dependencies rclcpp aimdk_msgs
```

将以下代码保存为包内 `src/battery_monitor.cpp`：

```cpp
#include <memory>
#include "rclcpp/rclcpp.hpp"
#include "aimdk_msgs/msg/bms.hpp"

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  auto node = std::make_shared<rclcpp::Node>("cybertronic_battery_monitor");
  auto subscription = node->create_subscription<aimdk_msgs::msg::Bms>(
    "/aima/hal/bms/state", rclcpp::SensorDataQoS(),
    [node](aimdk_msgs::msg::Bms::ConstSharedPtr msg) {
      RCLCPP_INFO(node->get_logger(), "Battery %u%% | %.2f V",
        static_cast<unsigned>(msg->remaining_capacity_percentage),
        msg->voltage / 1000.0);
    });
  rclcpp::spin(node);
  rclcpp::shutdown();
  return 0;
}
```

在生成的 `CMakeLists.txt` 中确认已存在 `find_package(rclcpp REQUIRED)`、`find_package(aimdk_msgs REQUIRED)`，在最后的 `ament_package()` **之前**添加：

```cmake
add_executable(battery_monitor src/battery_monitor.cpp)
ament_target_dependencies(battery_monitor rclcpp aimdk_msgs)
install(TARGETS battery_monitor DESTINATION lib/${PROJECT_NAME})
```

建立并编译独立工作区：

```bash
export PRIMEBOT_APP_WS="$HOME/workspace/primebot-app-${PRIMEBOT_MODEL}"
mkdir -p "$PRIMEBOT_APP_WS/src"
ln -s "$PRIMEBOT_REPO/projects/cpp-battery/cybertronic_battery" \
  "$PRIMEBOT_APP_WS/src/cybertronic_battery"
cd "$PRIMEBOT_APP_WS"
colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release
source "$PRIMEBOT_APP_WS/install/setup.bash"
ros2 run cybertronic_battery battery_monitor
```

符号链接只需建立一次，已存在时不重复执行。此路线依赖第 3.2 节生成的 `aimdk_msgs`，无需为只读电池节点编译全套 C++ 示例。

### 7.2 在官方示例中试验

也可在所选 SDK 的 `examples/cpp/src/` 新增 `.cpp`，将无后缀文件名加入 `EXAMPLE_TARGETS`，再重新编译、加载并 `ros2 run aimdk_examples_cpp <名称>`。这是修改第三方基线，应单独提交并说明原因。

需要 OpenCV 或 Ruckig 的自有节点，应按源码中的方式显式增加 `find_package`、链接库及 package.xml 依赖。普通消息订阅节点不应被强制绑定视频库。部署前还需验证动态链接库和 RPATH；编译成功不等于目标板上可以运行。

## 8. 交互、音视频与运动开发

### 8.1 随包示例索引

两个机型都有以下同名 Python/C++ 示例，但参数、资源和实现不保证相同。Python 在 `examples/python/<名称>.py`，C++ 在 `examples/cpp/src/<名称>.cpp`；运行前阅读对应文件头部、参数声明及接口说明。以下为索引，不是运行结果。

| 能力 | 示例名称 | 准备与验收重点 |
| --- | --- | --- |
| 电池、触摸 | `get_bms_state`、`get_touch_state` | 先做真实状态读取 |
| 语音识别结果 | `get_asr_result` | 检查设备是否实际产生 ASR 事件 |
| 音频设备 | `get_audio_device_list` | 确认设备枚举及音频模块状态 |
| 音量、静音及 TTS | `volume_control` | 阅读菜单与服务响应，避免意外更改现场音量 |
| 表情、灯光 | `play_emotion`、`play_lights` | 使用所选机型文档列出的有效资源 |
| 拍照、视频 | `get_jpg`、`get_video_stream` | 相机通道、RTSP 地址、OpenCV/FFmpeg 与显示环境 |
| 音频播放、录音 | `play_audio_from_pc`、`play_audio_from_robot`、`record_audio` | 本机/板载路径差异、SSH 密钥、音频格式、授权与存储 |
| 高层动作与预设动作 | `set_mc_action`、`set_preset_motion` | 机型动作 ID、当前模式、控制权及现场停止流程 |
| 速度控制 | `mc_locomotion_velocity` | 速度范围、刷新频率、超时行为及控制权切换 |
| 上半身与关节控制 | `upper_body_control`、`joint_control` | 关节映射、限位、轨迹库、高低层控制冲突 |
| 任务终止 | `shutdown_task` | 是任务接口，不应当成通用硬件急停 |

只读示例运行方式：

```bash
python3 "$PRIMEBOT_SDK/examples/python/get_asr_result.py"
# 已完成完整 C++ 构建时：
ros2 run aimdk_examples_cpp get_bms_state
```

SDK 没有 `demo.py` 或名为 `demo` 的 C++ 可执行目标；原指南中的这两个名字是占位表达，应换成实际文件/目标名称。

### 8.2 音视频

先读取每个脚本的使用说明再提供参数。部分脚本使用 argparse，部分使用 ROS 参数或位置参数，不能假设所有脚本都支持 `--help`。录音和 PC 音频上传示例还涉及 SSH/SCP。

视频窗口在无图形桌面或无显示转发的 SSH 会话中可能无法显示，应区分“收到数据”与“GUI 显示成功”。采集文件保存在本地数据目录或外部存储，仓库只提交说明和必要的授权样例。

### 8.3 运动开发阶段

按“理解状态与模式 → 验证高层动作 → 小范围应用组合 → 低层关节开发”推进，不直接从关节指令开始。

在具体运动实验中记录：控制来源、动作/关节名称、单位、限位、输入频率、启动姿态、停止及恢复方式。`Ctrl+C` 只保证客户端进程尝试退出，不保证机器人已经停止；以对应接口与现场验证为准。

低层关节控制前必须按 SDK 要求关闭本体高层运控，并平放、悬挂或采取规定防护。Q1/T1 关节名称与动作枚举有差异；例如 T1 脚本使用 `FL_HIP_PITCH_Joint` 等名称，Q1 示例使用 `right_hip_pitch_joint` 等名称，不能互抄。

T1 `joint_control.py` 对控制频率、watchdog 及退出阻尼有特定说明。这些是该脚本/机型的约束，不自动推广到 Q1；先读所选机型源码和固件接口。本文不提供可直接执行的通用关节目标值。

## 9. 板载部署与自启动

### 9.1 先在 PC 验证，再选择部署板卡

确认目标 CPU 架构、系统库、Python/ROS2 版本。x86 编译产物不能直接作为 ARM 程序运行；原指南提到官方 Docker 原生/交叉编译环境，但它们不包含在这两个 SDK 目录中，需从官方资源页另外获取并按对应说明使用。

开发 PC 上运行通过后，再传输自有代码和所需资源到板端。板端 Python 同样需要可用的 ROS2、匹配的消息安装环境和依赖，不能只复制 `main.py` 就假定可运行。

### 9.2 SSH 与文件传输

设备密钥由售后提供，目标板卡的密钥可能不同。建议将私钥保存在仓库外的 `~/.ssh/`，而非照搬原指南放进 SDK 目录：

```bash
# 替换为售后提供并存放好的实际密钥路径
export PRIMEBOT_KEY="$HOME/.ssh/primebot_device_key"
chmod 600 "$PRIMEBOT_KEY"
ssh -i "$PRIMEBOT_KEY" run@10.1.1.101
# 在开发 PC 执行，目标目录需先确认存在且当前用户可写
scp -i "$PRIMEBOT_KEY" ./your_resource.wav \
  run@10.1.1.101:/home/user/cybertronic/
```

不要提交无扩展名的 `id_ed25519` 私钥；通用 `*.key` 忽略规则不会匹配这种文件名。

### 9.3 存放与手动验收

| 内容 | 本地指南建议 |
| --- | --- |
| 音视频、模型及配置 | `/home/user/<项目>/` |
| 日志与 bag | `/robot/persist/log/`、`/robot/persist/bag/` |
| 普通长期组件 | `/opt` |
| 接入官方进程管理的模块 | `/robot/software/<模块>/`，以自启动章节为准 |

先在板端手动启动，检查消息导入、DDS、资源路径、日志、退出行为和运行资源。不在资源紧张的运控板部署大模型或大型数据处理任务。

### 9.4 自启动接入步骤

1. 在 `/robot/software/<模块>/bin/` 部署启动脚本，并赋执行权限。
2. 脚本使用真实绝对路径加载 ROS2 和所选 SDK，设置需要的 DDS 域及日志目录；脚本进程管理应将停止信号传递给业务进程，单进程可使用 `exec python3 /绝对路径/main.py`。
3. 确认目标板与实际配置文件，备份 `/robot/software/process_manager/bin/cfg/` 下对应 YAML。Q1/T1、硬件版本和板号不同，不能把指南中的示例文件名当成通用路径。
4. 只向 `apps` 添加自有模块的 `path`、`sudo`、`stderr` 和 `env`，并按官方说明加入第二阶段 `startup_stages`。不删改现有核心模块。
5. 手动验证脚本后，再验证重启启动、停启、日志和资源占用；失败时恢复备份并保存原因。

板端诊断命令（模块名使用实际值）：

```bash
yamo em doctor
yamo em stop-app my_module
yamo em start-app my_module
top -o %CPU
free -h
df -h
```

首次开发不需要立即接入自启动。完整 YAML 结构应参考对应机型指南第 4 节和设备原配置。

## 10. 故障排查

| 现象 | 按顺序检查 |
| --- | --- |
| Ping 不通 | 电源、开发者模式与重启、网线、PC 静态地址、实际设备 IP、地址冲突、路由 |
| Ping 通但发现不到节点 | ROS_DOMAIN_ID、ROS_LOCALHOST_ONLY、FastDDS 环境、多网卡/组播/防火墙、daemon 旧缓存 |
| 找到节点但 echo 无数据 | 消息环境、发布者是否实际发数据、事件触发条件、QoS、UDP buffer 与过滤规则 |
| `Cannot determine type` / 无法导入 aimdk_msgs | 是否构建消息包、是否在当前终端 source、包前缀是否为当前机型 |
| 无法导入 rclpy | 是否加载 ROS2，是否误用了 Conda/不同 Python ABI |
| Service 一直等待 | 先用 service list/type 验证名称和类型，再查设备模块、模式和网络 |
| TTS 返回但没声音 | 检查 tts_resp 的业务结果、静音/音量及任务状态 |
| 缺少 nanobind | 给 CMake 实际选用的 Python 安装 nanobind，核对解释器路径 |
| OpenCV/Ruckig 找包失败 | 是否构建依赖、安装路径与 CMake 硬编码；尤其检查 Q1 示例配置 |
| 程序提示共享库 not found | 用 ldd 核对真实库位置、目标架构、RPATH/运行环境 |
| colcon 报重复包名 | 是否错误扫描两套 SDK；缩小 base-paths，使用一个机型工作区 |
| 编译内存不足 | 限制并行；先构建消息包，再逐步加功能 |

不要把全局关闭防火墙作为默认安装步骤。先记录 `sudo ufw status verbose` 和网络拓扑，根据隔离开发网络与实际策略排查 DDS UDP 流量；若进行临时策略实验，要记录原设置并恢复。

反馈问题时附：SDK/仓库 commit、机型与固件、开发层级、板卡/PC 架构、ROS2/Python 版本、复现命令、节点/Topic/Service 列表、业务响应及必要日志。日志与 bag 从板端导出后先脱敏，不直接提交整个目录。

## 11. 实验与提交规范

每次真实运行在 `experiments/YYYY-MM-DD-short-name/` 建立记录，至少包含：

- 目标及所选机型、硬件/固件、SDK 路径、仓库 commit。
- 开发机系统、架构、Python/ROS2、依赖版本、开发者模式。
- 网络拓扑、域配置、实际命令及改动参数。
- 预期结果、真实结果、失败情况、停止与恢复结果。
- 日志/视频证据链接、是否仅本机/仿真/真机验证。

自有代码放 examples/projects，教程放 tutorials，活动过程放 events。修改 SDK 源码时说明原因，不覆盖 `manifests/primebot-sdk-files.json` 中原始基线哈希来隐藏差异。构建产物、设备私钥和原始音视频不提交。

首次开发完成的验收清单：

- [ ] 确定一个机型与固件，完成环境记录。
- [ ] 编译该机型消息包，确认包前缀正确。
- [ ] 真机发现、BMS 数据与触摸事件通过。
- [ ] 至少一个交互接口的业务结果与实际表现一致。
- [ ] 自有节点可在新终端重复运行，退出与失败处理明确。
- [ ] 保存复现步骤与实验结果，再决定是否部署板端。

## 12. 依据与已知差异

本手册以仓库保存的文件为主要依据：

- [Q1 快速入门与集成指南](../third_party/primebot/sdk_q1-v1.0.0.0/PrimeBot_SDK快速入门与集成指南.md)、[Q1 接口说明](../third_party/primebot/sdk_q1-v1.0.0.0/接口说明.md)、[Q1 使用声明](../third_party/primebot/sdk_q1-v1.0.0.0/友好用户使用声明.md)。
- [T1 快速入门与集成指南](../third_party/primebot/sdk_t1-v1.0.0.0/PrimeBot_SDK快速入门与集成指南.md)、[T1 接口说明](../third_party/primebot/sdk_t1-v1.0.0.0/接口说明.md)、[T1 使用声明](../third_party/primebot/sdk_t1-v1.0.0.0/友好用户使用声明.md)。
- [Q1 C++ 构建配置](../third_party/primebot/sdk_q1-v1.0.0.0/examples/cpp/CMakeLists.txt)、[T1 C++ 构建配置](../third_party/primebot/sdk_t1-v1.0.0.0/examples/cpp/CMakeLists.txt)。
- [原始 SDK 文件校验清单](../manifests/primebot-sdk-files.json)。
- [colcon 包发现参数](https://colcon.readthedocs.io/en/released/reference/discovery-arguments.html)：`--base-paths` 限定递归发现范围，默认从当前目录扫描。

本仓库的工作区隔离、先构建消息包、自有代码目录和独立 overlay 方案是整理后的推荐操作，并非宣称上游逐条提供的同一流程。Q1 C++ 路径差异尚未修复；官方示例中的占位名称已在本文替换为实际入口。遇到运行差异优先核对所选机型源码、设备固件及现场状态。
