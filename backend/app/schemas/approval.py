from pydantic import BaseModel, Field


class ApprovalDecision(BaseModel):
    decision: str = Field(pattern='^(APPROVED|REJECTED|REVISION_REQUESTED)$')
    comment: str | None = None
