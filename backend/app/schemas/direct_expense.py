from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class DirectExpensePolicyOut(BaseModel):
    id: int
    name: str
    expense_area: str
    min_amount: Decimal
    max_amount: Decimal | None = None
    approval_mode: str


class DirectExpenseInvoiceOut(BaseModel):
    original_name: str
    content_type: str
    size: int
    download_url: str


class DirectExpenseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    record_id: str
    display_id: str
    expense_area: str
    supplier: str
    item_description: str
    amount: Decimal
    requester_user_id: int
    requester_analytics_id: str | None = None
    requester_email: str
    approval_policy_id: int
    invoice: DirectExpenseInvoiceOut
    created_at: datetime
