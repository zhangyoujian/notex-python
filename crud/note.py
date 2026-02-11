from sqlalchemy import select, update, desc, delete
from sqlalchemy.ext.asyncio import AsyncSession
from models.notebook import Note
from utils import logger
import os


async def db_create_note(db: AsyncSession,
                         notebook_id: str,
                         title: str,
                         content: str,
                         type_: str,
                         source_ids: str,
                         metadata_: str):
    note = Note(notebook_id=notebook_id, title=title, content=content, type=type_, source_ids=source_ids, metadata=metadata_)
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return note


async def db_get_note_by_id(db: AsyncSession, note_id: str):
    query = select(Note).where(Note.id == note_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def db_list_notes(db: AsyncSession, notebook_id: str):
    query = select(Note).where(Note.notebook_id == notebook_id).order_by(desc(Note.created_at))
    result = await db.execute(query)
    return result.scalars().all()


async def db_get_note_by_file_name(db: AsyncSession, file_name: str):
    query = select(Note)
    result = await db.execute(query)
    notes = result.scalars().all()
    for note in notes:
        if note.type == "infograph":
            logger.debug(f"Found infograph note {note.id}, metadata: {note.metadata_}")

        image_url = note.metadata_dict.get("image_url", "")
        if len(image_url) > 0:
            logger.debug(f"Checking image_url: {os.path.basename(image_url)} vs {file_name}")

        if os.path.basename(image_url) == file_name:
            return note

        slides = note.metadata_dict.get("slides", "")

        if isinstance(list, slides):
            for slide in slides:
                if os.path.basename(slide) == file_name:
                    return note
        elif isinstance(str, slides):
            if os.path.basename(slides) == file_name:
                return note

    logger.debug(f"Checked {len(notes)} notes, file not found")

    return None


async def db_delete_note(db: AsyncSession, note_id: str):
    stmt = delete(Note).where(Note.id == note_id)
    await db.execute(stmt)
    await db.commit()

