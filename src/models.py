"""Modelos Pydantic para validación de entrada/salida."""
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TodoStatus(str, Enum):
    pending = "pending"
    done = "done"


class TodoCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None


class TodoUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    status: Optional[TodoStatus] = None


class TodoOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    status: TodoStatus
    created_at: datetime
    updated_at: datetime
