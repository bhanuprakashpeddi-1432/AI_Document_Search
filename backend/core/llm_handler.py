import openai
import json
import hashlib
from typing import List, Dict, Any, Optional
import logging
from models.schemas import SourceChunk, SubQuestion
from .config import settings

logger = logging.getLogger(__name__)


class LLMHandler:
    """Handles GPT-4 interactions for query decomposition and answer synthesis"""
    
    def __init__(self):
        """Initialize OpenAI client"""
        try:
            openai.api_key = settings.OPENAI_API_KEY
            self.model = "gpt-4-1106-preview"  # GPT-4 Turbo
            self.max_tokens = settings.MAX_TOKENS
            self.temperature = settings.TEMPERATURE
            
            logger.info("LLM handler initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize LLM handler: {str(e)}")
            raise
    
    def decompose_question(self, question: str, context_hint: str = "") -> List[SubQuestion]:
        """
        Decompose complex questions into atomic sub-questions
        
        Args:
            question: The main question to decompose
            context_hint: Additional context about the document
            
        Returns:
            List[SubQuestion]: List of atomic sub-questions
        """
        try:
            system_prompt = """You are an expert at breaking down complex questions into simpler, atomic sub-questions.
            
Your task is to decompose the given question into 1-5 atomic sub-questions that, when answered together, 
will provide a complete answer to the original question.

Rules:
1. Each sub-question should be self-contained and answerable from document text
2. Sub-questions should be specific and focused
3. Avoid overly complex sub-questions
4. If the original question is already atomic, return it as-is
5. Return your response as a JSON array of objects with 'question' and 'priority' fields

Example:
Original: "What are the eligibility criteria and waiting periods for different types of surgeries?"
Response: [
    {"question": "What are the general eligibility criteria for the policy?", "priority": 1},
    {"question": "What are the waiting periods for different types of surgeries?", "priority": 2},
    {"question": "Are there specific eligibility requirements for surgical procedures?", "priority": 3}
]"""

            user_prompt = f"""Question to decompose: "{question}"
            
{f'Context about the document: {context_hint}' if context_hint else ''}

Please decompose this question into atomic sub-questions."""

            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=800,
                temperature=0.1
            )
            
            content = response.choices[0].message.content.strip()
            
            # Parse JSON response
            try:
                sub_questions_data = json.loads(content)
                sub_questions = [
                    SubQuestion(
                        question=sq["question"],
                        priority=sq.get("priority", 1)
                    ) for sq in sub_questions_data
                ]
                
                logger.info(f"Decomposed question into {len(sub_questions)} sub-questions")
                return sub_questions
                
            except json.JSONDecodeError:
                # Fallback: return original question as single sub-question
                logger.warning("Failed to parse JSON response, using original question")
                return [SubQuestion(question=question, priority=1)]
                
        except Exception as e:
            logger.error(f"Failed to decompose question: {str(e)}")
            # Fallback: return original question
            return [SubQuestion(question=question, priority=1)]
    
    def answer_question_with_context(self, question: str, 
                                   source_chunks: List[SourceChunk]) -> str:
        """
        Answer a question using provided context chunks
        
        Args:
            question: The question to answer
            source_chunks: Relevant context chunks
            
        Returns:
            str: Generated answer
        """
        try:
            if not source_chunks:
                return "I couldn't find relevant information to answer this question."
            
            # Prepare context from source chunks
            context_parts = []
            for i, chunk in enumerate(source_chunks[:5], 1):  # Limit to top 5 chunks
                page_info = f"[Page {chunk.page_number}]" if chunk.page_number else "[Unknown Page]"
                context_parts.append(f"Context {i} {page_info}:\n{chunk.text}\n")
            
            context = "\n".join(context_parts)
            
            system_prompt = """You are an expert document analyst. Your task is to answer questions based ONLY on the provided context.

Rules:
1. Answer ONLY based on the information provided in the context
2. If the context doesn't contain enough information, say so clearly
3. Be concise but comprehensive
4. Quote specific phrases from the context when relevant
5. If you find conflicting information, mention it
6. Do not make assumptions or use external knowledge
7. Always cite which context section your answer comes from when possible"""

            user_prompt = f"""Context:
{context}

Question: {question}

Please provide a clear, accurate answer based on the context provided."""

            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            answer = response.choices[0].message.content.strip()
            logger.info(f"Generated answer for question: {question[:50]}...")
            return answer
            
        except Exception as e:
            logger.error(f"Failed to answer question with context: {str(e)}")
            return "I encountered an error while processing your question. Please try again."
    
    def synthesize_final_answer(self, original_question: str, 
                               sub_answers: List[Dict[str, Any]]) -> str:
        """
        Synthesize final answer from sub-question answers
        
        Args:
            original_question: The original question
            sub_answers: List of sub-question answers with their contexts
            
        Returns:
            str: Synthesized final answer
        """
        try:
            if not sub_answers:
                return "I couldn't find enough information to answer this question."
            
            if len(sub_answers) == 1:
                return sub_answers[0]["answer"]
            
            # Prepare sub-answers for synthesis
            sub_answer_parts = []
            for i, sa in enumerate(sub_answers, 1):
                sub_answer_parts.append(f"Sub-question {i}: {sa['question']}\nAnswer: {sa['answer']}\n")
            
            sub_answers_text = "\n".join(sub_answer_parts)
            
            system_prompt = """You are an expert at synthesizing information from multiple sources into coherent, comprehensive answers.

Your task is to combine the answers to related sub-questions into a single, well-structured answer to the original question.

Rules:
1. Create a coherent, flowing answer that addresses the original question completely
2. Eliminate redundancy while preserving important details
3. Maintain accuracy - don't add information not present in the sub-answers
4. Structure the answer logically
5. If sub-answers conflict, acknowledge the conflict
6. Be comprehensive but concise"""

            user_prompt = f"""Original Question: {original_question}

Sub-question Answers:
{sub_answers_text}

Please synthesize these sub-answers into a comprehensive answer to the original question."""

            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            synthesized_answer = response.choices[0].message.content.strip()
            logger.info(f"Synthesized final answer for: {original_question[:50]}...")
            return synthesized_answer
            
        except Exception as e:
            logger.error(f"Failed to synthesize final answer: {str(e)}")
            # Fallback: combine sub-answers directly
            combined_answer = "\n\n".join([sa["answer"] for sa in sub_answers])
            return combined_answer
    
    def process_question_with_rag(self, question: str, 
                                 source_chunks: List[SourceChunk]) -> Dict[str, Any]:
        """
        Complete question processing pipeline with RAG
        
        Args:
            question: The question to process
            source_chunks: Available source chunks for context
            
        Returns:
            Dict[str, Any]: Processing results with answer and sources used
        """
        try:
            # Step 1: Decompose question
            sub_questions = self.decompose_question(question)
            
            # Step 2: Answer each sub-question
            sub_answers = []
            all_sources_used = []
            
            for sub_q in sorted(sub_questions, key=lambda x: x.priority):
                # For now, use all available chunks for each sub-question
                # In a more sophisticated implementation, you would filter chunks by relevance
                relevant_chunks = source_chunks[:5]  # Use top 5 chunks
                
                if relevant_chunks:
                    answer = self.answer_question_with_context(sub_q.question, relevant_chunks)
                    sub_answers.append({
                        "question": sub_q.question,
                        "answer": answer,
                        "sources": relevant_chunks
                    })
                    all_sources_used.extend(relevant_chunks)
            
            # Step 3: Synthesize final answer
            if len(sub_answers) > 1:
                final_answer = self.synthesize_final_answer(question, sub_answers)
            elif len(sub_answers) == 1:
                final_answer = sub_answers[0]["answer"]
            else:
                final_answer = "I couldn't find relevant information to answer this question."
            
            # Remove duplicate sources
            unique_sources = []
            seen_chunks = set()
            for source in all_sources_used:
                if source.chunk_id not in seen_chunks:
                    unique_sources.append(source)
                    seen_chunks.add(source.chunk_id)
            
            return {
                "answer": final_answer,
                "sources": unique_sources[:10],  # Limit to top 10 sources
                "sub_questions": sub_questions,
                "sub_answers": sub_answers
            }
            
        except Exception as e:
            logger.error(f"Failed to process question with RAG: {str(e)}")
            return {
                "answer": "I encountered an error while processing your question. Please try again.",
                "sources": [],
                "sub_questions": [],
                "sub_answers": []
            }
    
    def generate_query_hash(self, question: str, doc_hash: str) -> str:
        """
        Generate a hash for query caching
        
        Args:
            question: The question
            doc_hash: Document hash
            
        Returns:
            str: Query hash
        """
        query_string = f"{question}_{doc_hash}"
        return hashlib.sha256(query_string.encode()).hexdigest()
    
    def validate_api_connection(self) -> bool:
        """
        Test OpenAI API connection
        
        Returns:
            bool: True if connection is successful
        """
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            logger.info("OpenAI API connection validated successfully")
            return True
            
        except Exception as e:
            logger.error(f"OpenAI API connection failed: {str(e)}")
            return False
