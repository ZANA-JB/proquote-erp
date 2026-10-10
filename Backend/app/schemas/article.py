from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ArticleCreate(BaseModel):
    designation: str = Field(min_length=1, max_length=500)
    quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    unit: Optional[str] = Field(default=None, max_length=64)
    unit_price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)

    model_config = ConfigDict(from_attributes=True)


class ArticleUpdate(BaseModel):
    designation: Optional[str] = Field(default=None, min_length=1, max_length=500)
    quantity: Optional[Decimal] = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    unit: Optional[str] = Field(default=None, max_length=64)
    unit_price: Optional[Decimal] = Field(default=None, ge=0, max_digits=12, decimal_places=2)

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def require_at_least_one_field(self):
        if self.designation is None and self.quantity is None and self.unit is None and self.unit_price is None:
            raise ValueError("At least one field must be provided")
        return self


class ArticleOut(BaseModel):
    id: str
    designation: str
    quantity: Decimal
    unit: Optional[str]
    unit_price: Decimal
    line_total: Decimal

    model_config = ConfigDict(from_attributes=True)
