from decimal import Decimal
from datetime import datetime
from typing import Literal
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, HttpUrl, model_validator

class QuotationOptionCreate(BaseModel):
    supplier: str = Field(min_length=2, max_length=200)
    amount: Decimal = Field(gt=0)
    item_url: HttpUrl | None = None
    attachment_pending: bool = Field(default=False, exclude=True)
    notes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode='after')
    def require_support(self):
        if not self.item_url and not self.attachment_pending:
            raise ValueError('Cada cotización debe incluir una URL o un archivo adjunto')
        return self

class QuotationOptionOut(BaseModel):
    id: int
    option_number: int
    supplier: str
    amount: Decimal
    item_url: str | None = None
    notes: str | None = None
    created_at: datetime
    vote_count: int = 0
    class Config: from_attributes = True

class QuotationVoteOut(BaseModel):
    quotation_option_id: int
    voter_email: str
    voter_name: str | None = None
    voter_role: str
    created_at: datetime
    updated_at: datetime
    class Config: from_attributes = True


class ExpenseCreate(BaseModel):
    """Canonical request contract shared by API, ORM and database.

    New code uses expense_area / expense_category end to end. Legacy input names
    remain accepted temporarily so an older deployed client fails gracefully
    during rollout, but serialization and persistence always use canonical names.
    """

    model_config = ConfigDict(populate_by_name=True)

    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=3)
    expense_area: str = Field(
        min_length=2,
        max_length=80,
        validation_alias=AliasChoices('expense_area', 'expense_type'),
    )
    expense_category: str | None = Field(
        default=None,
        max_length=80,
        validation_alias=AliasChoices('expense_category', 'expense_subcategory'),
    )
    urgency: Literal['LOW', 'NORMAL', 'HIGH', 'CRITICAL'] = 'NORMAL'
    request_type: Literal['SIMPLE', 'MULTI_QUOTE'] = 'SIMPLE'
    amount: Decimal | None = Field(default=None, gt=0)
    supplier: str | None = Field(default=None, min_length=2, max_length=200)
    item_url: HttpUrl | None = None
    quotation_options: list[QuotationOptionCreate] = Field(default_factory=list, max_length=10)
    quotation_pending: bool = Field(default=False, exclude=True)
    revised_from_request_id: str | None = Field(default=None, max_length=36)

    @property
    def expense_type(self) -> str:
        """Temporary compatibility alias for legacy backend callers."""
        return self.expense_area

    @property
    def expense_subcategory(self) -> str | None:
        """Temporary compatibility alias for legacy backend callers."""
        return self.expense_category

    @model_validator(mode='after')
    def require_support(self):
        if self.request_type == 'MULTI_QUOTE':
            if len(self.quotation_options) < 2:
                raise ValueError('Debes agregar al menos dos cotizaciones')
            urls = [str(option.item_url).split('#', 1)[0].rstrip('/') for option in self.quotation_options if option.item_url]
            if len(urls) != len(set(urls)):
                raise ValueError('Las cotizaciones no pueden utilizar enlaces idénticos')
            return self
        if self.amount is None or not self.supplier:
            raise ValueError('El monto y el proveedor son obligatorios')
        if not self.item_url and not self.quotation_pending:
            raise ValueError('Debes proporcionar una URL o adjuntar una cotización')
        return self


class AttachmentOut(BaseModel):
    id: int
    original_name: str
    content_type: str
    size: int
    document_type: str
    quotation_option_id: int | None = None

    class Config:
        from_attributes = True


class InvoiceOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    attachment_id: int
    original_name: str
    content_type: str
    size: int
    uploaded_at: datetime
    request_id: str
    display_id: str
    flow_id: str
    title: str
    expense_area: str = Field(validation_alias=AliasChoices('expense_area', 'expense_type'))
    expense_category: str | None = Field(
        default=None,
        validation_alias=AliasChoices('expense_category', 'expense_subcategory'),
    )
    urgency: str = 'NORMAL'
    supplier: str
    amount: Decimal
    requested_by: str
    requester_analytics_id: str | None = None
    expense_status: str
    closed_at: datetime | None = None
    closed_by: str | None = None

    @property
    def expense_type(self) -> str:
        return self.expense_area

    @property
    def expense_subcategory(self) -> str | None:
        return self.expense_category


class ApprovalOut(BaseModel):
    id: int
    flow_id: str
    approver_email: str
    approver_name: str | None = None
    approver_role: str
    step: int
    approval_mode: str
    status: str
    comment: str | None = None
    created_at: datetime
    decided_at: datetime | None = None
    cancelled_at: datetime | None = None
    cancelled_by: str | None = None
    cancellation_reason: str | None = None
    closed_at: datetime | None = None
    closed_by: str | None = None
    closure_notes: str | None = None

    class Config:
        from_attributes = True


class ExpenseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    request_id: str
    flow_id: str
    display_id: str
    revised_from_request_id: str | None = None
    request_type: str = 'SIMPLE'
    title: str
    description: str
    expense_area: str = Field(validation_alias=AliasChoices('expense_area', 'expense_type'))
    expense_category: str | None = Field(
        default=None,
        validation_alias=AliasChoices('expense_category', 'expense_subcategory'),
    )
    urgency: str = 'NORMAL'
    amount: Decimal | None = None
    supplier: str | None = None
    item_url: str | None = None
    requested_by: str
    requester_analytics_id: str | None = None
    status: str
    created_at: datetime
    last_event_at: datetime | None = None
    last_event_type: str | None = None
    cancelled_at: datetime | None = None
    cancelled_by: str | None = None
    cancellation_reason: str | None = None
    closed_at: datetime | None = None
    closed_by: str | None = None
    closure_notes: str | None = None
    approvals: list[ApprovalOut] = Field(default_factory=list)
    attachments: list[AttachmentOut] = Field(default_factory=list)
    quotation_options: list[QuotationOptionOut] = Field(default_factory=list)
    quotation_votes: list[QuotationVoteOut] = Field(default_factory=list)
    quotation_voter_count: int = 0
    quotation_vote_count: int = 0
    quotation_quorum_reached: bool = False
    selected_quotation_id: int | None = None
    approval_policy_id: int | None = None
    approval_policy_mode: str | None = None
    policy_evaluation_amount: Decimal | None = None
    minimum_votes_required: int | None = None
    can_cancel: bool = False
    can_correct: bool = False
    can_close: bool = False
    can_delegate_close: bool = False
    can_vote: bool = False

    @property
    def expense_type(self) -> str:
        return self.expense_area

    @property
    def expense_subcategory(self) -> str | None:
        return self.expense_category
