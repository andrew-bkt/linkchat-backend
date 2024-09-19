# backend/app/schemas/surveybot.py

from pydantic import BaseModel, Field
from typing import Optional, List, Union
from datetime import datetime
import uuid

class QuestionBase(BaseModel):
    question_text: str
    question_type: str
    options: Optional[List[str]] = None
    order_number: int
    guidance: Optional[str] = None
    answer_criteria: Optional[str] = None

class QuestionCreate(QuestionBase):
    pass

class Question(QuestionBase):
    id: str

class SurveyBotBase(BaseModel):
    name: str
    instructions: Optional[str] = None

class SurveyBotCreate(SurveyBotBase):
    questions: List[QuestionCreate]

class SurveyBotUpdate(SurveyBotBase):
    questions: List[Union[QuestionCreate, Question]]

class SurveyBot(SurveyBotBase):
    id: str
    user_id: str
    token: str
    questions: List[Question]
    created_at: datetime
    updated_at: datetime

class SurveyResponse(BaseModel):
    id: str
    survey_bot_id: str
    respondent_id: Optional[str]
    completed: bool
    created_at: datetime
    updated_at: datetime

class SurveyAnswer(BaseModel):
    id: str
    survey_response_id: str
    question_id: str
    question_text: str
    raw_answer: str
    ai_interpretation: str
    created_at: datetime
    updated_at: datetime


class SurveyResult(BaseModel):
    response: SurveyResponse
    answers: List[SurveyAnswer]
