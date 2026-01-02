"""
RFPs Router (v1)

Production API endpoints for RFP management with multi-tenant support.
"""

from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from database.models import Organization
from api.auth.dependencies import get_current_active_user, get_current_org
from services import get_processor
from services.storage import get_storage
from services.billing import check_can_create_rfp, increment_usage


router = APIRouter(prefix="/rfps", tags=["RFPs"])


# ============================================================================
# Response Models
# ============================================================================

class RFPUploadResponse(BaseModel):
    """Response from RFP upload."""
    rfp_id: str
    filename: str
    status: str
    text_length: int
    ocr_used: bool
    warnings: List[str] = []


class RFPResponse(BaseModel):
    """RFP metadata response."""
    rfp_id: str
    filename: str
    client_name: Optional[str] = None
    sector: Optional[str] = None
    submission_deadline: Optional[str] = None
    status: str
    text_length: Optional[int] = None
    ocr_used: bool = False
    created_at: Optional[str] = None


class RFPTextResponse(BaseModel):
    """RFP text response."""
    rfp_id: str
    text: str
    length: int


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/upload", response_model=RFPUploadResponse)
async def upload_rfp(
    file: UploadFile = File(...),
    client_name: Optional[str] = Form(None),
    sector: Optional[str] = Form(None),
    submission_deadline: Optional[str] = Form(None),
    current_org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload an RFP document for processing.
    
    Requires authentication. RFP is scoped to the user's organization.
    Usage limits are enforced based on subscription plan.
    """
    org_id = str(current_org.id)
    
    # Check usage limits
    can_create, message = await check_can_create_rfp(org_id)
    if not can_create:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=message
        )
    
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
    
    # Get org-scoped storage
    storage = get_storage(org_id)
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
    
    # Increment usage after successful upload
    await increment_usage(org_id)
    
    return RFPUploadResponse(
        rfp_id=rfp_id,
        filename=file.filename,
        status="uploaded",
        text_length=len(result["text"]),
        ocr_used=result.get("ocr_used", False),
        warnings=result.get("warnings", [])
    )


@router.get("", response_model=List[RFPResponse])
async def list_rfps(
    current_org: Organization = Depends(get_current_org)
):
    """List all RFPs for the current organization."""
    storage = get_storage(str(current_org.id))
    rfps = storage.list_rfps()
    
    return [
        RFPResponse(
            rfp_id=rfp.get("rfp_id", ""),
            filename=rfp.get("filename", ""),
            client_name=rfp.get("client_name"),
            sector=rfp.get("sector"),
            submission_deadline=rfp.get("submission_deadline"),
            status=rfp.get("status", "unknown"),
            text_length=rfp.get("text_length"),
            ocr_used=rfp.get("ocr_used", False),
            created_at=rfp.get("created_at")
        )
        for rfp in rfps
    ]


@router.get("/{rfp_id}", response_model=RFPResponse)
async def get_rfp(
    rfp_id: str,
    current_org: Organization = Depends(get_current_org)
):
    """Get RFP metadata by ID."""
    storage = get_storage(str(current_org.id))
    metadata = storage.get_rfp_metadata(rfp_id)
    
    if not metadata:
        raise HTTPException(status_code=404, detail="RFP not found")
    
    return RFPResponse(
        rfp_id=metadata.get("rfp_id", rfp_id),
        filename=metadata.get("filename", ""),
        client_name=metadata.get("client_name"),
        sector=metadata.get("sector"),
        submission_deadline=metadata.get("submission_deadline"),
        status=metadata.get("status", "unknown"),
        text_length=metadata.get("text_length"),
        ocr_used=metadata.get("ocr_used", False),
        created_at=metadata.get("created_at")
    )


@router.get("/{rfp_id}/text", response_model=RFPTextResponse)
async def get_rfp_text(
    rfp_id: str,
    current_org: Organization = Depends(get_current_org)
):
    """Get extracted text for an RFP."""
    storage = get_storage(str(current_org.id))
    text = storage.get_raw_text(rfp_id)
    
    if text is None:
        raise HTTPException(status_code=404, detail="RFP text not found")
    
    return RFPTextResponse(
        rfp_id=rfp_id,
        text=text,
        length=len(text)
    )


@router.delete("/{rfp_id}")
async def delete_rfp(
    rfp_id: str,
    current_org: Organization = Depends(get_current_org)
):
    """Delete an RFP and all associated data."""
    storage = get_storage(str(current_org.id))
    
    if not storage.get_rfp_metadata(rfp_id):
        raise HTTPException(status_code=404, detail="RFP not found")
    
    storage.delete_rfp(rfp_id)
    return {"status": "deleted", "rfp_id": rfp_id}
