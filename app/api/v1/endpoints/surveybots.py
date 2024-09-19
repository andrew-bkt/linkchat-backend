# backend/app/api/v1/endpoints/surveybots.py

from fastapi import APIRouter, Depends, HTTPException, Body
from typing import List
from app.schemas.surveybot import SurveyBotCreate, SurveyBot, SurveyBotUpdate, SurveyResult, SurveyResponse
from app.schemas.user import User
from app.api import deps
from app.db.session import get_supabase
from app.services.link_generator import generate_unique_token
from app.services.surveybot_service import SurveyBotService
import uuid
from datetime import datetime
import logging

router = APIRouter()

@router.post("/", response_model=SurveyBot)
async def create_survey_bot(
    survey_bot: SurveyBotCreate,
    current_user: User = Depends(deps.get_current_user)
):
    supabase = get_supabase()
    token = generate_unique_token()

    # Create survey bot
    survey_bot_data = {
        "id": str(uuid.uuid4()),
        "user_id": str(current_user.id),
        "name": survey_bot.name,
        "instructions": survey_bot.instructions,
        "token": token
    }
    survey_bot_response = supabase.table("survey_bots").insert(survey_bot_data).execute()
    created_survey_bot = survey_bot_response.data[0]

    # Create questions
    questions_data = [
        {
            "id": str(uuid.uuid4()),
            "survey_bot_id": created_survey_bot["id"],
            "question_text": q.question_text,
            "question_type": q.question_type,
            "options": q.options,
            "order_number": q.order_number,
            "guidance": q.guidance,
            "answer_criteria": q.answer_criteria
        }
        for q in survey_bot.questions
    ]
    questions_response = supabase.table("survey_questions").insert(questions_data).execute()
    created_questions = questions_response.data

    return SurveyBot(
        id=created_survey_bot["id"],
        user_id=created_survey_bot["user_id"],
        name=created_survey_bot["name"],
        instructions=created_survey_bot["instructions"],
        token=created_survey_bot["token"],
        questions=created_questions,
        created_at=created_survey_bot["created_at"],
        updated_at=created_survey_bot["updated_at"]
    )

@router.get("/", response_model=List[SurveyBot])
async def get_user_survey_bots(current_user: User = Depends(deps.get_current_user)):
    supabase = get_supabase()
    survey_bots_response = supabase.table("survey_bots").select("*").eq("user_id", current_user.id).execute()
    survey_bots = survey_bots_response.data

    for survey_bot in survey_bots:
        questions_response = supabase.table("survey_questions").select("*").eq("survey_bot_id", survey_bot["id"]).execute()
        survey_bot["questions"] = questions_response.data

    return [SurveyBot(**sb) for sb in survey_bots]

@router.get("/{survey_bot_id}", response_model=SurveyBot)
async def get_survey_bot(survey_bot_id: str, current_user: User = Depends(deps.get_current_user)):
    supabase = get_supabase()
    survey_bot_response = supabase.table("survey_bots").select("*").eq("id", survey_bot_id).single().execute()
    
    if not survey_bot_response.data:
        raise HTTPException(status_code=404, detail="Survey bot not found")
    
    survey_bot = survey_bot_response.data
    
    if survey_bot["user_id"] != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to access this survey bot")

    questions_response = supabase.table("survey_questions").select("*").eq("survey_bot_id", survey_bot_id).execute()
    survey_bot["questions"] = questions_response.data

    return SurveyBot(**survey_bot)

@router.put("/{survey_bot_id}", response_model=SurveyBot)
async def update_survey_bot(
    survey_bot_id: str,
    survey_bot_update: SurveyBotUpdate,
    current_user: User = Depends(deps.get_current_user)
):
    supabase = get_supabase()
    
    # Check if the survey bot exists and belongs to the current user
    existing_survey_bot = supabase.table("survey_bots").select("*").eq("id", survey_bot_id).single().execute()
    if not existing_survey_bot.data or existing_survey_bot.data["user_id"] != str(current_user.id):
        raise HTTPException(status_code=404, detail="Survey bot not found or not authorized")

    # Update survey bot
    survey_bot_data = {
        "name": survey_bot_update.name,
        "instructions": survey_bot_update.instructions
    }
    updated_survey_bot = supabase.table("survey_bots").update(survey_bot_data).eq("id", survey_bot_id).execute().data[0]

    # Update questions
    existing_questions = supabase.table("survey_questions").select("id").eq("survey_bot_id", survey_bot_id).execute().data
    existing_question_ids = set(q["id"] for q in existing_questions)

    for question in survey_bot_update.questions:
        if isinstance(question, dict) and "id" in question:
            # Update existing question
            supabase.table("survey_questions").update({
                "question_text": question["question_text"],
                "question_type": question["question_type"],
                "options": question["options"],
                "order_number": question["order_number"],
                "guidance": question.get("guidance", ""),
                "answer_criteria": question.get("answer_criteria", "")
            }).eq("id", question["id"]).execute()
            existing_question_ids.remove(question["id"])
        else:
            # Create new question
            new_question = {
                "id": str(uuid.uuid4()),
                "survey_bot_id": survey_bot_id,
                "question_text": question.question_text,
                "question_type": question.question_type,
                "options": question.options,
                "order_number": question.order_number,
                "guidance": question.guidance,
                "answer_criteria": question.answer_criteria
            }
            supabase.table("survey_questions").insert(new_question).execute()

    # Delete questions that were not included in the update
    for question_id in existing_question_ids:
        supabase.table("survey_questions").delete().eq("id", question_id).execute()

    # Fetch updated questions
    updated_questions = supabase.table("survey_questions").select("*").eq("survey_bot_id", survey_bot_id).execute().data

    return SurveyBot(
        **updated_survey_bot,
        questions=updated_questions
    )

@router.delete("/{survey_bot_id}", status_code=204)
async def delete_survey_bot(survey_bot_id: str, current_user: User = Depends(deps.get_current_user)):
    supabase = get_supabase()
    
    # Check if the survey bot exists and belongs to the current user
    existing_survey_bot = supabase.table("survey_bots").select("*").eq("id", survey_bot_id).single().execute()
    if not existing_survey_bot.data or existing_survey_bot.data["user_id"] != str(current_user.id):
        raise HTTPException(status_code=404, detail="Survey bot not found or not authorized")

    # Delete the survey bot (this will cascade delete related questions, responses, and answers)
    supabase.table("survey_bots").delete().eq("id", survey_bot_id).execute()

@router.get("/{survey_bot_id}/results", response_model=List[SurveyResult])
async def get_survey_results(survey_bot_id: str, current_user: User = Depends(deps.get_current_user)):
    supabase = get_supabase()
    
    # Check if the survey bot exists and belongs to the current user
    existing_survey_bot = supabase.table("survey_bots").select("*").eq("id", survey_bot_id).single().execute()
    if not existing_survey_bot.data or existing_survey_bot.data["user_id"] != str(current_user.id):
        raise HTTPException(status_code=404, detail="Survey bot not found or not authorized")

    # Fetch survey responses
    responses = supabase.table("survey_responses").select("*").eq("survey_bot_id", survey_bot_id).execute().data

    results = []
    for response in responses:
        answers = supabase.table("survey_answers").select("*").eq("survey_response_id", response["id"]).execute().data
        results.append(SurveyResult(response=response, answers=answers))

    return results

@router.get("/token/{token}", response_model=SurveyBot)
async def get_survey_bot_by_token(token: str):
    supabase = get_supabase()
    survey_bot_response = supabase.table("survey_bots").select("*").eq("token", token).single().execute()
    
    if not survey_bot_response.data:
        raise HTTPException(status_code=404, detail="Survey bot not found")
    
    survey_bot = survey_bot_response.data
    
    questions_response = supabase.table("survey_questions").select("*").eq("survey_bot_id", survey_bot["id"]).execute()
    survey_bot["questions"] = questions_response.data

    return SurveyBot(**survey_bot)


@router.post("/{survey_bot_id}/submit", status_code=204)
async def submit_survey(
    survey_bot_id: str,
    survey_response: dict,
    current_user: User = Depends(deps.get_current_user)
):
    supabase = get_supabase()

    # Retrieve the survey bot to ensure it exists and belongs to the user
    survey_bot_response = supabase.table("survey_bots").select("*").eq("id", survey_bot_id).single().execute()
    if not survey_bot_response.data or survey_bot_response.data["user_id"] != str(current_user.id):
        raise HTTPException(status_code=404, detail="Survey bot not found or not authorized")

    # Create the survey response
    survey_response_data = {
        "id": str(uuid.uuid4()),
        "survey_bot_id": survey_bot_id,
        "respondent_id": str(current_user.id),  # Optionally set respondent_id if you want to track who responds
        "completed": True,
        "created_at": datetime.now().isoformat(),  # Use isoformat to serialize datetime
        "updated_at": datetime.now().isoformat(),  # Use isoformat to serialize datetime
    }
    response = supabase.table("survey_responses").insert(survey_response_data).execute()
    created_response_id = response.data[0]["id"]

    # Create the survey answers
    try:
        answers_data = []
        for question_id, answer in survey_response.items():
            try:
                uuid.UUID(question_id)  # Validate that question_id is a valid UUID
            except ValueError:
                logging.error(f"Invalid question_id: {question_id}")
                raise HTTPException(status_code=400, detail=f"Invalid question_id: {question_id}")

            if not isinstance(answer, str):
                logging.error(f"Invalid answer type for question_id {question_id}: {answer}")
                raise HTTPException(status_code=400, detail=f"Invalid answer type for question_id {question_id}: {answer}")

            answers_data.append({
                "id": str(uuid.uuid4()),
                "survey_response_id": created_response_id,
                "question_id": question_id,
                "answer": answer,
                "created_at": datetime.now().isoformat(),  # Use isoformat to serialize datetime
                "updated_at": datetime.now().isoformat(),  # Use isoformat to serialize datetime
            })

        supabase.table("survey_answers").insert(answers_data).execute()
    except Exception as e:
        logging.error(f"Error while creating survey answers: {e}")
        raise HTTPException(status_code=400, detail="Error while creating survey answers")

    return

@router.post("/{survey_bot_id}/chat")
async def chat_with_survey_bot(
    survey_bot_id: str,
    message: dict = Body(...),
):
    try:
        supabase = get_supabase()
        
        # Retrieve the survey bot
        survey_bot_response = supabase.table("survey_bots").select("*").eq("id", survey_bot_id).single().execute()
        if not survey_bot_response.data:
            raise HTTPException(status_code=404, detail="Survey bot not found")

        survey_bot = survey_bot_response.data
        
        # Retrieve the questions for this survey bot
        questions_response = supabase.table("survey_questions").select("*").eq("survey_bot_id", survey_bot_id).execute()
        survey_bot["questions"] = sorted(questions_response.data, key=lambda x: x["order_number"])

        # Create a SurveyBotService instance
        survey_bot_service = SurveyBotService(survey_bot)

        # Process the user's message and get a response
        conversation = message.get("conversation", [])
        response = await survey_bot_service.get_response(message["message"], conversation)

        # Check if the survey is complete
        if survey_bot_service.current_question_index >= len(survey_bot['questions']):
            # Save the survey results
            survey_results = survey_bot_service.get_survey_results()
            
            # Create a new survey response
            survey_response_data = {
                "id": str(uuid.uuid4()),
                "survey_bot_id": survey_bot_id,
                "respondent_id": message.get("respondent_id"),  # You might want to pass this from the frontend
                "completed": True,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
            response = supabase.table("survey_responses").insert(survey_response_data).execute()
            created_response_id = response.data[0]["id"]

            # Save the full conversation
            conversation_data = {
                "survey_response_id": created_response_id,
                "conversation": survey_results['full_conversation'],
            }
            supabase.table("survey_conversations").insert(conversation_data).execute()

            # Save the answers with more detail
            for question in survey_bot['questions']:
                question_id = question['id']
                raw_answer = survey_results['raw_answers'].get(question_id, "")
                interpretation = survey_results['interpreted_answers'].get(question_id, "")
                
                answer_data = {
                    "id": str(uuid.uuid4()),
                    "survey_response_id": created_response_id,
                    "question_id": question_id,
                    "question_text": question['question_text'],
                    "raw_answer": raw_answer,
                    "ai_interpretation": interpretation,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                }
                supabase.table("survey_answers").insert(answer_data).execute()

        response = await survey_bot_service.get_response(message["message"], conversation)

        return {"message": response}
    except Exception as e:
        logging.error(f"Error in chat_with_survey_bot: {e}")
        return {"message": "An error occurred while processing your request"}