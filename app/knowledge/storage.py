"""Storage adapter for raw knowledge uploads."""

import asyncio
import re
from pathlib import Path
from uuid import UUID

from app.core.config import settings


class LocalKnowledgeStorage:
    def __init__(self, root: str):
        self.root = Path(root)

    async def save(self, chatbot_id: UUID, document_id: UUID, filename: str, data: bytes) -> str:
        safe_name = self._safe_filename(filename)
        directory = self.root / str(chatbot_id) / str(document_id)

        def _write() -> str:
            directory.mkdir(parents=True, exist_ok=True)
            path = directory / safe_name
            path.write_bytes(data)
            return str(path)

        return await asyncio.to_thread(_write)

    async def read(self, storage_path: str) -> bytes:
        return await asyncio.to_thread(Path(storage_path).read_bytes)

    async def delete(self, storage_path: str | None) -> None:
        if not storage_path:
            return

        def _delete() -> None:
            path = Path(storage_path)
            if path.exists():
                path.unlink()
            # Best-effort cleanup of the now-empty per-document directory.
            try:
                path.parent.rmdir()
            except OSError:
                pass  # not empty, or already gone - either is fine here

        await asyncio.to_thread(_delete)

    def _safe_filename(self, filename: str) -> str:
        name = Path(filename).name.strip() or "document.txt"
        return re.sub(r"[^A-Za-z0-9._-]", "_", name)[:160]


def get_knowledge_storage() -> LocalKnowledgeStorage:
    return LocalKnowledgeStorage(settings.KNOWLEDGE_STORAGE_DIR)