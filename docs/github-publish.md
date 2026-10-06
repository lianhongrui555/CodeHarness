# 发布到 GitHub

## 当前状态

- 本地仓库已经初始化。
- 当前分支为 `main`。
- 所有代码、测试和文档都已经提交。
- 尚未配置 GitHub 远程仓库。
- 当前电脑尚未安装 GitHub CLI，也未完成 GitHub 登录。

## 方法一：浏览器创建仓库并推送（推荐）

不需要安装 GitHub CLI。

### 1. 在浏览器创建空仓库

打开：

https://github.com/new

填写仓库名称：

```text
CodeHarness
```

选择 Public 或 Private。不要勾选 README、.gitignore 或 License，因为本地仓库已经包含项目文件。

### 2. 复制仓库地址

创建后复制 HTTPS 地址，格式类似：

```text
https://github.com/你的用户名/CodeHarness.git
```

不要把 GitHub 密码或 Token 发到聊天中。

### 3. 配置远程仓库

在 PowerShell 执行：

```powershell
cd D:\CodeHarness
git remote add origin https://github.com/你的用户名/CodeHarness.git
git branch -M main
```

如果提示 `origin` 已经存在，改用：

```powershell
git remote set-url origin https://github.com/你的用户名/CodeHarness.git
```

### 4. 推送

```powershell
git push -u origin main
```

第一次推送时，Git Credential Manager 会打开浏览器或登录窗口。选择 GitHub 账号并授权即可。

### 5. 验证

```powershell
git remote -v
git status
```

浏览器刷新 GitHub 仓库页面，应能看到完整的代码、提交记录和工程日志。

## 方法二：GitHub CLI


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
