"""配置管理"""
import os
from typing import Optional, Dict, Any
from pydantic import BaseModel

class Config(BaseModel):
    """HelloAgents配置类"""
    
    # LLM配置
    default_model: str = "gpt-3.5-turbo"
    default_provider: str = "openai"
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    
    # 系统配置
    debug: bool = False
    log_level: str = "INFO"
    
    # 其他配置
    max_history_length: int = 100
    

#     @classmethod 的作用是：把一个方法变成“类方法”。

# 普通方法第一个参数是 self，表示当前对象实例；类方法第一个参数通常是 cls，表示当前类本身。

# 比如：

# class A:
#     def normal(self):
#         pass

#     @classmethod
#     def build(cls):
#         pass
# 区别是：

# normal() 需要先创建对象再调用
# build() 可以直接通过类调用
# 例如：

# a = A()
# a.normal()
# 而类方法可以这样：

# A.build()
    @classmethod
    def from_env(cls) -> "Config":
        """从环境变量创建配置"""
        return cls(
            debug=os.getenv("DEBUG", "false").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            temperature=float(os.getenv("TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("MAX_TOKENS")) if os.getenv("MAX_TOKENS") else None,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.dict()
