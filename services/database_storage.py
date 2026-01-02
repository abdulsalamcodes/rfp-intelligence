"""
Database Storage Service

Async storage service using PostgreSQL database.
Provides the same interface as the JSON-based StorageService.
"""

import uuid
from datetime import datetime, timezone, date
from typing import Optional, List, Any

from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    RFP, RFPContent, AgentOutput, UserEdit, Organization
)
from database.connection import AsyncSessionLocal, get_db_context


class DatabaseStorageService:
    """
    Async storage service using PostgreSQL.
    
    All methods are async and require an organization context for multi-tenancy.
    """
    
    def __init__(self, org_id: Optional[str] = None):
        """
        Initialize database storage.
        
        Args:
            org_id: Organization ID for multi-tenant isolation.
                    If None, operates without org filtering (admin mode).
        """
        self.org_id = uuid.UUID(org_id) if org_id else None
    
    async def generate_rfp_id(self) -> str:
        """Generate a unique RFP ID (UUID)."""
        return str(uuid.uuid4())
    
    # =========================================================================
    # RFP Metadata
    # =========================================================================
    
    async def save_rfp_metadata(
        self,
        rfp_id: str,
        metadata: dict,
        created_by: Optional[str] = None
    ) -> None:
        """Save or update RFP metadata."""
        async with get_db_context() as db:
            rfp_uuid = uuid.UUID(rfp_id)
            
            # Check if RFP exists
            result = await db.execute(
                select(RFP).where(RFP.id == rfp_uuid)
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                # Update existing
                existing.filename = metadata.get("filename", existing.filename)
                existing.client_name = metadata.get("client_name")
                existing.sector = metadata.get("sector")
                existing.status = metadata.get("status", existing.status)
                existing.text_length = metadata.get("text_length")
                existing.ocr_used = metadata.get("ocr_used", False)
                
                if metadata.get("submission_deadline"):
                    try:
                        existing.submission_deadline = date.fromisoformat(
                            metadata["submission_deadline"][:10]
                        )
                    except (ValueError, TypeError):
                        pass
            else:
                # Create new RFP
                deadline = None
                if metadata.get("submission_deadline"):
                    try:
                        deadline = date.fromisoformat(
                            metadata["submission_deadline"][:10]
                        )
                    except (ValueError, TypeError):
                        pass
                
                rfp = RFP(
                    id=rfp_uuid,
                    organization_id=self.org_id,
                    created_by=uuid.UUID(created_by) if created_by else None,
                    filename=metadata.get("filename", "unknown"),
                    client_name=metadata.get("client_name"),
                    sector=metadata.get("sector"),
                    submission_deadline=deadline,
                    status=metadata.get("status", "uploaded"),
                    text_length=metadata.get("text_length"),
                    ocr_used=metadata.get("ocr_used", False)
                )
                db.add(rfp)
            
            await db.commit()
    
    async def get_rfp_metadata(self, rfp_id: str) -> Optional[dict]:
        """Get RFP metadata."""
        async with get_db_context() as db:
            try:
                rfp_uuid = uuid.UUID(rfp_id)
            except ValueError:
                return None
            
            query = select(RFP).where(RFP.id == rfp_uuid)
            if self.org_id:
                query = query.where(RFP.organization_id == self.org_id)
            
            result = await db.execute(query)
            rfp = result.scalar_one_or_none()
            
            if not rfp:
                return None
            
            return {
                "rfp_id": str(rfp.id),
                "filename": rfp.filename,
                "client_name": rfp.client_name,
                "sector": rfp.sector,
                "submission_deadline": rfp.submission_deadline.isoformat() if rfp.submission_deadline else None,
                "status": rfp.status,
                "text_length": rfp.text_length,
                "ocr_used": rfp.ocr_used,
                "created_at": rfp.created_at.isoformat() if rfp.created_at else None,
                "updated_at": rfp.updated_at.isoformat() if rfp.updated_at else None
            }
    
    # =========================================================================
    # Raw Text
    # =========================================================================
    
    async def save_raw_text(self, rfp_id: str, text: str) -> None:
        """Save extracted raw text."""
        async with get_db_context() as db:
            rfp_uuid = uuid.UUID(rfp_id)
            
            # Check if content exists
            result = await db.execute(
                select(RFPContent).where(RFPContent.rfp_id == rfp_uuid)
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                existing.raw_text = text
            else:
                content = RFPContent(
                    rfp_id=rfp_uuid,
                    raw_text=text
                )
                db.add(content)
            
            await db.commit()
    
    async def get_raw_text(self, rfp_id: str) -> Optional[str]:
        """Get extracted raw text."""
        async with get_db_context() as db:
            try:
                rfp_uuid = uuid.UUID(rfp_id)
            except ValueError:
                return None
            
            result = await db.execute(
                select(RFPContent.raw_text).where(RFPContent.rfp_id == rfp_uuid)
            )
            row = result.scalar_one_or_none()
            return row
    
    # =========================================================================
    # Agent Outputs
    # =========================================================================
    
    async def save_agent_output(
        self, 
        rfp_id: str, 
        agent_name: str, 
        output: dict
    ) -> None:
        """Save agent output (creates new version if exists)."""
        async with get_db_context() as db:
            rfp_uuid = uuid.UUID(rfp_id)
            
            # Get latest version
            result = await db.execute(
                select(AgentOutput.version)
                .where(
                    AgentOutput.rfp_id == rfp_uuid,
                    AgentOutput.agent_name == agent_name
                )
                .order_by(AgentOutput.version.desc())
                .limit(1)
            )
            latest_version = result.scalar_one_or_none() or 0
            
            # Create new version
            agent_output = AgentOutput(
                rfp_id=rfp_uuid,
                agent_name=agent_name,
                output=output,
                version=latest_version + 1
            )
            db.add(agent_output)
            await db.commit()
    
    async def get_agent_output(
        self, 
        rfp_id: str, 
        agent_name: str,
        version: Optional[int] = None
    ) -> Optional[dict]:
        """Get agent output (latest version by default)."""
        async with get_db_context() as db:
            try:
                rfp_uuid = uuid.UUID(rfp_id)
            except ValueError:
                return None
            
            query = select(AgentOutput).where(
                AgentOutput.rfp_id == rfp_uuid,
                AgentOutput.agent_name == agent_name
            )
            
            if version:
                query = query.where(AgentOutput.version == version)
            else:
                query = query.order_by(AgentOutput.version.desc())
            
            result = await db.execute(query.limit(1))
            agent_output = result.scalar_one_or_none()
            
            if not agent_output:
                return None
            
            return agent_output.output
    
    async def get_all_agent_outputs(self, rfp_id: str) -> dict:
        """Get latest outputs for all agents."""
        agents = ["analysis", "compliance", "experience", "proposal", "review"]
        outputs = {}
        
        for agent in agents:
            output = await self.get_agent_output(rfp_id, agent)
            if output:
                outputs[agent] = output
        
        return outputs
    
    # =========================================================================
    # User Edits
    # =========================================================================
    
    async def save_user_edit(
        self, 
        rfp_id: str, 
        section: str, 
        edit: dict,
        user_id: Optional[str] = None
    ) -> None:
        """Save a user edit to a section."""
        async with get_db_context() as db:
            rfp_uuid = uuid.UUID(rfp_id)
            
            user_edit = UserEdit(
                rfp_id=rfp_uuid,
                user_id=uuid.UUID(user_id) if user_id else None,
                section=section,
                original_content=edit.get("original"),
                edited_content=edit.get("edited")
            )
            db.add(user_edit)
            await db.commit()
    
    async def get_user_edits(self, rfp_id: str) -> dict:
        """Get all user edits for an RFP, grouped by section."""
        async with get_db_context() as db:
            try:
                rfp_uuid = uuid.UUID(rfp_id)
            except ValueError:
                return {}
            
            result = await db.execute(
                select(UserEdit)
                .where(UserEdit.rfp_id == rfp_uuid)
                .order_by(UserEdit.created_at)
            )
            edits = result.scalars().all()
            
            grouped = {}
            for edit in edits:
                if edit.section not in grouped:
                    grouped[edit.section] = []
                grouped[edit.section].append({
                    "original": edit.original_content,
                    "edited": edit.edited_content,
                    "timestamp": edit.created_at.isoformat() if edit.created_at else None
                })
            
            return grouped
    
    # =========================================================================
    # Document Storage
    # =========================================================================
    
    async def save_uploaded_document(
        self, 
        rfp_id: str, 
        filename: str, 
        content: bytes
    ) -> str:
        """Save the original uploaded document."""
        async with get_db_context() as db:
            rfp_uuid = uuid.UUID(rfp_id)
            
            # Get or create RFPContent
            result = await db.execute(
                select(RFPContent).where(RFPContent.rfp_id == rfp_uuid)
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                existing.original_file = content
            else:
                rfp_content = RFPContent(
                    rfp_id=rfp_uuid,
                    original_file=content
                )
                db.add(rfp_content)
            
            await db.commit()
            
        return rfp_id
    
    # =========================================================================
    # Listing
    # =========================================================================
    
    async def list_rfps(self, limit: int = 100, offset: int = 0) -> List[dict]:
        """List all RFPs with metadata."""
        async with get_db_context() as db:
            query = select(RFP).order_by(RFP.created_at.desc())
            
            if self.org_id:
                query = query.where(RFP.organization_id == self.org_id)
            
            query = query.limit(limit).offset(offset)
            
            result = await db.execute(query)
            rfps = result.scalars().all()
            
            return [
                {
                    "rfp_id": str(rfp.id),
                    "filename": rfp.filename,
                    "client_name": rfp.client_name,
                    "sector": rfp.sector,
                    "status": rfp.status,
                    "created_at": rfp.created_at.isoformat() if rfp.created_at else None
                }
                for rfp in rfps
            ]
    
    async def delete_rfp(self, rfp_id: str) -> bool:
        """Delete an RFP and all associated data."""
        async with get_db_context() as db:
            try:
                rfp_uuid = uuid.UUID(rfp_id)
            except ValueError:
                return False
            
            query = delete(RFP).where(RFP.id == rfp_uuid)
            if self.org_id:
                query = query.where(RFP.organization_id == self.org_id)
            
            result = await db.execute(query)
            await db.commit()
            
            return result.rowcount > 0


# Factory function
def get_database_storage(org_id: Optional[str] = None) -> DatabaseStorageService:
    """Get a database storage service instance."""
    return DatabaseStorageService(org_id)
