"""Décrit les données échangées pour les cotations."""

from decimal import Decimal
from datetime import date
from typing import List, Literal, Optional
from pydantic import BaseModel, EmailStr, ConfigDict, Field, field_validator, model_validator
from app.schemas.article import ArticleCreate, ArticleOut


class QuotationCreate(BaseModel):
    client_name: str = Field(min_length=1, max_length=250)
    client_email: EmailStr
    client_address: Optional[str] = Field(default=None, max_length=1000)
    client_reference: Optional[str] = Field(default=None, max_length=100)
    validity_date: date
    delivery_duration: str = Field(min_length=1, max_length=100)
    incoterm: str = Field(min_length=1, max_length=50)
    special_conditions: Optional[str] = Field(default=None, max_length=4000)
    vat_mode: Literal["sans_tva", "avec_tva"] = "sans_tva"
    vat_code: Optional[str] = Field(default=None, min_length=1, max_length=100)
    vat_rate: Optional[Decimal] = Field(default=None, gt=0, le=100, max_digits=5, decimal_places=2)
    payment_method: Optional[str] = Field(default=None, max_length=250)
    payment_terms: Optional[str] = Field(default=None, max_length=500)
    articles: List[ArticleCreate]

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def validate_articles(cls, values):
        if not values.articles:
            raise ValueError("A quotation must have at least one article")
        if values.vat_mode == "avec_tva" and (not values.vat_code or values.vat_rate is None):
            raise ValueError("A VAT code and rate are required when VAT applies")
        return values

    @field_validator("vat_code")
    @classmethod
    def strip_vat_code(cls, value):
        return value.strip() if value is not None else None


class QuotationUpdate(BaseModel):
    client_name: Optional[str] = Field(default=None, min_length=1, max_length=250)
    client_email: Optional[EmailStr] = None
    client_address: Optional[str] = Field(default=None, max_length=1000)
    client_reference: Optional[str] = Field(default=None, max_length=100)
    validity_date: Optional[date] = None
    delivery_duration: Optional[str] = Field(default=None, min_length=1, max_length=100)
    incoterm: Optional[str] = Field(default=None, min_length=1, max_length=50)
    special_conditions: Optional[str] = Field(default=None, max_length=4000)
    vat_mode: Optional[Literal["sans_tva", "avec_tva"]] = None
    vat_code: Optional[str] = Field(default=None, min_length=1, max_length=100)
    vat_rate: Optional[Decimal] = Field(default=None, gt=0, le=100, max_digits=5, decimal_places=2)
    payment_method: Optional[str] = Field(default=None, max_length=250)
    payment_terms: Optional[str] = Field(default=None, max_length=500)
    articles: Optional[List[ArticleCreate]] = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("vat_code")
    @classmethod
    def strip_vat_code(cls, value):
        return value.strip() if value is not None else None

    @model_validator(mode="after")
    def validate_vat_fields(self):
        if self.vat_mode == "avec_tva" and (not self.vat_code or self.vat_rate is None):
            raise ValueError("A VAT code and rate are required when VAT applies")
        return self


class QuotationOut(BaseModel):
    id: str
    reference: Optional[str] = None
    client_name: str
    client_email: EmailStr
    client_address: Optional[str]
    client_reference: Optional[str]
    creation_date: date
    validity_date: Optional[date]
    delivery_duration: Optional[str]
    incoterm: Optional[str]
    special_conditions: Optional[str]
    vat_mode: str
    vat_code: Optional[str]
    vat_rate: Optional[Decimal]
    vat_amount: Decimal
    total_including_tax: Decimal
    payment_method: Optional[str]
    payment_terms: Optional[str]
    status: str
    total_amount: Decimal
    purchase_indicator: str
    articles: List[ArticleOut]

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={Decimal: lambda v: float(v)},
    )


class QuotationListItem(BaseModel):
    id: str
    reference: Optional[str] = None
    client_name: str
    creation_date: date
    total_amount: Decimal
    status: str
    purchase_indicator: str

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={Decimal: lambda v: float(v)},
    )


from app.models.quotation import QuotationStatus


class StatusChangeRequest(BaseModel):
    new_status: QuotationStatus

    model_config = ConfigDict(from_attributes=True)
