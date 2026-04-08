from pydantic import BaseModel


class ChatVarEntity(BaseModel):
    """DB mirror of the chat_vars table."""
    id: int
    name: str
    value: str
    enabled: int
    created_at: str
