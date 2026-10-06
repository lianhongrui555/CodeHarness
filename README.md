# CodeHarness

CodeHarness 是一个面向代码项目场景的本地 AI Agent Harness。

它的目标不是重新训练模型，而是在本地大模型外面增加一层可靠的工程外壳，让模型能够：

- 理解用户任务
- 读取项目文件
- 调用受控工具
- 观察工具结果
- 继续决策，直到任务完成
- 保存会话和工程日志

## 当前架构

```text
用户
  ↓
CLI / 后续 Web 接口
  ↓
CodeHarness Agent Loop
  ├─ Ollama 模型适配器
  ├─ 消息与事件系统
  ├─ 工具注册表
  ├─ 文件系统工具
  ├─ 会话存储
  └─ 上下文压缩（后续阶段）
  ↓
本地代码项目
```

## 参考架构

本项目参考 Pi Agent 的分层思想：

- `pi-ai`：模型连接与流式事件
- `pi-agent-core`：Agent Loop、消息、工具调用、会话
- `pi-coding-agent`：代码项目应用层

CodeHarness 使用 Python 实现相同核心思想，并连接本地 Ollama `qwen2.5:7b`。

## 目录结构

```text
CodeHarness/
├─ README.md
├─ pyproject.toml
├─ .gitignore
├─ src/code_harness/       # 核心代码
├─ tests/                  # 自动化测试
├─ docs/                   # 架构和使用文档
├─ docs/logs/              # 工程日志
├─ specs/                  # 分阶段规格说明
└─ examples/               # 示例任务和后续演示
```

## 设计原则

1. 本地优先：优先使用本地 Ollama。
2. 安全优先：文件和命令工具必须限制工作目录。
3. 可观察：模型输出、工具开始、工具结束和错误都要产生事件。
4. 可恢复：会话必须能够保存并继续。
5. 可测试：每个核心模块都要有独立测试。
6. 清晰提交：代码、文档和工程日志通过 Git 管理。

## 当前状态

- [x] 建立工程目录
- [x] 编写架构说明
- [x] 定义消息结构
- [x] 实现最小 Agent Loop
- [x] 实现 Ollama 模型适配器
- [x] 实现工具注册表
- [x] 实现数学工具
- [x] 实现 CLI 入口
- [x] 实现只读文件工具
- [x] 实现会话保存
- [x] 实现上下文压缩
- [x] 实现代码搜索
- [x] 实现 Git 状态、差异和提交历史工具

## GitHub 发布

发布步骤见 docs/github-publish.md。
