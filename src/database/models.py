from typing import Optional
from pydantic import BaseModel

class User(BaseModel):
    
    telegram_id: int
    real_name: str
    created_at: str

class DocumentRecord(BaseModel):

    id: Optional[int] = None
    filename: str
    filepath: str  
    scope_type: str
    location: str
    content: str
    author_name: Optional[str] = None
    uploaded_at: Optional[str] = None
    is_active: bool = True
    version: int = 1