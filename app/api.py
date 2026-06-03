from __future__ import annotations

import shutil
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.schemas import AskRequest, AskResponse, IngestResponse
from app.service import service

router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict[str, object]:
    return {"status": "ok", "sources": service.sources()}


@router.get("/documents")
def documents() -> dict[str, list[str]]:
    return {"documents": service.sources()}


@router.post("/ingest", response_model=IngestResponse)
def ingest(files: list[UploadFile] = File(...)) -> IngestResponse:
    temporary_paths: list[Path] = []
    try:
        for uploaded_file in files:
            suffix = Path(uploaded_file.filename or "").suffix
            with NamedTemporaryFile(delete=False, suffix=suffix) as temporary_file:
                shutil.copyfileobj(uploaded_file.file, temporary_file)
                temporary_paths.append(Path(temporary_file.name))
        return service.ingest_paths(temporary_paths)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    finally:
        for path in temporary_paths:
            path.unlink(missing_ok=True)


@router.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    return service.ask(request.question, request.top_k)

