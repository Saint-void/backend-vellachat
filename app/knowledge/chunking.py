"""Text chunking for retrieval."""

import re


class TextChunker:
    def __init__(self, max_chars: int = 1200, overlap_chars: int = 180):
        self.max_chars = max_chars
        self.overlap_chars = overlap_chars

    def chunk(self, text: str) -> list[str]:
        cleaned = re.sub(r"\s+", " ", text).strip()
        if not cleaned:
            return []

        chunks: list[str] = []
        start = 0

        while start < len(cleaned):
            end = min(start + self.max_chars, len(cleaned))
            if end < len(cleaned):
                boundary = cleaned.rfind(".", start, end)
                if boundary > start + int(self.max_chars * 0.55):
                    end = boundary + 1

            chunk = cleaned[start:end].strip()
            if chunk:
                chunks.append(chunk)

            if end >= len(cleaned):
                break
            start = max(0, end - self.overlap_chars)

        return chunks
