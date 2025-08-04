import pinecone
import json
from typing import List, Optional, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import logging
from datetime import datetime
from models.schemas import DocumentChunk, SourceChunk
from .config import settings

logger = logging.getLogger(__name__)


class VectorDBHandler:
    """Handles Pinecone vector operations and PostgreSQL caching"""
    
    def __init__(self):
        """Initialize Pinecone and PostgreSQL connections"""
        try:
            # Initialize Pinecone
            pinecone.init(
                api_key=settings.PINECONE_API_KEY,
                environment=settings.PINECONE_ENV
            )
            
            # Connect to Pinecone index
            if settings.PINECONE_INDEX not in pinecone.list_indexes():
                # Create index if it doesn't exist
                pinecone.create_index(
                    name=settings.PINECONE_INDEX,
                    dimension=384,  # Default for all-MiniLM-L6-v2
                    metric="cosine"
                )
                logger.info(f"Created Pinecone index: {settings.PINECONE_INDEX}")
            
            self.index = pinecone.Index(settings.PINECONE_INDEX)
            
            # Initialize PostgreSQL connection
            self.engine = create_engine(settings.POSTGRES_URL)
            self._create_tables()
            
            logger.info("Vector DB handler initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Vector DB handler: {str(e)}")
            raise
    
    def _create_tables(self):
        """Create necessary PostgreSQL tables"""
        try:
            with self.engine.connect() as conn:
                # Create document_cache table
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS document_cache (
                        id SERIAL PRIMARY KEY,
                        document_hash VARCHAR(64) UNIQUE NOT NULL,
                        document_url TEXT NOT NULL,
                        processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        chunk_count INTEGER,
                        metadata JSONB
                    )
                """))
                
                # Create query_cache table for caching results
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS query_cache (
                        id SERIAL PRIMARY KEY,
                        query_hash VARCHAR(64) UNIQUE NOT NULL,
                        document_hash VARCHAR(64) NOT NULL,
                        query TEXT NOT NULL,
                        answer TEXT,
                        sources JSONB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (document_hash) REFERENCES document_cache(document_hash)
                    )
                """))
                
                conn.commit()
                logger.info("Database tables created/verified successfully")
                
        except SQLAlchemyError as e:
            logger.error(f"Failed to create database tables: {str(e)}")
            raise
    
    def check_if_doc_processed(self, doc_hash: str) -> bool:
        """
        Check if document has already been processed
        
        Args:
            doc_hash: Document hash
            
        Returns:
            bool: True if document is already processed
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("SELECT COUNT(*) as count FROM document_cache WHERE document_hash = :hash"),
                    {"hash": doc_hash}
                )
                count = result.fetchone()["count"]
                return count > 0
                
        except SQLAlchemyError as e:
            logger.error(f"Failed to check document processing status: {str(e)}")
            return False
    
    def mark_doc_as_processed(self, doc_hash: str, doc_url: str, 
                             chunk_count: int, metadata: Optional[Dict] = None) -> bool:
        """
        Mark document as processed in the cache
        
        Args:
            doc_hash: Document hash
            doc_url: Document URL
            chunk_count: Number of chunks processed
            metadata: Additional metadata
            
        Returns:
            bool: True if successfully marked
        """
        try:
            with self.engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO document_cache (document_hash, document_url, chunk_count, metadata)
                    VALUES (:hash, :url, :count, :metadata)
                    ON CONFLICT (document_hash) DO UPDATE SET
                        processed_at = CURRENT_TIMESTAMP,
                        chunk_count = :count,
                        metadata = :metadata
                """), {
                    "hash": doc_hash,
                    "url": doc_url,
                    "count": chunk_count,
                    "metadata": json.dumps(metadata) if metadata else None
                })
                conn.commit()
                logger.info(f"Marked document as processed: {doc_hash}")
                return True
                
        except SQLAlchemyError as e:
            logger.error(f"Failed to mark document as processed: {str(e)}")
            return False
    
    def store_vectors(self, chunks: List[DocumentChunk], embeddings: List[List[float]], 
                     doc_hash: str) -> bool:
        """
        Store vectors in Pinecone
        
        Args:
            chunks: List of document chunks
            embeddings: List of embedding vectors
            doc_hash: Document hash for namespacing
            
        Returns:
            bool: True if successfully stored
        """
        try:
            # Prepare vectors for upsert
            vectors = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                vector_id = f"{doc_hash}_{chunk.id}"
                metadata = {
                    "chunk_id": chunk.id,
                    "text": chunk.text[:1000],  # Limit text length for metadata
                    "page_number": chunk.page_number,
                    "chunk_type": chunk.chunk_type,
                    "document_hash": doc_hash
                }
                
                vectors.append({
                    "id": vector_id,
                    "values": embedding,
                    "metadata": metadata
                })
            
            # Upsert vectors in batches
            batch_size = 100
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i + batch_size]
                self.index.upsert(vectors=batch)
            
            logger.info(f"Stored {len(vectors)} vectors in Pinecone for document {doc_hash}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store vectors: {str(e)}")
            return False
    
    def query_vectors(self, query_embedding: List[float], doc_hash: str, 
                     top_k: int = 10, score_threshold: float = 0.7) -> List[SourceChunk]:
        """
        Query vectors from Pinecone
        
        Args:
            query_embedding: Query embedding vector
            doc_hash: Document hash for filtering
            top_k: Number of top results to return
            score_threshold: Minimum similarity score threshold
            
        Returns:
            List[SourceChunk]: List of relevant chunks
        """
        try:
            # Query Pinecone with filter for document hash
            results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True,
                filter={"document_hash": doc_hash}
            )
            
            # Convert results to SourceChunk objects
            source_chunks = []
            for match in results.matches:
                if match.score >= score_threshold:
                    metadata = match.metadata
                    source_chunk = SourceChunk(
                        text=metadata.get("text", ""),
                        chunk_id=metadata.get("chunk_id"),
                        page_number=metadata.get("page_number"),
                        score=float(match.score)
                    )
                    source_chunks.append(source_chunk)
            
            logger.info(f"Retrieved {len(source_chunks)} chunks from Pinecone for document {doc_hash}")
            return source_chunks
            
        except Exception as e:
            logger.error(f"Failed to query vectors: {str(e)}")
            return []
    
    def get_cached_query_result(self, query_hash: str, doc_hash: str) -> Optional[Dict[str, Any]]:
        """
        Get cached query result from PostgreSQL
        
        Args:
            query_hash: Hash of the query
            doc_hash: Document hash
            
        Returns:
            Optional[Dict]: Cached result if found
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT answer, sources, created_at 
                    FROM query_cache 
                    WHERE query_hash = :query_hash AND document_hash = :doc_hash
                """), {"query_hash": query_hash, "doc_hash": doc_hash})
                
                row = result.fetchone()
                if row:
                    return {
                        "answer": row["answer"],
                        "sources": json.loads(row["sources"]) if row["sources"] else [],
                        "created_at": row["created_at"]
                    }
                return None
                
        except SQLAlchemyError as e:
            logger.error(f"Failed to get cached query result: {str(e)}")
            return None
    
    def cache_query_result(self, query_hash: str, doc_hash: str, query: str, 
                          answer: str, sources: List[SourceChunk]) -> bool:
        """
        Cache query result in PostgreSQL
        
        Args:
            query_hash: Hash of the query
            doc_hash: Document hash
            query: Original query text
            answer: Generated answer
            sources: Source chunks used
            
        Returns:
            bool: True if successfully cached
        """
        try:
            # Convert sources to dict for JSON storage
            sources_dict = [source.dict() for source in sources]
            
            with self.engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO query_cache (query_hash, document_hash, query, answer, sources)
                    VALUES (:query_hash, :doc_hash, :query, :answer, :sources)
                    ON CONFLICT (query_hash) DO UPDATE SET
                        answer = :answer,
                        sources = :sources,
                        created_at = CURRENT_TIMESTAMP
                """), {
                    "query_hash": query_hash,
                    "doc_hash": doc_hash,
                    "query": query,
                    "answer": answer,
                    "sources": json.dumps(sources_dict)
                })
                conn.commit()
                
            logger.info(f"Cached query result for hash: {query_hash}")
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to cache query result: {str(e)}")
            return False
    
    def delete_document_vectors(self, doc_hash: str) -> bool:
        """
        Delete all vectors for a document from Pinecone
        
        Args:
            doc_hash: Document hash
            
        Returns:
            bool: True if successfully deleted
        """
        try:
            # Delete vectors with matching document_hash filter
            self.index.delete(filter={"document_hash": doc_hash})
            
            # Remove from PostgreSQL cache
            with self.engine.connect() as conn:
                conn.execute(
                    text("DELETE FROM document_cache WHERE document_hash = :hash"),
                    {"hash": doc_hash}
                )
                conn.commit()
            
            logger.info(f"Deleted vectors and cache for document: {doc_hash}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete document vectors: {str(e)}")
            return False
    
    def get_index_stats(self) -> Dict[str, Any]:
        """
        Get Pinecone index statistics
        
        Returns:
            Dict[str, Any]: Index statistics
        """
        try:
            stats = self.index.describe_index_stats()
            return {
                "total_vector_count": stats.total_vector_count,
                "dimension": stats.dimension,
                "index_fullness": stats.index_fullness,
                "namespaces": stats.namespaces
            }
        except Exception as e:
            logger.error(f"Failed to get index stats: {str(e)}")
            return {}
