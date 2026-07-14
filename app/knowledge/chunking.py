"""Text chunking for retrieval."""

import re


class TextChunker:
    def __init__(self, max_chars: int = 1200, overlap_chars: int = 180):
        if max_chars <= 0:
            raise ValueError("max_chars must be positive")
        if overlap_chars < 0:
            raise ValueError("overlap_chars cannot be negative")
        if overlap_chars >= max_chars:
            raise ValueError("overlap_chars must be smaller than max_chars")

        self.max_chars = max_chars
        self.overlap_chars = overlap_chars

    def chunk(self, text: str) -> list[str]:
        cleaned = self._normalize(text)
        if not cleaned:
            return []

        length = len(cleaned)
        min_acceptable_offset = int(self.max_chars * 0.55)
        chunks: list[str] = []
        start = 0

        while start < length:
            end = min(start + self.max_chars, length)
            if end < length:
                end = self._find_boundary(cleaned, start, end, min_acceptable_offset)

            piece = cleaned[start:end].strip()
            if piece:
                chunks.append(piece)

            if end >= length:
                break

            # Guarantee forward progress even in edge configs where the
            # boundary search or a large overlap would otherwise stall.
            start = max(start + 1, end - self.overlap_chars)

        return chunks

    def _normalize(self, text: str) -> str:
        # Collapse whitespace within paragraphs but preserve paragraph
        # breaks, so boundary search below can prefer them over a
        # mid-thought cut.
        paragraphs = re.split(r"\n\s*\n", text.strip())
        cleaned_paragraphs = [re.sub(r"\s+", " ", p).strip() for p in paragraphs]
        return "\n\n".join(p for p in cleaned_paragraphs if p)

    def _find_boundary(self, cleaned: str, start: int, end: int, min_acceptable_offset: int) -> int:
        min_acceptable = start + min_acceptable_offset

        paragraph_break = cleaned.rfind("\n\n", start, end)
        if paragraph_break > min_acceptable:
            return paragraph_break + 2

        sentence_end = cleaned.rfind(". ", start, end)
        if sentence_end > min_acceptable:
            return sentence_end + 1

        space = cleaned.rfind(" ", start, end)
        if space > min_acceptable:
            return space + 1

        return end