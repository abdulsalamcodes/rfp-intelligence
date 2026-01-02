"""
Document Routes

Endpoints for document upload and management.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel

from services import get_processor, get_storage


router = APIRouter()


class DocumentUploadResponse(BaseModel):
    """Response from document upload."""
    rfp_id: str
    filename: str
    status: str
    text_length: int
    ocr_used: bool
    warnings: list[str]


class DocumentMetadata(BaseModel):
    """RFP metadata for upload."""
    client_name: Optional[str] = None
    sector: Optional[str] = None
    submission_deadline: Optional[str] = None


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    client_name: Optional[str] = Form(None),
    sector: Optional[str] = Form(None),
    submission_deadline: Optional[str] = Form(None)
):
    """
    Upload an RFP document for processing.
    
    Accepts PDF or DOCX files. Extracts text and stores for analysis.
    Uses OCR automatically if the document appears to be scanned.
    """
    # Validate file type
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    suffix = file.filename.lower().split(".")[-1]
    if suffix not in ["pdf", "docx", "doc"]:
        raise HTTPException(
            status_code=400, 
            detail="Unsupported file format. Please upload PDF or DOCX."
        )
    
    # Read file content
    content = await file.read()
    
    # Generate RFP ID and save document
    storage = get_storage()
    rfp_id = storage.generate_rfp_id()
    storage.save_uploaded_document(rfp_id, file.filename, content)
    
    # Process document
    processor = get_processor()
    try:
        result = processor.process_bytes(content, file.filename)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process document: {str(e)}"
        )
    
    # Save raw text
    storage.save_raw_text(rfp_id, result["text"])
    
    # Save metadata
    metadata = {
        "rfp_id": rfp_id,
        "filename": file.filename,
        "client_name": client_name,
        "sector": sector,
        "submission_deadline": submission_deadline,
        "created_at": datetime.now().isoformat(),
        "status": "uploaded",
        "text_extracted": bool(result["text"]),
        "ocr_used": result.get("ocr_used", False),
        "text_length": len(result["text"])
    }
    storage.save_rfp_metadata(rfp_id, metadata)
    
    return DocumentUploadResponse(
        rfp_id=rfp_id,
        filename=file.filename,
        status="uploaded",
        text_length=len(result["text"]),
        ocr_used=result.get("ocr_used", False),
        warnings=result.get("warnings", [])
    )


@router.get("/{rfp_id}")
async def get_document(rfp_id: str):
    """Get document metadata by RFP ID."""
    storage = get_storage()
    metadata = storage.get_rfp_metadata(rfp_id)
    
    if not metadata:
        raise HTTPException(status_code=404, detail="RFP not found")
    
    return metadata


@router.get("/{rfp_id}/text")
async def get_document_text(rfp_id: str):
    """Get extracted text for a document."""
    storage = get_storage()
    text = storage.get_raw_text(rfp_id)
    
    if text is None:
        raise HTTPException(status_code=404, detail="RFP text not found")
    
    return {
        "rfp_id": rfp_id,
        "text": text,
        "length": len(text)
    }


@router.get("/")
async def list_documents():
    """List all uploaded RFP documents."""
    storage = get_storage()
    return storage.list_rfps()


@router.delete("/{rfp_id}")
async def delete_document(rfp_id: str):
    """Delete an RFP and all associated data."""
    storage = get_storage()
    
    if not storage.get_rfp_metadata(rfp_id):
        raise HTTPException(status_code=404, detail="RFP not found")
    
    storage.delete_rfp(rfp_id)
    return {"status": "deleted", "rfp_id": rfp_id}
