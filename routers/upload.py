from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pypdf import PdfReader
import io
from config.db_config import get_session
from models import Source, User
from service.auth import get_current_user
from service.vector import get_vector_service, VectorService

router = APIRouter(prefix="/api/upload", tags=["upload"])


@router.post("", response_model=Source)
async def upload_file(
        file: UploadFile = File(...),
        notebook_id: str = Form(...),
        current_user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_session),
        vector_service: VectorService = Depends(get_vector_service)
):
    # Verify file type
    content = ""
    file_type = "file"

    try:
        if file.content_type == "application/pdf":
            # Read PDF
            pdf_content = await file.read()
            pdf_file = io.BytesIO(pdf_content)
            reader = PdfReader(pdf_file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            content = text
            file_type = "pdf"
        elif file.content_type in ["text/plain", "text/markdown", "application/json"]:
            # Read text
            content_bytes = await file.read()
            content = content_bytes.decode("utf-8")
            file_type = "text"
        else:
            # Try to read as text for other types
            try:
                content_bytes = await file.read()
                content = content_bytes.decode("utf-8")
                file_type = "text"
            except:
                raise HTTPException(
                    status_code=400,
                    detail="Unsupported file type. Please upload PDF or text files."
                )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error reading file: {str(e)}"
        )

    if not content.strip():
        raise HTTPException(
            status_code=400,
            detail="File is empty"
        )

    # Create Source record
    source = Source(
        notebook_id=notebook_id,
        name=file.filename,
        type=file_type,
        content=content,  # Store full content in DB (might be large, but okay for MVP)
        file_name=file.filename,
        file_size=len(content),
        chunk_count=0
    )

    # Chunk content and add to Vector DB
    # Simple chunking by paragraphs or fixed size
    chunk_size = 1000
    overlap = 200
    chunks = []

    # Naive chunking
    text_len = len(content)
    start = 0
    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunk = content[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap

    source.chunk_count = len(chunks)

    # Add to DB
    session.add(source)
    await session.commit()
    await session.refresh(source)

    # Add to Vector DB
    if chunks:
        metadatas = [{
            "source_id": source.id,
            "notebook_id": notebook_id,
            "chunk_index": i,
            "source_name": file.filename
        } for i in range(len(chunks))]

        vector_service.add_texts(
            texts=chunks,
            metadatas=metadatas
        )

    return source
