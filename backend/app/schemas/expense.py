from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl, model_validator


class ExpenseCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=3)
    expense_type: str = Field(min_length=2, max_length=80)
    expense_subcategory: str | None = Field(default=None, max_length=80)
    amount: Decimal = Field(gt=0)
    supplier: str = Field(min_length=2, max_length=200)
    item_url: HttpUrl | None = None
    quotation_pending: bool = Field(default=False, exclude=True)
    revised_from_request_id: str | None = Field(default=None, max_length=36)

    @model_validator(mode='after')
    def require_support(self):
        if not self.item_url and not self.quotation_pending:
            raise ValueError('Debes proporcionar una URL o adjuntar una cotización')
        return self


class AttachmentOut(BaseModel):
    id: int
    original_name: str
    content_type: str
    size: int
    document_type: str

    class Config:
        from_attributes = True


class InvoiceOut(BaseModel):
    attachment_id: int
    original_name: str
    content_type: str
    size: int
    uploaded_at: datetime
    request_id: str
    display_id: str
    flow_id: str
    title: str
    expense_type: str
    expense_subcategory: str | None = None
    supplier: str
    amount: Decimal
    requested_by: str
    requester_analytics_id: str | None = None
    expense_status: str
    closed_at: datetime | None = None
    closed_by: str | None = None


class ApprovalOut(BaseModel):
    id: int
    flow_id: str
    approver_email: str
    approver_role: str
    step: int
    status: str
    cancelled_at: datetime | None = None
    cancelled_by: str | None = None
    cancellation_reason: str | None = None
    closed_at: datetime | None = None
    closed_by: str | None = None
    closure_notes: str | None = None

    class Config:
        from_attributes = True


class ExpenseOut(BaseModel):
    id: int
    request_id: str
    flow_id: str
    display_id: str
    revised_from_request_id: str | None = None
    title: str
    description: str
    expense_type: str
    expense_subcategory: str | None = None
    amount: Decimal
    supplier: str
    item_url: str | None = None
    requested_by: str
    requester_analytics_id: str | None = None
    status: str
    cancelled_at: datetime | None = None
    cancelled_by: str | None = None
    cancellation_reason: str | None = None
    closed_at: datetime | None = None
    closed_by: str | None = None
    closure_notes: str | None = None
    approvals: list[ApprovalOut] = Field(default_factory=list)
    attachments: list[AttachmentOut] = Field(default_factory=list)

    class Config:
        from_attributes = True
