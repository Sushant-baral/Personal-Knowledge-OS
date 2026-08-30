"""
CRUD operations for long-term memory. Deliberately simple: plain SQL rows,
no embeddings, no ranking beyond recency. The agent decides *when* to
call retrieve_memories(); this module just stores and fetches.
"""

from typing import List, Optional

from sqlalchemy.orm import Session

from app.database.models import Memory


def store_memory(db: Session, user_id: int, content: str, memory_type: str = "general") -> Memory:
    memory = Memory(user_id=user_id, content=content.strip(), memory_type=memory_type)
    db.add(memory)
    db.commit()
    db.refresh(memory)
    return memory


def retrieve_memories(
    db: Session, user_id: int, memory_type: Optional[str] = None, limit: int = 10
) -> List[Memory]:
    q = db.query(Memory).filter(Memory.user_id == user_id)
    if memory_type:
        q = q.filter(Memory.memory_type == memory_type)
    return q.order_by(Memory.created_at.desc()).limit(limit).all()


def update_memory(
    db: Session, memory_id: int, content: Optional[str] = None, memory_type: Optional[str] = None
) -> Optional[Memory]:
    memory = db.get(Memory, memory_id)
    if not memory:
        return None
    if content is not None:
        memory.content = content.strip()
    if memory_type is not None:
        memory.memory_type = memory_type
    db.commit()
    db.refresh(memory)
    return memory


def delete_memory(db: Session, memory_id: int) -> bool:
    memory = db.get(Memory, memory_id)
    if not memory:
        return False
    db.delete(memory)
    db.commit()
    return True
