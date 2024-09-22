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
    """
    Represents the state of the survey.

    Attributes:
        messages (List[dict]): List of conversation messages.
        current_question_index (int): Index of the current question.
        answers (Dict[str, str]): Dictionary of answers keyed by question ID.
        survey_complete (bool): Flag indicating if the survey is complete.
    """
    messages: List[dict]
    current_question_index: int
    answers: Dict[str, str]
    survey_complete: bool

class SurveyBotService:
    """
    Service class for managing the survey bot functionality.
    """

    def __init__(self, survey_bot):
        """
        Initialize the SurveyBotService.

        Args:
            survey_bot: The survey bot configuration.
        """
        self.survey_bot = survey_bot
        self.chat_model = ChatOpenAI(temperature=0.7, openai_api_key=settings.OPENAI_API_KEY)
        self.memory = ConversationBufferMemory(return_messages=True)
        self.workflow = self._create_workflow()
        self.current_question_index = 0
        self.full_conversation = []
        self.interpreted_answers = {}

    def _format_questions(self):
        """
        Format the survey questions into a string.

        Returns:
            str: Formatted string of survey questions.
        """
        return "\n".join([f"{q['order_number']}. {q['question_text']} (Type: {q['question_type']})" for q in self.survey_bot['questions']])


    def _create_workflow(self):
        """
        Create the survey workflow.

        Returns:
            StateGraph: Compiled workflow graph.
        """
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
            messages = state.get('messages', [])
            current_question_index = state.get('current_question_index', 0)
            answers = state.get('answers', {})

            human_message = messages[-1]['content'] if messages else ""
            logging.debug(f"Human message: {human_message}")

            validation_instructions = ""
            move_to_next_question = True

            if current_question_index > 0 and human_message:
                current_question = self.survey_bot['questions'][current_question_index - 1]
                logging.debug(f"Current question: {current_question}")
                
                if current_question.get('answer_criteria'):
                    answer_criteria = current_question['answer_criteria']
                    logging.debug(f"Answer criteria: {answer_criteria}")
                    validation_instructions = f"""
                        Check if the user's answer meets the following criteria: {answer_criteria}.
                        If it does not, politely ask the user to provide more details according to the criteria.
                        If it does meet the criteria, acknowledge the answer and proceed to the next question.
                        """
                    move_to_next_question = False  # We'll decide this based on the AI's response
                else:
                    answers[current_question['id']] = human_message
                    logging.debug(f"No criteria, added answer: {human_message}")

            if current_question_index < len(self.survey_bot['questions']):
                next_question = self.survey_bot['questions'][current_question_index]
                survey_complete = False
                logging.debug(f"Next question: {next_question}")

                agent_scratchpad = f"""
                    Acknowledge their previous answer if any.
                    {validation_instructions}
                    If the previous answer meets the criteria or there were no criteria, ask this question: {next_question['question_text']}
                    """
            else:
                next_question = None
                survey_complete = True
                agent_scratchpad = "This was the last question. Thank the user for completing the survey."
                logging.debug("Survey complete")

            full_conversation = "\n".join([f"{'Human' if msg['role'] == 'human' else 'AI'}: {msg['content']}" for msg in messages])
            logging.debug(f"Full conversation: {full_conversation}")

            logging.debug(f"Prompt to OpenAI:\n{self.prompt.format_messages(user_input=full_conversation, agent_scratchpad=agent_scratchpad)}")

            response = self.chat_model(self.prompt.format_messages(
                user_input=full_conversation,
                agent_scratchpad=agent_scratchpad
            ))
            logging.debug(f"OpenAI response: {response}")

            if current_question_index > 0:
                current_question = self.survey_bot['questions'][current_question_index - 1]
                self.interpreted_answers[current_question['id']] = f"Question: {current_question['question_text']}\nAnswer: {human_message}\nInterpretation: {agent_scratchpad}"

            # Check if the response indicates that more details are needed
            if "provide more details" in response.content.lower() or "could you please" in response.content.lower():
                move_to_next_question = False
                logging.debug("AI requested more details")
            elif move_to_next_question:
                current_question_index += 1
                if current_question_index > 0:
                    answers[self.survey_bot['questions'][current_question_index - 1]['id']] = human_message
                logging.debug(f"Moving to next question. New index: {current_question_index}")

            new_state = {
                'messages': messages + [{'role': 'assistant', 'content': response.content}],
                'current_question_index': current_question_index,
                'answers': answers,
                'survey_complete': survey_complete
            }

            logging.debug(f"New state in survey_agent: {new_state}")

            self.full_conversation.append({'role': 'human', 'content': human_message})
            self.full_conversation.append({'role': 'assistant', 'content': response.content})

            return new_state
        except Exception as e:
            logging.error(f"Exception in survey_agent: {e}", exc_info=True)
            return {
                'messages': state.get('messages', []) + [{'role': 'assistant', 'content': "I'm sorry, but I encountered an error."}],
                'current_question_index': state.get('current_question_index', 0),
                'answers': state.get('answers', {}),
                'survey_complete': True  # End the survey due to the error
            }



    async def get_response(self, user_message: str, conversation: List[dict]) -> str:
        """
        Get the next response from the survey bot.

        Args:
            user_message (str): The user's message.
            conversation (List[dict]): The conversation history.

        Returns:
            str: The survey bot's response.
        """
        try:
            logging.debug(f"get_response called with user_message: '{user_message}' and conversation: {conversation}")

            if not conversation:
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

            self.memory.chat_memory.clear()
            for message in conversation:
                if message['role'] == 'user':
                    self.memory.chat_memory.add_user_message(message['content'])
                else:
                    self.memory.chat_memory.add_ai_message(message['content'])

            self.memory.chat_memory.add_user_message(user_message)

            messages = self.memory.chat_memory.messages

            answers = {}
            ai_message_indices = [i for i, msg in enumerate(messages) if isinstance(msg, AIMessage)]
            human_message_indices = [i for i, msg in enumerate(messages) if isinstance(msg, HumanMessage)]

            question_ai_indices = ai_message_indices[1:] if len(ai_message_indices) > 0 else []
            current_question_index = len(question_ai_indices)

            for idx, ai_idx in enumerate(question_ai_indices):
                human_idx = ai_idx + 1
                if human_idx < len(messages) and isinstance(messages[human_idx], HumanMessage):
                    question = self.survey_bot['questions'][idx]
                    answers[question['id']] = messages[human_idx].content

            state = {
                'messages': [{'role': 'human' if isinstance(msg, HumanMessage) else 'assistant', 'content': msg.content}
                            for msg in self.memory.chat_memory.messages],
                'current_question_index': current_question_index,
                'answers': answers,
                'survey_complete': False
            }

            logging.debug(f"Initial state before workflow: {state}")

            if self.workflow is None:
                logging.error("Workflow is None, unable to process state")
                return "I apologize, but I encountered an error while processing your response."

            final_state = next(self.workflow.stream(state))
            logging.debug(f"State after workflow step: {final_state}")

            state_data = final_state.get('survey_agent', {})

            logging.debug(f"Extracted state data: {state_data}")

            if isinstance(state_data, dict) and "messages" in state_data and state_data["messages"]:
                latest_message = state_data["messages"][-1]
                self.memory.chat_memory.add_ai_message(latest_message['content'])
                self.current_question_index = state_data.get("current_question_index", self.current_question_index)
                return latest_message['content']
            else:
                logging.error(f"Invalid state data: {state_data}")
                return "I apologize, but I encountered an error while processing your response."

        except Exception as e:
            logging.error(f"Error in SurveyBotService: {e}", exc_info=True)
            return "I apologize, but I encountered an error while processing your response."

    def get_survey_results(self):
        """
        Get the results of the survey.

        Returns:
            dict: A dictionary containing the full conversation, interpreted answers, and raw answers.
        """
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
        """
        Reset the survey to its initial state.
        """
        self.memory.clear()
        self.current_question_index = 0
