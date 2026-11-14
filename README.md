# cybertronic-primebot-playground

启元机器人 Q1/T1 开发实践与活动记录，汇集 ROS2 SDK 入门、交互示例、实验项目、技术笔记与活动复盘，持续沉淀可复现的机器人开发成果。

Personal playground for Primebot Q1 and T1 robots, featuring ROS2 SDK tutorials, interactive demos, experiments, technical notes, and community event recaps.

> 当前阶段：目录与文档框架初始化。尚未添加可运行示例，未完成编译、仿真或真机验证。

## 从这里开始

1. 查看[官方资源索引](docs/resources.md)和[版本兼容记录](docs/compatibility.md)。
2. 按[入门路线](docs/getting-started.md)准备开发环境。
3. 阅读[真机操作约定](docs/robot-operation.md)，再开展实验。
4. 在[活动档案](events/README.md)记录参与过程，在[实验记录](experiments/README.md)保存验证结果。

## 目录导航

```text
cybertronic-primebot-playground/
├── docs/                    # 入门、资源、兼容记录与问题排查
├── events/                  # 按日期组织的活动笔记与复盘
├── tutorials/               # 从实践提炼出的完整教程
├── examples/
│   ├── common/              # 经验证可共用的示例
│   ├── q1/                  # Q1 专属示例
│   └── t1/                  # T1 专属示例
├── projects/                # 完整作品与演示
├── experiments/             # 探索过程、结果与失败记录
├── scripts/                 # 环境检查与诊断工具
├── configs/                 # 可共享的配置模板
├── third_party/primebot/     # Q1/T1 v1.0.0.0 完整 SDK 开发基线
├── manifests/               # 上游地址与依赖版本记录
└── .github/                 # 问题反馈模板与仓库维护约定
```

## 建设顺序

- [x] 建立目录结构与内容约定。
- [ ] 登记活动使用的 SDK、固件及开发环境。
- [ ] 完成首次连接和电池、触摸等状态读取验证。
- [ ] 完成一个语音、表情或灯光交互示例。
- [ ] 整理首份活动复盘与可复现教程。
- [ ] 按机型补充运动实验与完整作品。

## 内容与许可

这是 cybertronic23 的个人实践仓库，非启元官方项目。两个官方 SDK 完整保存在 [third_party/primebot](third_party/primebot/README.md)，作为二次开发基线；模型及其他资源按需引用。第三方内容遵循各自的许可。仓库原创内容遵循 [MIT License](LICENSE)，第三方内容不因被引用而改变许可。

大型视频、原始传感器数据和 SDK 压缩包通过外部链接管理；仓库不保存设备密钥、凭据或个人环境配置。
