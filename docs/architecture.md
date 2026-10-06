# CodeHarness 架构说明

## 总目标

CodeHarness 负责把本地模型的“单次回答”升级为“可以循环执行任务的工程系统”。

## 分层设计

### 1. 模型层 Provider

职责：

- 连接 Ollama
- 发送消息和工具定义
- 接收普通回答或工具调用
- 把上游格式转换成内部统一格式

第一版只实现 Ollama OpenAI 兼容接口。

### 2. Agent Core

职责：

- 保存消息列表
- 执行 Agent Loop
- 判断是最终回答还是工具调用
- 执行工具并把结果回填
- 限制最大循环次数
- 发出可观察事件

核心循环：

```text
加载上下文
while 未完成 and 未超过最大步数:
    调用模型
    记录模型消息
    if 有工具调用:
        执行工具
        记录工具结果
        continue
    输出最终回答
    完成
保存会话
```

### 3. Tool System

每个工具包含：

- 名称
- 中文说明
- 参数 JSON Schema
- 执行函数
- 权限级别

第一版只实现：

- `calculator`
- `list_files`
- `read_file`

### 4. Session Store

第一版使用 JSONL：

- 每行保存一条事件
- 支持继续上次会话
- 方便排查 Agent 的每一步

### 5. Context Compression

后续阶段实现：

- 估算上下文长度
- 保留最近消息
- 把旧消息总结成压缩摘要
- 防止模型上下文溢出

## 事件类型

第一版计划支持：

```text
user_message
assistant_message
tool_call
tool_result
error
session_started
session_finished
```

事件让命令行、Web 和日志共享同一套数据。
