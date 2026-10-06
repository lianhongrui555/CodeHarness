"""代码项目工作目录和安全路径检查。"""

# 导入系统路径工具。
from pathlib import Path


class WorkspaceError(ValueError):
    """表示工作目录或路径不合法。"""


class Workspace:
    """限制 Agent 只能在指定项目目录内操作。"""

    def __init__(self, root: str | Path) -> None:
        """初始化工作目录。"""

        # 把传入路径转换成绝对路径。
        self.root = Path(root).expanduser().resolve()

        # 工作目录必须真实存在。
        if not self.root.exists():
            raise WorkspaceError(f"工作目录不存在：{self.root}")

        # 工作目录必须是目录。
        if not self.root.is_dir():
            raise WorkspaceError(f"工作目录不是目录：{self.root}")

        # 禁止密钥、证书、云端凭据和 Git 内部目录。
        self._sensitive_names = {
            ".aws",
            ".ssh",
            ".git",
            ".codeharness",
            "id_rsa",
            "id_ed25519",
        }

        # 默认隐藏常见的依赖、缓存和构建目录。
        self._ignored_names = {
            ".venv",
            "venv",
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
            "node_modules",
            "dist",
            "build",
        }
        # 禁止常见私钥或证书后缀。
        self._sensitive_suffixes = {
            ".key",
            ".pem",
            ".p12",
            ".pfx",
        }

    def is_sensitive(self, path: Path) -> bool:
        """判断路径是否属于敏感文件。"""

        # 计算相对于工作目录的路径片段。
        relative = path.resolve().relative_to(self.root)

        # 逐个检查路径片段。
        for part in relative.parts:
            # 检查敏感目录名。
            if part in self._sensitive_names:
                return True

            # 检查 .env 系列文件。
            if part == ".env" or part.startswith(".env."):
                return True

        # 检查敏感后缀。
        if path.suffix.lower() in self._sensitive_suffixes:
            return True

        # 其他路径允许访问。
        return False

    def is_ignored(self, path: Path) -> bool:
        """判断路径是否属于默认隐藏的缓存或依赖目录。"""

        # 计算相对于工作目录的路径片段。
        relative = path.resolve().relative_to(self.root)

        # 任意路径片段命中隐藏目录时返回 True。
        return any(part in self._ignored_names for part in relative.parts)
    def resolve(self, relative_path: str = ".") -> Path:
        """把相对路径安全地解析成工作目录内的绝对路径。"""

        # 空路径默认表示工作目录。
        raw_path = (relative_path or ".").strip()

        # 拒绝绝对路径，强制使用项目相对路径。
        if Path(raw_path).is_absolute():
            raise WorkspaceError("只能使用工作目录内的相对路径")

        # 拼接并解析真实路径。
        candidate = (self.root / raw_path).resolve()

        # 防止通过 ../ 跳出工作目录。
        if not candidate.is_relative_to(self.root):
            raise WorkspaceError("路径超出工作目录范围")

        # 拒绝敏感路径。
        if self.is_sensitive(candidate):
            raise WorkspaceError(f"禁止访问敏感路径：{relative_path}")

        # 返回安全路径。
        return candidate

    def relative(self, path: Path) -> str:
        """把绝对路径转换成适合展示的项目相对路径。"""

        # 返回使用正斜杠的相对路径。
        return path.resolve().relative_to(self.root).as_posix()
