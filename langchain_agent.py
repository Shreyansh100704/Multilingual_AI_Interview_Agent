"""
LangChain-based Interview Agent
Handles LLM orchestration, memory management, and prompt execution.
"""

import json
from typing import Dict, List, Any

from langchain.memory import ConversationBufferMemory
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from prompts import (
    RESUME_SUMMARY_PROMPT,
    QUESTION_GENERATION_PROMPT_EN,
    QUESTION_GENERATION_PROMPT_HI,
    EVALUATION_PROMPT_EN_GEMINI,
    EVALUATION_PROMPT_EN_OPENROUTER,
    EVALUATION_PROMPT_HI_GEMINI,
    EVALUATION_PROMPT_HI_OPENROUTER,
    OVERALL_SUMMARY_PROMPT
)


class InterviewAgent:
    """
    Central agent for interview orchestration using LangChain.
    """
    
    def __init__(self, model_id: str, api_keys: Dict[str, str], language: str = "en"):
        """
        Initialize the interview agent with specified model and configuration.
        
        Args:
            model_id: Model identifier
            api_keys: Dictionary containing 'openrouter' and 'gemini' API keys
            language: Interview language ('en' or 'hi')
        """
        self.model_id = model_id
        self.language = language
        self.api_keys = api_keys
        
        # Initialize LLM
        self.llm = self._initialize_llm(model_id, api_keys)
        
        # Initialize conversational memory
        self.memory = ConversationBufferMemory(
            memory_key="history",
            return_messages=False
        )
    
    def _initialize_llm(self, model_id: str, api_keys: Dict[str, str]):
        """
        Factory method for LLM initialization based on provider.
        """
        if 'gemini' in model_id.lower():
            # Map user-friendly names to actual model paths
            model_mapping = {
                'gemini-2.5-flash': 'models/gemini-2.5-flash',
                'gemini-flash-latest': 'models/gemini-flash-latest',
                'gemini-2.5-flash-lite': 'models/gemini-2.5-flash-lite',
                'gemini-2.5-pro': 'models/gemini-2.5-pro',
                'gemini-pro-latest': 'models/gemini-pro-latest'
            }
            
            # Use mapping if available, otherwise use as-is
            actual_model = model_mapping.get(model_id, model_id)
            
            # Add 'models/' prefix if not present
            if not actual_model.startswith('models/'):
                actual_model = f'models/{actual_model}'
            
            return ChatGoogleGenerativeAI(
                model=actual_model,
                google_api_key=api_keys['gemini'],
                temperature=0.7,
                max_output_tokens=2048,
                convert_system_message_to_human=True
            )
        else:
            # OpenRouter / OpenAI-compatible models
            # Use ChatOpenAI with OpenAI-compatible parameter names and set the base URL
            # so it can route requests to OpenRouter. Ensure the correct api key param
            # is passed (`openai_api_key`) and base (`openai_api_base`).
            return ChatOpenAI(
                model_name=model_id,
                openai_api_key=api_keys.get('openrouter'),
                openai_api_base="https://openrouter.ai/api/v1",
                temperature=0.7,
                max_tokens=4096  # Increased to prevent JSON truncation
            )
    
    def _manage_memory_threshold(self):
        """
        FIFO memory management: Delete oldest 5 Q&A pairs when threshold reached.
        Threshold: 20 messages (10 Q&A pairs).
        """
        messages = self.memory.chat_memory.messages
        
        if len(messages) > 20:
            # Remove oldest 10 messages (5 Q&A pairs)
            self.memory.chat_memory.messages = messages[10:]
            print(f"[Memory Manager] Pruned oldest 5 exchanges. Current count: {len(self.memory.chat_memory.messages)}")
    
    def summarize_resume(self, resume_text: str) -> str:
        """
        Generate a concise resume summary using LLM.
        
        Args:
            resume_text: Raw text extracted from PDF
            
        Returns:
            str: 150-word summary of the resume
        """
        prompt = RESUME_SUMMARY_PROMPT.format(resume_text=resume_text)
        
        try:
            response = self.llm.invoke(prompt)
            return response.content.strip()
        except Exception as e:
            print(f"Resume summarization error: {e}")
            raise
    
    def generate_question(self, resume_summary: str, role: str, difficulty: str, history: List[Dict]) -> str:
        """
        Generate next interview question based on context.
        
        Args:
            resume_summary: Candidate's resume summary
            role: Target job role
            difficulty: Current difficulty level (Easy/Medium/Hard)
            history: List of previous Q&A exchanges
            
        Returns:
            str: Generated interview question
        """
        # Check and manage memory threshold
        self._manage_memory_threshold()
        
        # Select prompt based on language
        prompt_template = QUESTION_GENERATION_PROMPT_HI if self.language == 'hi' else QUESTION_GENERATION_PROMPT_EN
        
        # Format conversation history
        history_text = self._format_history(history)
        
        # Get last rating for conditional praise
        last_rating = "N/A"
        if history:
            last_rating = history[-1].get('rating', "N/A")
        
        # Format the prompt with all variables
        prompt = prompt_template.format(
            resume_summary=resume_summary,
            role=role,
            difficulty=difficulty,
            history=history_text,
            last_rating=last_rating
        )
        
        try:
            response = self.llm.invoke(prompt)
            question = response.content.strip()
            
            # Store in memory
            self.memory.chat_memory.add_user_message(f"Generated question: {question}")
            
            return question
        except Exception as e:
            print(f"Question generation error: {e}")
            raise
    
    
    def evaluate_answer(self, question: str, answer: str) -> Dict[str, Any]:
        """
        Evaluate candidate's answer and provide structured feedback.
        
        Args:
            question: The interview question
            answer: Candidate's response
            
        Returns:
            dict: Structured evaluation with rating, strengths, improvements, missing_points
        """
        # Select prompt based on language AND model provider
        is_gemini = 'gemini' in self.model_id.lower()
        
        if self.language == 'hi':
            prompt_template = EVALUATION_PROMPT_HI_GEMINI if is_gemini else EVALUATION_PROMPT_HI_OPENROUTER
        else:
            prompt_template = EVALUATION_PROMPT_EN_GEMINI if is_gemini else EVALUATION_PROMPT_EN_OPENROUTER
        
        # Format the prompt
        prompt = prompt_template.format(question=question, answer=answer)
        
        max_retries = 2
        for attempt in range(max_retries):
            try:
                response = self.llm.invoke(prompt)
                result = response.content.strip()
                
                print(f"Raw LLM response: {result[:300]}...")
                
                # Clean up the response - Remove markdown code blocks
                if '```json' in result:
                    result = result.split('```json')[1].split('```')[0].strip()
                elif '```' in result:
                    result = result.split('```')[1].split('```')[0].strip()
                
                # Handle truncated JSON - if it ends with "... or incomplete string, try to fix it
                if result.endswith('...') or not result.endswith('}'):
                    # Try to close the JSON properly
                    # Count open braces and quotes to determine what's missing
                    open_braces = result.count('{') - result.count('}')
                    
                    # Remove trailing incomplete content
                    if '...' in result:
                        # Find the last complete field before the truncation
                        last_comma = result.rfind(',')
                        last_quote = result.rfind('"', 0, last_comma)
                        if last_quote > 0:
                            result = result[:last_quote + 1]
                    
                    # Close any open strings
                    if result.count('"') % 2 != 0:
                        result += '"'
                    
                    # Close open braces
                    result += '}' * open_braces
                
                # Parse JSON response
                evaluation = json.loads(result)
                
                # Handle missing_points as array or string
                if 'missing_points' in evaluation:
                    if isinstance(evaluation['missing_points'], list):
                        evaluation['missing_points'] = ', '.join(str(item) for item in evaluation['missing_points'])
                    elif not isinstance(evaluation['missing_points'], str):
                        evaluation['missing_points'] = str(evaluation['missing_points'])
                
                # Validate required fields
                required_fields = ['rating', 'strengths', 'improvements']
                for field in required_fields:
                    if field not in evaluation:
                        raise ValueError(f"Missing required field: {field}")
                
                # Add missing_points if not present
                if 'missing_points' not in evaluation:
                    evaluation['missing_points'] = 'N/A'
                
                # Validate and fix rating
                rating = float(evaluation['rating'])
                if rating < 1.0 or rating > 10.0:
                    print(f"Warning: Rating {rating} out of range, clamping to 1-10")
                    rating = max(1.0, min(10.0, rating))
                evaluation['rating'] = round(rating, 2)
                
                # Ensure strings are properly formatted
                evaluation['strengths'] = str(evaluation['strengths']).strip()
                evaluation['improvements'] = str(evaluation['improvements']).strip()
                evaluation['missing_points'] = str(evaluation['missing_points']).strip()
                
                # Store in memory
                self.memory.chat_memory.add_ai_message(f"Answer evaluated: Rating {evaluation['rating']}/10")
                
                print(f"Evaluation successful: Rating {evaluation['rating']}/10")
                return evaluation
                
            except (json.JSONDecodeError, ValueError) as e:
                print(f"Attempt {attempt + 1}/{max_retries} - Parsing error: {e}")
                print(f"Problematic JSON: {result[:500]}...")
                
                if attempt == max_retries - 1:
                    # Last attempt failed - use intelligent fallback
                    print("All parsing attempts failed. Using intelligent fallback.")
                    
                    # Heuristic-based scoring
                    answer_lower = answer.lower().strip()
                    answer_length = len(answer.split())
                    
                    # Check for "don't know" responses
                    dont_know_phrases = ['i dont know', "i don't know", 'idk', 'no idea', 'dont know', 
                                        "don't know", 'not sure', 'no clue']
                    is_dont_know = any(phrase in answer_lower for phrase in dont_know_phrases)
                    
                    if is_dont_know or answer_length < 3:
                        fallback_rating = 1.50
                        fallback_strengths = "Candidate was honest about not knowing"
                        fallback_improvements = "Study the topic and provide a substantive answer"
                    elif answer_length < 10:
                        fallback_rating = 3.00
                        fallback_strengths = "Brief attempt at answering"
                        fallback_improvements = "Provide more detailed explanation with examples"
                    elif answer_length < 30:
                        fallback_rating = 5.00
                        fallback_strengths = "Provided some relevant information"
                        fallback_improvements = "Expand on concepts and add more depth"
                    else:
                        fallback_rating = 6.00
                        fallback_strengths = "Detailed response provided"
                        fallback_improvements = "Structure could be improved for clarity"
                    
                    return {
                        "rating": fallback_rating,
                        "strengths": fallback_strengths,
                        "improvements": fallback_improvements,
                        "missing_points": "Unable to parse detailed feedback from evaluation system"
                    }
            except Exception as e:
                print(f"Unexpected evaluation error: {e}")
                if attempt == max_retries - 1:
                    raise


    
    def generate_overall_summary(self, role: str, history: List[Dict]) -> str:
        """
        Generate comprehensive interview performance summary.
        
        Args:
            role: Target job role
            history: Complete Q&A history with evaluations
            
        Returns:
            str: Overall performance summary
        """
        # Calculate average rating
        avg_rating = sum(q['rating'] for q in history) / len(history)
        
        # Format detailed history
        history_text = ""
        for i, entry in enumerate(history, 1):
            history_text += f"\nQ{i}: {entry['question']}\n"
            history_text += f"A{i}: {entry['answer']}\n"
            history_text += f"Rating: {entry['rating']}/10 | Strengths: {entry['strengths']} | Improvements: {entry['improvements']}\n"
        
        # Format the prompt
        prompt = OVERALL_SUMMARY_PROMPT.format(
            role=role,
            num_questions=len(history),
            avg_rating=round(avg_rating, 2),
            history=history_text
        )
        
        try:
            response = self.llm.invoke(prompt)
            return response.content.strip()
        except Exception as e:
            print(f"Summary generation error: {e}")
            raise
    
    def _format_history(self, history: List[Dict]) -> str:
        """
        Format conversation history for prompt injection.
        """
        if not history:
            return "No previous questions asked yet."
        
        formatted = ""
        for i, entry in enumerate(history, 1):
            formatted += f"Q{i}: {entry['question']}\n"
            formatted += f"A{i}: {entry['answer']} (Rating: {entry['rating']}/10)\n\n"
        
        return formatted.strip()
