from typing import Generic, List, TypeVar
from pydantic import BaseModel
from pydantic.generics import GenericModel

T = TypeVar("T")


class PaginatedResponse(GenericModel, Generic[T]):
    total: int
    skip: int
    limit: int
    items: List[T]
