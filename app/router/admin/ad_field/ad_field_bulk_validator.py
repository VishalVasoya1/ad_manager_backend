"""Ad Field Bulk Operations Pydantic validators."""

from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, field_validator
from app.router.admin.ad_field.ad_field_validator import AdFieldCreateRequest


class AdFieldBulkCreateRequest(BaseModel):
    """Request model for bulk creating ad fields."""
    fields: List[AdFieldCreateRequest]


class AdFieldBulkUpdateItem(BaseModel):
    """Single ad field update item with ID."""
    id: UUID
    title: Optional[str] = None
    type: Optional[str] = None
    value: Optional[str] = None
    type_value: Optional[str] = None
    regex: Optional[str] = None

    @field_validator("type", mode="before")
    @classmethod
    def validate_type(cls, v):
        """Validate field type if provided."""
        if v is None:
            return v
        valid = ("radio", "dropdown", "input", "textfield", "checkbox")
        if v.lower() not in valid:
            raise ValueError(f"Ad field type must be one of: {', '.join(valid)}")
        return v.lower()


class AdFieldBulkUpdateRequest(BaseModel):
    """Request model for bulk updating ad fields."""
    fields: List[AdFieldBulkUpdateItem]


class AdFieldBulkDeleteRequest(BaseModel):
    """Request model for bulk deleting ad fields."""
    field_ids: List[UUID]


class BulkOperationResult(BaseModel):
    """Result of a bulk operation."""
    success_count: int
    failed_count: int
    failed_ids: List[UUID] = []
    errors: List[str] = []
