"""Storage adapter for raw knowledge uploads."""

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
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / safe_name
        path.write_bytes(data)
        return str(path)

    async def read(self, storage_path: str) -> bytes:
        return Path(storage_path).read_bytes()

    async def delete(self, storage_path: str | None) -> None:
        if not storage_path:
            return
        path = Path(storage_path)
        if path.exists():
            path.unlink()

    def _safe_filename(self, filename: str) -> str:
        name = Path(filename).name.strip() or "document.txt"
        return re.sub(r"[^A-Za-z0-9._-]", "_", name)[:160]


def get_knowledge_storage() -> LocalKnowledgeStorage:
    return LocalKnowledgeStorage(settings.KNOWLEDGE_STORAGE_DIR)
