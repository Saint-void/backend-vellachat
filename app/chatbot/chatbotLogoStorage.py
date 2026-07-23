"""Storage adapter for chatbot logos."""

import asyncio
from pathlib import Path
from uuid import UUID

from app.core.coreExceptions import ValidationError


class ChatbotLogoStorage:
    """Manages chatbot logo file storage on disk."""

    # Valid image MIME types
    VALID_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}
    # Mapping from MIME type to file extension
    MIME_TO_EXT = {
        "image/png": "png",
        "image/jpeg": "jpg",
        "image/webp": "webp",
        "image/gif": "gif",
    }

    def __init__(self, root: str, max_bytes: int = 2 * 1024 * 1024):
        self.root = Path(root)
        self.max_bytes = max_bytes

    async def replace(self, chatbot_id: UUID, mime_type: str, data: bytes) -> Path:
        """
        Replace the logo for a chatbot.

        Args:
            chatbot_id: The chatbot's UUID
            mime_type: The MIME type of the image (e.g., "image/png")
            data: The raw image bytes

        Returns:
            Path object for the saved file (not yet written to disk for new files)

        Raises:
            ValidationError: If mime_type is invalid, data is not a valid image, or file is too large
        """
        if mime_type not in self.VALID_TYPES:
            raise ValidationError(f"Unsupported image type: {mime_type}")

        if len(data) > self.max_bytes:
            raise ValidationError(f"Image exceeds maximum size of {self.max_bytes} bytes")

        # Validate that the data is actually an image by checking magic bytes
        self._validate_image_data(mime_type, data)

        # Delete old logo if exists
        old_path = await self.resolve(chatbot_id)
        if old_path:
            await self.delete(str(old_path))

        ext = self.MIME_TO_EXT[mime_type]
        filename = f"logo.{ext}"
        directory = self.root / str(chatbot_id)

        def _write() -> Path:
            directory.mkdir(parents=True, exist_ok=True)
            path = directory / filename
            path.write_bytes(data)
            return path

        return await asyncio.to_thread(_write)

    async def resolve(self, chatbot_id: UUID) -> Path | None:
        """
        Find the logo file for a chatbot.

        Returns:
            Path object if logo exists, None otherwise
        """
        directory = self.root / str(chatbot_id)

        def _resolve() -> Path | None:
            if not directory.exists():
                return None

            for ext in self.MIME_TO_EXT.values():
                path = directory / f"logo.{ext}"
                if path.exists():
                    return path

            return None

        return await asyncio.to_thread(_resolve)

    async def read(self, storage_path: str) -> bytes:
        """Read logo file contents."""
        def _read() -> bytes:
            return Path(storage_path).read_bytes()

        return await asyncio.to_thread(_read)

    async def delete(self, storage_path: str | None) -> None:
        """Delete a logo file."""
        if not storage_path:
            return

        def _delete() -> None:
            path = Path(storage_path)
            if path.exists():
                path.unlink()
            # Best-effort cleanup of the now-empty directory
            try:
                path.parent.rmdir()
            except OSError:
                pass

        await asyncio.to_thread(_delete)

    def _validate_image_data(self, mime_type: str, data: bytes) -> None:
        """Validate that data matches the claimed MIME type by checking magic bytes."""
        if len(data) < 4:
            raise ValidationError("Image data too small")

        magic_bytes = {
            "image/png": b"\x89PNG",
            "image/jpeg": b"\xff\xd8\xff",
            "image/webp": b"RIFF",  # RIFF header; WebP specific check would need more bytes
            "image/gif": b"GIF8",
        }

        expected_magic = magic_bytes.get(mime_type)
        if expected_magic and not data.startswith(expected_magic):
            raise ValidationError(f"Invalid image data for {mime_type}")
