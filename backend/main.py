from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
import logging
from typing import List
import asyncio

from models.schemas import QueryRequest, QueryResponse, SourceChunk
from core.config import settings
from core.security import verify_token, SecurityHeaders, validate_api_keys
from core.document_processor import DocumentProcessor
from core.embedding_handler import EmbeddingHandler
from core.vector_db_handler import VectorDBHandler
from core.llm_handler import LLMHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="HackRX Intelligent Query-Retrieval System",
    description="Production-ready API for document analysis and question answering",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # Frontend URLs
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Global handlers - Initialize once
document_processor = None
embedding_handler = None
vector_db_handler = None
llm_handler = None

@app.on_event("startup")
async def startup_event():
    """Initialize application components on startup"""
    global document_processor, embedding_handler, vector_db_handler, llm_handler
    
    try:
        logger.info("Starting HackRX API initialization...")
        
        # Validate API keys
        if not validate_api_keys():
            logger.error("API key validation failed")
            raise Exception("Invalid API configuration")
        
        # Initialize components
        document_processor = DocumentProcessor()
        embedding_handler = EmbeddingHandler()
        vector_db_handler = VectorDBHandler()
        llm_handler = LLMHandler()
        
        # Test connections
        if not llm_handler.validate_api_connection():
            logger.warning("OpenAI API connection test failed")
        
        logger.info("HackRX API initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize API: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down HackRX API...")

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "HackRX Intelligent Query-Retrieval System",
        "version": "1.0.0",
        "status": "active",
        "endpoints": {
            "main": "/hackrx/run",
            "health": "/health",
            "docs": "/docs" if settings.DEBUG else "disabled"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check component status
        components_status = {
            "document_processor": document_processor is not None,
            "embedding_handler": embedding_handler is not None,
            "vector_db_handler": vector_db_handler is not None,
            "llm_handler": llm_handler is not None
        }
        
        all_healthy = all(components_status.values())
        
        return {
            "status": "healthy" if all_healthy else "unhealthy",
            "timestamp": time.time(),
            "components": components_status,
            "settings": {
                "debug": settings.DEBUG,
                "chunk_size": settings.CHUNK_SIZE,
                "top_k_chunks": settings.TOP_K_CHUNKS
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unhealthy"
        )

@app.post("/hackrx/run", response_model=QueryResponse)
async def process_queries(
    request: QueryRequest,
    token: str = Depends(verify_token)
) -> QueryResponse:
    """
    Main endpoint for document processing and question answering
    
    Args:
        request: Query request with document URL and questions
        token: Verified Bearer token
        
    Returns:
        QueryResponse: Answers with source traceability
    """
    start_time = time.time()
    
    try:
        logger.info(f"Processing request with {len(request.questions)} questions")
        
        # Validate request
        if not request.documents or not request.questions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Both documents URL and questions are required"
            )
        
        if len(request.questions) > 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 10 questions allowed per request"
            )
        
        # Generate document hash
        doc_hash = document_processor.get_document_hash(request.documents)
        
        # Check if document is already processed
        if not vector_db_handler.check_if_doc_processed(doc_hash):
            logger.info("Document not in cache, processing...")
            
            # Process document
            chunks = await document_processor.process_document(request.documents)
            
            if not chunks:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to process document or document is empty"
                )
            
            # Generate embeddings
            chunk_texts = [chunk.text for chunk in chunks]
            embeddings = embedding_handler.generate_dense_embeddings(chunk_texts)
            
            # Store in vector database
            vector_db_handler.store_vectors(chunks, embeddings.tolist(), doc_hash)
            
            # Mark document as processed
            vector_db_handler.mark_doc_as_processed(
                doc_hash, 
                request.documents, 
                len(chunks),
                {"processing_time": time.time() - start_time}
            )
            
            logger.info(f"Document processed and cached with {len(chunks)} chunks")
        else:
            logger.info("Document found in cache, skipping processing")
        
        # Process questions
        answers = []
        all_sources = []
        
        for question in request.questions:
            try:
                # Generate query hash for caching
                query_hash = llm_handler.generate_query_hash(question, doc_hash)
                
                # Check query cache
                cached_result = vector_db_handler.get_cached_query_result(query_hash, doc_hash)
                
                if cached_result:
                    logger.info(f"Using cached result for question: {question[:50]}...")
                    answers.append(cached_result["answer"])
                    
                    # Convert cached sources to SourceChunk objects
                    cached_sources = [
                        SourceChunk(**source) for source in cached_result["sources"]
                    ]
                    all_sources.append(cached_sources)
                else:
                    # Generate fresh answer
                    logger.info(f"Generating new answer for: {question[:50]}...")
                    
                    # Generate query embedding
                    query_embedding = embedding_handler.generate_dense_embeddings([question])[0]
                    
                    # Retrieve relevant chunks from vector DB
                    relevant_chunks = vector_db_handler.query_vectors(
                        query_embedding.tolist(),
                        doc_hash,
                        top_k=settings.TOP_K_CHUNKS,
                        score_threshold=settings.SIMILARITY_THRESHOLD
                    )
                    
                    if not relevant_chunks:
                        # Fallback: try with lower threshold
                        relevant_chunks = vector_db_handler.query_vectors(
                            query_embedding.tolist(),
                            doc_hash,
                            top_k=settings.TOP_K_CHUNKS,
                            score_threshold=0.5
                        )
                    
                    # Process with LLM
                    if relevant_chunks:
                        result = llm_handler.process_question_with_rag(question, relevant_chunks)
                        answer = result["answer"]
                        sources = result["sources"]
                    else:
                        answer = "I couldn't find relevant information in the document to answer this question."
                        sources = []
                    
                    answers.append(answer)
                    all_sources.append(sources)
                    
                    # Cache the result
                    vector_db_handler.cache_query_result(
                        query_hash, doc_hash, question, answer, sources
                    )
                
            except Exception as e:
                logger.error(f"Failed to process question '{question}': {str(e)}")
                answers.append("I encountered an error while processing this question. Please try again.")
                all_sources.append([])
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Create response
        response = QueryResponse(
            answers=answers,
            sources=all_sources,
            processing_time=processing_time,
            document_hash=doc_hash
        )
        
        logger.info(f"Request completed in {processing_time:.2f} seconds")
        
        # Add security headers
        headers = SecurityHeaders.get_security_headers()
        return JSONResponse(
            content=response.dict(),
            headers=headers
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in process_queries: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred while processing your request"
        )

@app.get("/stats")
async def get_stats(token: str = Depends(verify_token)):
    """Get system statistics (protected endpoint)"""
    try:
        return {
            "vector_db_stats": vector_db_handler.get_index_stats(),
            "embedding_info": embedding_handler.get_embeddings_info(),
            "settings": {
                "chunk_size": settings.CHUNK_SIZE,
                "chunk_overlap": settings.CHUNK_OVERLAP,
                "top_k_chunks": settings.TOP_K_CHUNKS,
                "similarity_threshold": settings.SIMILARITY_THRESHOLD
            }
        }
    except Exception as e:
        logger.error(f"Failed to get stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system statistics"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info" if not settings.DEBUG else "debug"
    )
