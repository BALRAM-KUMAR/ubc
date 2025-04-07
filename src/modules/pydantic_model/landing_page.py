from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class PlanSchema(BaseModel):
    id: int
    name: str
    price: int
    features: Optional[Dict[str, Any]] = None
    recommended: bool = False

    class Config:
        orm_mode = True

class LanguageSchema(BaseModel):
    id: int
    name: str
    request_language: Optional[str] = None
    description: Optional[str] = None

    class Config:
        orm_mode = True

class ComplianceImplementedSchema(BaseModel):
    id: int
    name: str
    details: Dict[str, Any]
    description: Optional[str] = None

    class Config:
        orm_mode = True

class TenantTestimonialsSchema(BaseModel):
    id: int
    tenant_id: int
    feedback: str
    rating: int
    is_approved: bool
    created_at: datetime

    class Config:
        orm_mode = True

class FAQAnswerSchema(BaseModel):
    id: int
    question_id: int
    answer: str
    created_at: datetime

    class Config:
        orm_mode = True

class FAQQuestionSchema(BaseModel):
    id: int
    question: str
    created_at: datetime
    answers: List[FAQAnswerSchema] = []

    class Config:
        orm_mode = True

class FAQCommentSchema(BaseModel):
    id: int
    question_id: Optional[int] = None
    answer_id: Optional[int] = None
    comment: str
    created_at: datetime

    class Config:
        orm_mode = True

class FAQLikeSchema(BaseModel):
    id: int
    question_id: Optional[int] = None
    answer_id: Optional[int] = None
    created_at: datetime

    class Config:
        orm_mode = True