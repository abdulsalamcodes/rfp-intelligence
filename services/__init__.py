"""
RFP Intelligence - Services Package

Document processing and storage services.
"""

from services.document_processor import (
    DocumentProcessor,
    get_processor,
    extract_text,
    extract_text_from_bytes,
    OCR_AVAILABLE
)
from services.storage import (
    StorageService,
    get_storage
)

__all__ = [
    "DocumentProcessor",
    "get_processor",
    "extract_text",
    "extract_text_from_bytes",
    "OCR_AVAILABLE",
    "StorageService",
    "get_storage",
]
