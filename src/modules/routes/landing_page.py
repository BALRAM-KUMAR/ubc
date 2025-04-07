from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from core.dependencies import get_db
from core.models.public import Language, ComplianceImplemented, TenantTestimonials, FAQAnswer, FAQQuestion, FAQLike, FAQComment, Plan
from modules.pydantic_model.landing_page  import (PlanSchema, LanguageSchema, ComplianceImplementedSchema,
                     TenantTestimonialsSchema, FAQQuestionSchema, FAQAnswerSchema,
                     FAQCommentSchema, FAQLikeSchema)

router = APIRouter(
    prefix="/landing",
    tags=["LandingPage"],
)

# Plans
@router.get("/plans", response_model=list[PlanSchema])
async def get_plans(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Plan))
    return result.scalars().all()

# Languages
@router.get("/languages", response_model=list[LanguageSchema])
async def get_languages(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Language))
    return result.scalars().all()

# Compliances
@router.get("/compliances", response_model=list[ComplianceImplementedSchema])
async def get_compliances(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ComplianceImplemented))
    return result.scalars().all()

# Testimonials
@router.get("/testimonials", response_model=list[TenantTestimonialsSchema])
async def get_testimonials(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TenantTestimonials)
        .where(TenantTestimonials.is_approved == True)
        .order_by(TenantTestimonials.created_at.desc())
    )
    return result.scalars().all()

# FAQ Questions with nested relationships
@router.get("/faq-questions", response_model=list[FAQQuestionSchema])
async def get_faq_questions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(FAQQuestion)
        .options(selectinload(FAQQuestion.answers))
    )
    return result.scalars().all()

# FAQ Answers
@router.get("/faq-answers", response_model=list[FAQAnswerSchema])
async def get_faq_answers(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(FAQAnswer))
    return result.scalars().all()

# FAQ Comments
@router.get("/faq-comments", response_model=list[FAQCommentSchema])
async def get_faq_comments(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(FAQComment))
    return result.scalars().all()

# FAQ Likes
@router.get("/faq-likes", response_model=list[FAQLikeSchema])
async def get_faq_likes(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(FAQLike))
    return result.scalars().all()