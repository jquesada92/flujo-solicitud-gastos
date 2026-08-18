from pydantic import BaseModel, Field


class QuotationVoteRequest(BaseModel):
    quotation_option_id: int = Field(gt=0)
