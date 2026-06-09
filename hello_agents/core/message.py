"""消息系统"""
from typing import Optional, Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel

# 定义消息角色的类型，限制其取值
MessageRole = Literal["user", "assistant", "system", "tool"]

class Message(BaseModel):
    """消息类"""
    
    content: str
    role: MessageRole
    timestamp: datetime = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __init__(self, content: str, role: MessageRole, **kwargs):
        super().__init__(
            content=content,
            role=role,
            timestamp=kwargs.get('timestamp', datetime.now()),
            metadata=kwargs.get('metadata', {})
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（OpenAI API格式）"""
        return {
            "role": self.role,
            "content": self.content
        }
    
    def __str__(self) -> str:
        return f"[{self.role}] {self.content}"
    
#     def __str__(self) 是 Python 里的一个特殊方法，用来定义：
# 这个对象被转成字符串时，应该显示什么。
# 举个例子：

# class Message:
#     def __init__(self, content):
#         self.content = content

#     def __str__(self):
#         return f"Message: {self.content}"
#     然后：

# msg = Message("hello")
# print(msg)
# 输出会是：

# Message: hello
# 如果你不写 __str__，Python 默认打印出来通常会像这样：

# <__main__.Message object at 0x000001...>
