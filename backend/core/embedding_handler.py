import numpy as np
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import logging
from models.schemas import DocumentChunk, SourceChunk

logger = logging.getLogger(__name__)


class EmbeddingHandler:
    """Handles dense and sparse embeddings for hybrid search"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the embedding handler
        
        Args:
            model_name: Name of the sentence transformer model
        """
        try:
            self.dense_model = SentenceTransformer(model_name)
            self.tfidf_vectorizer = TfidfVectorizer(
                max_features=5000,
                stop_words='english',
                ngram_range=(1, 2),
                min_df=1,
                max_df=0.95
            )
            self.tfidf_fitted = False
            self.document_texts = []
            self.tfidf_matrix = None
            
            logger.info(f"Initialized embedding handler with model: {model_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize embedding handler: {str(e)}")
            raise
    
    def generate_dense_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Generate dense embeddings using sentence transformers
        
        Args:
            texts: List of text strings
            
        Returns:
            np.ndarray: Dense embeddings matrix
        """
        try:
            embeddings = self.dense_model.encode(texts, show_progress_bar=False)
            logger.info(f"Generated dense embeddings for {len(texts)} texts")
            return embeddings
            
        except Exception as e:
            logger.error(f"Failed to generate dense embeddings: {str(e)}")
            raise
    
    def fit_sparse_embeddings(self, texts: List[str]) -> None:
        """
        Fit TF-IDF vectorizer on document texts
        
        Args:
            texts: List of document texts to fit on
        """
        try:
            self.document_texts = texts
            self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(texts)
            self.tfidf_fitted = True
            
            logger.info(f"Fitted TF-IDF vectorizer on {len(texts)} documents")
            
        except Exception as e:
            logger.error(f"Failed to fit sparse embeddings: {str(e)}")
            raise
    
    def generate_sparse_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Generate sparse embeddings using TF-IDF
        
        Args:
            texts: List of text strings
            
        Returns:
            np.ndarray: Sparse embeddings matrix
        """
        try:
            if not self.tfidf_fitted:
                raise ValueError("TF-IDF vectorizer not fitted. Call fit_sparse_embeddings first.")
            
            sparse_embeddings = self.tfidf_vectorizer.transform(texts)
            logger.info(f"Generated sparse embeddings for {len(texts)} texts")
            return sparse_embeddings
            
        except Exception as e:
            logger.error(f"Failed to generate sparse embeddings: {str(e)}")
            raise
    
    def calculate_dense_similarity(self, query_embedding: np.ndarray, 
                                  document_embeddings: np.ndarray) -> np.ndarray:
        """
        Calculate cosine similarity for dense embeddings
        
        Args:
            query_embedding: Query embedding
            document_embeddings: Document embeddings matrix
            
        Returns:
            np.ndarray: Similarity scores
        """
        try:
            # Ensure query_embedding is 2D
            if query_embedding.ndim == 1:
                query_embedding = query_embedding.reshape(1, -1)
            
            similarities = cosine_similarity(query_embedding, document_embeddings)[0]
            return similarities
            
        except Exception as e:
            logger.error(f"Failed to calculate dense similarity: {str(e)}")
            raise
    
    def calculate_sparse_similarity(self, query_embedding: np.ndarray, 
                                   document_embeddings: np.ndarray) -> np.ndarray:
        """
        Calculate cosine similarity for sparse embeddings
        
        Args:
            query_embedding: Query sparse embedding
            document_embeddings: Document sparse embeddings matrix
            
        Returns:
            np.ndarray: Similarity scores
        """
        try:
            similarities = cosine_similarity(query_embedding, document_embeddings)[0]
            return similarities
            
        except Exception as e:
            logger.error(f"Failed to calculate sparse similarity: {str(e)}")
            raise
    
    def hybrid_search(self, query: str, chunks: List[DocumentChunk], 
                     top_k: int = 10, dense_weight: float = 0.7) -> List[SourceChunk]:
        """
        Perform hybrid search combining dense and sparse similarities
        
        Args:
            query: Search query
            chunks: List of document chunks
            top_k: Number of top chunks to return
            dense_weight: Weight for dense similarity (1 - dense_weight for sparse)
            
        Returns:
            List[SourceChunk]: Top-k most similar chunks with scores
        """
        try:
            if not chunks:
                return []
            
            # Extract texts from chunks
            chunk_texts = [chunk.text for chunk in chunks]
            
            # Generate embeddings for query
            query_dense_emb = self.generate_dense_embeddings([query])
            
            # Generate dense embeddings for chunks
            chunk_dense_emb = self.generate_dense_embeddings(chunk_texts)
            
            # Calculate dense similarities
            dense_similarities = self.calculate_dense_similarity(query_dense_emb, chunk_dense_emb)
            
            # Fit and generate sparse embeddings
            self.fit_sparse_embeddings(chunk_texts)
            query_sparse_emb = self.generate_sparse_embeddings([query])
            chunk_sparse_emb = self.tfidf_matrix
            
            # Calculate sparse similarities
            sparse_similarities = self.calculate_sparse_similarity(query_sparse_emb, chunk_sparse_emb)
            
            # Combine similarities using weighted average
            sparse_weight = 1 - dense_weight
            hybrid_scores = (dense_weight * dense_similarities + 
                           sparse_weight * sparse_similarities)
            
            # Get top-k indices
            top_indices = np.argsort(hybrid_scores)[::-1][:top_k]
            
            # Create SourceChunk objects
            source_chunks = []
            for idx in top_indices:
                chunk = chunks[idx]
                source_chunk = SourceChunk(
                    text=chunk.text,
                    chunk_id=chunk.id,
                    page_number=chunk.page_number,
                    score=float(hybrid_scores[idx])
                )
                source_chunks.append(source_chunk)
            
            logger.info(f"Hybrid search returned {len(source_chunks)} chunks for query: {query[:50]}...")
            return source_chunks
            
        except Exception as e:
            logger.error(f"Hybrid search failed: {str(e)}")
            raise
    
    def get_embeddings_info(self) -> Dict[str, Any]:
        """
        Get information about the embedding models
        
        Returns:
            Dict[str, Any]: Model information
        """
        return {
            "dense_model": {
                "name": self.dense_model.get_sentence_embedding_dimension() if hasattr(self.dense_model, 'get_sentence_embedding_dimension') else "unknown",
                "dimension": self.dense_model.get_sentence_embedding_dimension() if hasattr(self.dense_model, 'get_sentence_embedding_dimension') else 384
            },
            "sparse_model": {
                "name": "TF-IDF",
                "max_features": self.tfidf_vectorizer.max_features,
                "fitted": self.tfidf_fitted,
                "vocabulary_size": len(self.tfidf_vectorizer.vocabulary_) if self.tfidf_fitted else 0
            }
        }
