"""JSONL 会话存储。"""

# 导入日期时间工具。
from datetime import datetime, timezone

# 导入 JSON 工具。
import json

# 导入路径工具。
from pathlib import Path

# 导入正则表达式工具。
import re

# 导入类型工具。
from typing import Any

# 导入消息类型。
from code_harness.core.messages import Message


class SessionError(RuntimeError):
    """表示会话保存或恢复失败。"""


class SessionStore:
    """负责保存和恢复 Agent 会话。"""

    def __init__(self, workspace: str | Path) -> None:
        """初始化会话目录。"""

        # 保存项目根目录。
        self.workspace = Path(workspace).expanduser().resolve()

        # 会话文件统一保存在 .codeharness/sessions 下。
        self.sessions_dir = self.workspace / ".codeharness" / "sessions"

        # 自动创建目录。
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def _validate_session_id(self, session_id: str) -> str:
        """校验会话编号，避免路径穿越。"""

        # 去掉首尾空格。
        session_id = session_id.strip()

        # 必须由字母、数字、下划线或连字符组成。
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", session_id):
            raise SessionError("session_id 只能包含字母、数字、下划线和连字符，长度 1-64")

        # 返回安全编号。
        return session_id

    def session_path(self, session_id: str) -> Path:
        """返回会话文件路径。"""

        # 校验编号。
        safe_id = self._validate_session_id(session_id)

        # 返回 JSONL 文件。
        return self.sessions_dir / f"{safe_id}.jsonl"

    def append_snapshot(self, session_id: str, messages: list[Message]) -> Path:
        """把完整消息快照追加到会话文件。"""

        # 读取安全路径。
        path = self.session_path(session_id)

        # 构造快照记录。
        record: dict[str, Any] = {
            "type": "snapshot",
            "version": 1,
            "session_id": self._validate_session_id(session_id),
            "workspace": str(self.workspace),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "messages": [message.to_api_dict() for message in messages],
        }

        # 使用 try 写入 JSONL。
        try:
            # 追加一行 JSON，并强制使用 UTF-8。
            with path.open("a", encoding="utf-8", newline="\n") as file:
                file.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError as error:
            raise SessionError(f"保存会话失败：{error}") from error

        # 返回会话文件位置。
        return path

    def load_latest(self, session_id: str) -> list[Message]:
        """读取会话文件中最后一份完整快照。"""

        # 读取会话文件路径。
        path = self.session_path(session_id)

        # 文件不存在时返回空历史。
        if not path.exists():
            return []

        # 从最后一行向前查找最新快照。
        try:
            # 读取全部行。
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as error:
            raise SessionError(f"读取会话失败：{error}") from error

        # 反向查找快照记录。
        for line in reversed(lines):
            # 跳过空行。
            if not line.strip():
                continue

            # 尝试解析 JSON。
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            # 只接受快照类型。
            if record.get("type") != "snapshot":
                continue

            # 恢复消息列表。
            return [Message.from_api_dict(item) for item in record.get("messages", [])]

        # 没有有效快照时返回空历史。
        return []

    def clear(self, session_id: str) -> Path:
        """通过写入空快照清空会话，不删除历史文件。"""

        # 追加空快照。
        return self.append_snapshot(session_id, [])

    def list_sessions(self) -> list[str]:
        """列出已有会话编号。"""

        # 返回按名称排序的会话编号。
        return sorted(path.stem for path in self.sessions_dir.glob("*.jsonl"))
