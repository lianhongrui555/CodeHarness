# 发布到 GitHub

## 当前状态

- 本地仓库已经初始化。
- 当前分支为 `main`。
- 所有代码、测试和文档都已经提交。
- 尚未配置 GitHub 远程仓库。
- 当前电脑尚未安装 GitHub CLI，也未完成 GitHub 登录。

## 推荐发布步骤

### 1. 安装 GitHub CLI

从官方地址安装：

https://cli.github.com/

### 2. 登录 GitHub

在 PowerShell 执行：

```powershell
gh auth login --hostname github.com --git-protocol https --web
```

按照浏览器提示完成授权。不要把密码或 Token 发到聊天中。

### 3. 创建远程仓库并推送

```powershell
cd D:\CodeHarness
gh repo create CodeHarness --public --source . --remote origin --push
```

如果希望创建私有仓库，把 `--public` 改成 `--private`。

### 4. 验证

```powershell
git remote -v
gh repo view --web
```

浏览器会自动打开 GitHub 仓库页面。

## 注意事项

- 不要上传 `.env`、API Key、账号密码和私钥。
- `.codeharness/` 已经加入 `.gitignore`。
- `.venv/`、`__pycache__/` 和构建缓存不会提交。
- 推送前执行：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
git status --short
```
