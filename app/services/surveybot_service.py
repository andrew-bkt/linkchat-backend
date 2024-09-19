# backend/app/services/surveybot_service.py

from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain.memory import ConversationBufferMemory
from langgraph.graph import StateGraph, END
from typing import Dict, TypedDict, List
from app.core.config import settings
import logging

class SurveyState(TypedDict):
    messages: List[dict]
    current_question_index: int
    answers: Dict[str, str]
    survey_complete: bool

class SurveyBotService:
    def __init__(self, survey_bot):
        self.survey_bot = survey_bot
        self.chat_model = ChatOpenAI(temperature=0.7, openai_api_key=settings.OPENAI_API_KEY)
        self.memory = ConversationBufferMemory(return_messages=True)
        self.workflow = self._create_workflow()
        self.current_question_index = 0
        self.full_conversation = []
        self.interpreted_answers = {}

    def _format_questions(self):
        return "\n".join([f"{q['order_number']}. {q['question_text']} (Type: {q['question_type']})" for q in self.survey_bot['questions']])

    def _create_workflow(self):
        system_message = f"""You are a survey bot named {self.survey_bot['name']}. 
        Your task is to conduct a survey based on the following instructions:
        {self.survey_bot['instructions']}

        You have access to the following questions:
        {self._format_questions()}

        Conduct the survey in a conversational manner, asking one question at a time.
        Do not reveal all questions at once. Wait for the user's response before moving to the next question.
        After each user response, you should:
        1. Acknowledge their answer.
        2. Ask the next question in the survey.
        3. If it's the last question, thank the user for completing the survey.
        """

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("human", "{user_input}"),
            ("ai", "{agent_scratchpad}"),
        ])

        workflow = StateGraph(SurveyState)
        workflow.add_node("survey_agent", self.survey_agent)
        workflow.set_entry_point("survey_agent")
        workflow.add_conditional_edges(
            "survey_agent",
            lambda x: "survey_agent" if not x.get("survey_complete", False) else END
        )

        return workflow.compile()

    def survey_agent(self, state: SurveyState) -> SurveyState:
        try:
            logging.debug(f"survey_agent received state: {state}")
            messages = state['messages']
            current_question_index = state['current_question_index']
            answers = state['answers']

            human_message = messages[-1]['content'] if messages else ""
            
            if current_question_index > 0 and human_message:
                current_question = self.survey_bot['questions'][current_question_index - 1]
                answers[current_question['id']] = human_message

            if current_question_index < len(self.survey_bot['questions']):
                next_question = self.survey_bot['questions'][current_question_index]
                survey_complete = False
                agent_scratchpad = f"Acknowledge their previous answer if any, then ask this question: {next_question['question_text']}"
            else:
                next_question = None
                survey_complete = True
                agent_scratchpad = "This was the last question. Thank the user for completing the survey."

            full_conversation = "\n".join([f"{'Human' if msg['role'] == 'human' else 'AI'}: {msg['content']}" for msg in messages])
            
            logging.debug(f"Prompt to OpenAI:\n{self.prompt.format_messages(user_input=full_conversation, agent_scratchpad=agent_scratchpad)}")

            response = self.chat_model(self.prompt.format_messages(
                user_input=full_conversation,
                agent_scratchpad=agent_scratchpad
            ))
            logging.debug(f"OpenAI response: {response}")

            # Store AI's interpretation of the answer
            if current_question_index > 0:
                current_question = self.survey_bot['questions'][current_question_index - 1]
                self.interpreted_answers[current_question['id']] = f"Question: {current_question['question_text']}\nAnswer: {human_message}\nInterpretation: {agent_scratchpad}"

            new_state = {
                'messages': messages + [{'role': 'assistant', 'content': response.content}],
                'current_question_index': current_question_index + 1,
                'answers': answers,
                'survey_complete': survey_complete
            }

            logging.debug(f"New state in survey_agent: {new_state}")

            # Store the full conversation
            self.full_conversation.append({'role': 'human', 'content': human_message})
            self.full_conversation.append({'role': 'assistant', 'content': response.content})

            return new_state
        except Exception as e:
            logging.error(f"Exception in survey_agent: {e}")
            return {
                'messages': state['messages'] + [{'role': 'assistant', 'content': "I'm sorry, but I encountered an error."}],
                'current_question_index': state['current_question_index'],
                'answers': state['answers'],
                'survey_complete': True  # End the survey due to the error
            }


    async def get_response(self, user_message: str, conversation: List[dict]) -> str:
        try:
            logging.debug(f"get_response called with user_message: '{user_message}' and conversation: {conversation}")

            if not conversation:
                # If this is the first interaction, generate an initial greeting
                initial_prompt = ChatPromptTemplate.from_messages([
                    ("system", f"""You are a survey bot named {self.survey_bot['name']}. 
                    Create an initial greeting for a survey based on these instructions:
                    {self.survey_bot['instructions']}

                    The survey includes these questions:
                    {self._format_questions()}

                    Your greeting should:
                    1. Introduce the survey topic
                    2. Ask for the user's name
                    3. Be concise and welcoming
                    
                    Do not ask any survey questions yet."""),
                    ("human", "Generate the initial greeting for the survey."),
                ])
                initial_response = self.chat_model(initial_prompt.format_messages())
                self.memory.chat_memory.add_ai_message(initial_response.content)
                return initial_response.content

            # Update memory with the full conversation
            self.memory.chat_memory.clear()
            for message in conversation:
                if message['role'] == 'user':
                    self.memory.chat_memory.add_user_message(message['content'])
                else:
                    self.memory.chat_memory.add_ai_message(message['content'])

            # Add the latest user message to memory
            self.memory.chat_memory.add_user_message(user_message)

            # Create the current state based on memory
            ai_messages = [msg for msg in self.memory.chat_memory.messages if isinstance(msg, AIMessage)]
            current_question_index = len(ai_messages)

            state = {
                'messages': [{'role': 'human' if isinstance(msg, HumanMessage) else 'assistant', 'content': msg.content} 
                             for msg in self.memory.chat_memory.messages],
                'current_question_index': current_question_index,
                'answers': {},
                'survey_complete': False
            }

            logging.debug(f"Initial state before workflow: {state}")

            # Process the state through the workflow
            if self.workflow is None:
                logging.error("Workflow is None, unable to process state")
                return "I apologize, but I encountered an error while processing your response."

            final_state = next(self.workflow.stream(state))
            logging.debug(f"State after workflow step: {final_state}")

            # Extract state data
            if isinstance(final_state, dict) and 'survey_agent' in final_state:
                state_data = final_state['survey_agent']
            elif isinstance(final_state, dict):
                state_data = final_state
            else:
                raise Exception(f"Unexpected final state type: {type(final_state)}")

            logging.debug(f"Extracted state data: {state_data}")

            # Update memory and state after workflow processing
            self.memory.chat_memory.add_ai_message(state_data["messages"][-1]['content'])
            self.current_question_index = state_data["current_question_index"]

            # Return the most recent AI message
            return state_data["messages"][-1]['content']


        except Exception as e:
            logging.error(f"Error in SurveyBotService: {e}")
            return "I apologize, but I encountered an error while processing your response."

    def get_survey_results(self):
        raw_answers = {}
        for i, message in enumerate(self.memory.chat_memory.messages):
            if isinstance(message, HumanMessage) and i < len(self.survey_bot['questions']):
                question_id = self.survey_bot['questions'][i]['id']
                raw_answers[question_id] = message.content

        return {
            'full_conversation': self.full_conversation,
            'interpreted_answers': self.interpreted_answers,
            'raw_answers': raw_answers
        }

    def reset_survey(self):
        self.memory.clear()
        self.current_question_index = 0