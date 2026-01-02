"""
Storage Service

JSON-based storage for RFP data, agent outputs, and user edits.
Maintains traceability between RFP clauses and proposal sections.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Any
import uuid

from config.settings import settings


class StorageService:
    """
    Manages persistent storage for RFP Intelligence.
    
    Storage structure:
    - data/rfps/{rfp_id}/
        - metadata.json      # RFP metadata
        - raw_text.txt       # Extracted document text
        - analysis.json      # RFP Analysis Agent output
        - compliance.json    # Compliance Agent output
        - experience.json    # Experience Matching Agent output
        - proposal.json      # Technical Drafting Agent output
        - review.json        # Risk Review Agent output
        - user_edits.json    # User modifications
    """
    
    def __init__(self, data_dir: Optional[Path] = None):
        """Initialize storage service."""
        self.data_dir = data_dir or settings.data_dir
        self.rfps_dir = self.data_dir / "rfps"
        self.outputs_dir = self.data_dir / "outputs"
        self.exports_dir = self.data_dir / "exports"
        
        # Ensure directories exist
        for dir_path in [self.rfps_dir, self.outputs_dir, self.exports_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def _get_rfp_dir(self, rfp_id: str) -> Path:
        """Get directory for an RFP."""
        rfp_dir = self.rfps_dir / rfp_id
        rfp_dir.mkdir(parents=True, exist_ok=True)
        return rfp_dir
    
    def generate_rfp_id(self) -> str:
        """Generate a unique RFP ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique = str(uuid.uuid4())[:8]
        return f"rfp_{timestamp}_{unique}"
    
    # RFP Metadata
    def save_rfp_metadata(self, rfp_id: str, metadata: dict) -> None:
        """Save RFP metadata."""
        rfp_dir = self._get_rfp_dir(rfp_id)
        metadata["rfp_id"] = rfp_id
        metadata["updated_at"] = datetime.now().isoformat()
        
        with open(rfp_dir / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2, default=str)
    
    def get_rfp_metadata(self, rfp_id: str) -> Optional[dict]:
        """Get RFP metadata."""
        metadata_file = self._get_rfp_dir(rfp_id) / "metadata.json"
        if metadata_file.exists():
            with open(metadata_file, "r") as f:
                return json.load(f)
        return None
    
    # Raw Text
    def save_raw_text(self, rfp_id: str, text: str) -> None:
        """Save extracted raw text."""
        rfp_dir = self._get_rfp_dir(rfp_id)
        with open(rfp_dir / "raw_text.txt", "w", encoding="utf-8") as f:
            f.write(text)
    
    def get_raw_text(self, rfp_id: str) -> Optional[str]:
        """Get extracted raw text."""
        text_file = self._get_rfp_dir(rfp_id) / "raw_text.txt"
        if text_file.exists():
            with open(text_file, "r", encoding="utf-8") as f:
                return f.read()
        return None
    
    # Agent Outputs
    def save_agent_output(self, rfp_id: str, agent_name: str, output: dict) -> None:
        """Save agent output."""
        rfp_dir = self._get_rfp_dir(rfp_id)
        output["saved_at"] = datetime.now().isoformat()
        
        with open(rfp_dir / f"{agent_name}.json", "w") as f:
            json.dump(output, f, indent=2, default=str)
    
    def get_agent_output(self, rfp_id: str, agent_name: str) -> Optional[dict]:
        """Get agent output."""
        output_file = self._get_rfp_dir(rfp_id) / f"{agent_name}.json"
        if output_file.exists():
            with open(output_file, "r") as f:
                return json.load(f)
        return None
    
    def get_all_agent_outputs(self, rfp_id: str) -> dict:
        """Get all agent outputs for an RFP."""
        agents = ["analysis", "compliance", "experience", "proposal", "review"]
        outputs = {}
        for agent in agents:
            output = self.get_agent_output(rfp_id, agent)
            if output:
                outputs[agent] = output
        return outputs
    
    # User Edits
    def save_user_edit(self, rfp_id: str, section: str, edit: dict) -> None:
        """Save a user edit to a section."""
        rfp_dir = self._get_rfp_dir(rfp_id)
        edits_file = rfp_dir / "user_edits.json"
        
        edits = {}
        if edits_file.exists():
            with open(edits_file, "r") as f:
                edits = json.load(f)
        
        if section not in edits:
            edits[section] = []
        
        edit["timestamp"] = datetime.now().isoformat()
        edits[section].append(edit)
        
        with open(edits_file, "w") as f:
            json.dump(edits, f, indent=2)
    
    def get_user_edits(self, rfp_id: str) -> dict:
        """Get all user edits for an RFP."""
        edits_file = self._get_rfp_dir(rfp_id) / "user_edits.json"
        if edits_file.exists():
            with open(edits_file, "r") as f:
                return json.load(f)
        return {}
    
    # Document Storage
    def save_uploaded_document(self, rfp_id: str, filename: str, content: bytes) -> Path:
        """Save the original uploaded document."""
        rfp_dir = self._get_rfp_dir(rfp_id)
        doc_path = rfp_dir / f"original_{filename}"
        
        with open(doc_path, "wb") as f:
            f.write(content)
        
        return doc_path
    
    # Export Storage
    def save_export(self, rfp_id: str, filename: str, content: bytes) -> Path:
        """Save an exported document."""
        export_path = self.exports_dir / f"{rfp_id}_{filename}"
        
        with open(export_path, "wb") as f:
            f.write(content)
        
        return export_path
    
    def get_exports(self, rfp_id: str) -> list[Path]:
        """Get all exports for an RFP."""
        return list(self.exports_dir.glob(f"{rfp_id}_*"))
    
    # Listing
    def list_rfps(self) -> list[dict]:
        """List all RFPs with metadata."""
        rfps = []
        for rfp_dir in self.rfps_dir.iterdir():
            if rfp_dir.is_dir():
                metadata = self.get_rfp_metadata(rfp_dir.name)
                if metadata:
                    rfps.append(metadata)
        
        # Sort by created_at descending
        rfps.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return rfps
    
    def delete_rfp(self, rfp_id: str) -> bool:
        """Delete an RFP and all associated data."""
        rfp_dir = self.rfps_dir / rfp_id
        if rfp_dir.exists():
            import shutil
            shutil.rmtree(rfp_dir)
            return True
        return False
    
    # Traceability
    def save_traceability(self, rfp_id: str, traceability: dict) -> None:
        """
        Save traceability mapping between RFP clauses and proposal sections.
        
        Format:
        {
            "requirement_id": {
                "rfp_section": "Section reference",
                "proposal_sections": ["Technical Approach", "Work Plan"],
                "compliance_status": "met",
                "notes": "..."
            }
        }
        """
        rfp_dir = self._get_rfp_dir(rfp_id)
        with open(rfp_dir / "traceability.json", "w") as f:
            json.dump(traceability, f, indent=2)
    
    def get_traceability(self, rfp_id: str) -> Optional[dict]:
        """Get traceability mapping."""
        trace_file = self._get_rfp_dir(rfp_id) / "traceability.json"
        if trace_file.exists():
            with open(trace_file, "r") as f:
                return json.load(f)
        return None


# Module-level instance
_storage = None

def get_storage() -> StorageService:
    """Get or create the storage service instance."""
    global _storage
    if _storage is None:
        _storage = StorageService()
    return _storage
