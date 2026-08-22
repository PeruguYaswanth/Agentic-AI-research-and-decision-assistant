import re
from typing import List, Dict, Any, Tuple, Optional
import pypdf

class DocumentCleaner:
    """
    Lightweight, structure-aware PDF & Text parser and cleaner.
    Preserves page boundaries, headings, numbers, percentages, dates, lists, and tables
    while stripping repetitive headers, footers, and page artifacts.
    """

    @staticmethod
    def extract_and_clean_pdf(file_path: str) -> List[Dict[str, Any]]:
        """
        Extracts text from PDF page-by-page, detects repeated headers/footers,
        and returns clean page blocks with metadata.
        """
        reader = pypdf.PdfReader(file_path)
        raw_pages: List[Tuple[int, str]] = []

        for idx, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            raw_pages.append((idx, text))

        # Detect repeated running headers and footers across pages
        header_patterns, footer_patterns = DocumentCleaner._find_repeated_lines(raw_pages)

        cleaned_pages = []
        for page_num, raw_text in raw_pages:
            cleaned_text = DocumentCleaner._clean_page_text(raw_text, header_patterns, footer_patterns)
            if cleaned_text.strip():
                cleaned_pages.append({
                    "page_number": page_num,
                    "text": cleaned_text
                })

        return cleaned_pages

    @staticmethod
    def extract_and_clean_text(file_path: str) -> List[Dict[str, Any]]:
        """Reads plain text / markdown files preserving structure."""
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            raw_text = f.read()

        cleaned_text = DocumentCleaner._clean_general_text(raw_text)
        return [{
            "page_number": 1,
            "text": cleaned_text
        }]

    @staticmethod
    def _find_repeated_lines(pages: List[Tuple[int, str]]) -> Tuple[set, set]:
        """Detects identical header/footer lines that occur across 3+ pages."""
        if len(pages) < 3:
            return set(), set()

        first_lines = []
        last_lines = []

        for _, text in pages:
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            if lines:
                first_lines.append(lines[0])
                if len(lines) > 1:
                    last_lines.append(lines[-1])

        # Find lines repeated in > 50% of pages
        threshold = max(2, len(pages) // 2)
        headers = {l for l in first_lines if first_lines.count(l) >= threshold and len(l) > 4}
        footers = {l for l in last_lines if last_lines.count(l) >= threshold and len(l) > 4}
        return headers, footers

    @staticmethod
    def _clean_page_text(text: str, headers: set, footers: set) -> str:
        lines = text.split("\n")
        filtered_lines = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                filtered_lines.append("")
                continue

            # Remove page numbers like "Page 12", "- 12 -", "12 / 45"
            if re.match(r"^(?:page\s*\d+|\-*\s*\d+\s*\-*|\d+\s*/\s*\d+)$", stripped, re.IGNORECASE):
                continue

            # Remove detected recurring running headers/footers
            if stripped in headers or stripped in footers:
                continue

            filtered_lines.append(stripped)

        clean_content = "\n".join(filtered_lines)
        return DocumentCleaner._clean_general_text(clean_content)

    @staticmethod
    def _clean_general_text(text: str) -> str:
        # Fix unicode artifacts and replacement characters
        text = text.replace("\ufffd", "-").replace("\xa0", " ").replace("\r\n", "\n").replace("\r", "\n")

        # Fix hyphenated broken line breaks (e.g. "connec-\ntion" -> "connection")
        text = re.sub(r"(\b[a-zA-Z]{2,})-\n([a-zA-Z]{2,}\b)", r"\1\2", text)

        # Normalize multiple spaces on single lines (preserving newlines)
        text = re.sub(r"[ \t]+", " ", text)

        # Normalize multiple consecutive empty lines to maximum 2
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()
