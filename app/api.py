from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.config import settings
from app.schemas import AskRequest, AskResponse, IngestResponse
from app.service import service

router = APIRouter(prefix="/api")


def safe_filename(filename: str | None) -> str:
    name = Path(filename or "").name
    if not name:
        raise ValueError("Uploaded file must have a filename.")
    return name


@router.get("/health")
def health() -> dict[str, object]:
    return {"status": "ok", "sources": service.sources()}


@router.get("/documents")
def documents() -> dict[str, list[str]]:
    return {"documents": service.sources()}


@router.post("/ingest", response_model=IngestResponse)
def ingest(files: list[UploadFile] = File(...)) -> IngestResponse:
    try:
        saved_paths: list[Path] = []
        settings.upload_path.mkdir(parents=True, exist_ok=True)
        for uploaded_file in files:
            filename = safe_filename(uploaded_file.filename)
            target_path = settings.upload_path / filename
            with target_path.open("wb") as temporary_file:
                shutil.copyfileobj(uploaded_file.file, temporary_file)
            saved_paths.append(target_path)
        return service.ingest_paths(saved_paths, copy_uploads=False)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    return service.ask(request.question, request.top_k)
