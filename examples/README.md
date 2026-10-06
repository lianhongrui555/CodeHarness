# 示例

## 数学计算

```powershell
code-harness "请计算 12345*6789，并告诉我最终结果。"
```

预期模型自动调用 `calculator` 工具，并返回：

```text
83810205
```

## 连续对话

```powershell
code-harness --interactive
```

可用命令：

- `/reset`：清空会话历史
- `/exit`：退出程序

后续将加入项目结构和文件读取示例。

## 只读项目分析

```powershell
code-harness --workspace D:\CodeHarness "请列出项目根目录，读取 README.md 前 15 行，并总结项目。"
```

## 会话保存与恢复

```powershell
code-harness --workspace D:\CodeHarness --session demo "请记住数字 42。"
code-harness --workspace D:\CodeHarness --session demo --resume "刚才的数字是多少？"
```
