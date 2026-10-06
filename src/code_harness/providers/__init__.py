"""模型供应商实现。"""

# 对外导出 Ollama Provider。
from code_harness.providers.ollama import OllamaProvider

# 对外导出统一异常。
from code_harness.providers.base import ProviderError

# 声明公开接口。
__all__ = ["OllamaProvider", "ProviderError"]
