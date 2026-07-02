"""Memory store — SQLite-backed, replaces JSONL."""
from app.schemas import CoreObject, MachineLesson
from app.memory.database import (
    save_core_object,
    search_core_objects,
    save_lesson_db,
    list_lessons_db,
    save_memory_record,
)


def save_memory(obj: CoreObject) -> None:
    d = obj.model_dump()
    save_core_object(d)
    save_memory_record(d)


def search_memory(query: str, top_k: int = 5) -> list[CoreObject]:
    rows = search_core_objects(query, top_k=top_k)
    return [CoreObject(**r) for r in rows]


def save_lesson(lesson: MachineLesson) -> None:
    save_lesson_db(lesson.model_dump())


def list_lessons() -> list[MachineLesson]:
    rows = list_lessons_db()
    return [MachineLesson(**r) for r in rows]
