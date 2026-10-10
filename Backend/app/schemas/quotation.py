"""Décrit les données échangées pour les cotations."""

from decimal import Decimal
from datetime import date
from typing import List, Optional
from pydantic import BaseModel, EmailStr, ConfigDict, Field, model_validator
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
    articles: List[ArticleCreate]

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def validate_articles(cls, values):
        if not values.articles:
            raise ValueError("A quotation must have at least one article")
        return values


class QuotationUpdate(BaseModel):
    client_name: Optional[str] = Field(default=None, min_length=1, max_length=250)
    client_email: Optional[EmailStr] = None
    client_address: Optional[str] = Field(default=None, max_length=1000)
    client_reference: Optional[str] = Field(default=None, max_length=100)
    validity_date: Optional[date] = None
    delivery_duration: Optional[str] = Field(default=None, min_length=1, max_length=100)
    incoterm: Optional[str] = Field(default=None, min_length=1, max_length=50)
    special_conditions: Optional[str] = Field(default=None, max_length=4000)
    articles: Optional[List[ArticleCreate]] = None

    model_config = ConfigDict(from_attributes=True)


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
