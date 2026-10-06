"""测试 JSONL 会话存储。"""

# 导入路径工具。
from pathlib import Path

# 导入 pytest。
import pytest

# 导入消息类型。
from code_harness.core.messages import Message

# 导入会话存储。
from code_harness.sessions.store import SessionError, SessionStore


def test_session_store_save_and_load_latest(tmp_path: Path) -> None:
    """会话应能保存并恢复最新快照。"""

    # 创建会话存储。
    store = SessionStore(tmp_path)

    # 保存第一份快照。
    store.append_snapshot("demo", [Message.user("第一问")])

    # 保存第二份快照。
    store.append_snapshot("demo", [Message.user("第一问"), Message.assistant("第一答")])

    # 恢复最新快照。
    messages = store.load_latest("demo")

    # 验证消息。
    assert [message.content for message in messages] == ["第一问", "第一答"]
    assert store.list_sessions() == ["demo"]

    # 文件必须是 JSONL。
    assert store.session_path("demo").suffix == ".jsonl"


def test_session_store_clear_keeps_history(tmp_path: Path) -> None:
    """清空会话应写入空快照而不是删除文件。"""

    # 创建会话存储并保存消息。
    store = SessionStore(tmp_path)
    path = store.append_snapshot("demo", [Message.user("内容")])

    # 清空会话。
    store.clear("demo")

    # 最新快照应为空。
    assert store.load_latest("demo") == []

    # 原文件仍然存在，并包含多行历史。
    assert path.exists()
    assert len(path.read_text(encoding="utf-8").splitlines()) == 2


def test_session_store_rejects_path_traversal(tmp_path: Path) -> None:
    """非法会话编号必须被拒绝。"""

    # 创建会话存储。
    store = SessionStore(tmp_path)

    # 拒绝目录穿越。
    with pytest.raises(SessionError):
        store.session_path("../escape")

    # 拒绝路径分隔符。
    with pytest.raises(SessionError):
        store.session_path("a/b")
