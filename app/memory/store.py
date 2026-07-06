"""Memory store — SQLite-backed with episodic + semantic recall.

Layered architecture:
    store.py (public API)
      ├─ database.py    (core_objects, traces, lessons)
      ├─ episodic.py    (agent episodic memory, P2-3)
      └─ vector_db.py   (sqlite-vec backend)
"""

from app.memory.database import (
    list_lessons_db,
    save_core_object,
    save_lesson_db,
    save_memory_record,
    search_core_objects,
)
from app.memory.episodic import save_episode, search_episodes, recent_episodes, stats as episodic_stats
from app.schemas import CoreObject, MachineLesson


def save_memory(obj: CoreObject) -> None:
    d = obj.model_dump()
    save_core_object(d)
    save_memory_record(d)

    # Also index as episodic memory for agent recall
    try:
        save_episode(
            content=d.get("content", ""),
            source=d.get("source", "core"),
            metadata={"object_type": d.get("object_type", "document")},
        )
    except Exception:
        pass


def search_memory(query: str, top_k: int = 5) -> list[CoreObject]:
    # Try episodic (semantic) search first
    episodes = search_episodes(query, top_k=top_k)
    if episodes:
        return [CoreObject(**e) for e in episodes]

    # Fallback to LIKE-based search
    rows = search_core_objects(query, top_k=top_k)
    return [CoreObject(**r) for r in rows]


def save_lesson(lesson: MachineLesson) -> None:
    save_lesson_db(lesson.model_dump())


def list_lessons() -> list[MachineLesson]:
    rows = list_lessons_db()
    return [MachineLesson(**r) for r in rows]
