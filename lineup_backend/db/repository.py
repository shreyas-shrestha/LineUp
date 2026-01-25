"""Generic repository pattern for Firestore data access."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar, Generic

from lineup_backend.db.firestore_client import get_firestore_client

# Import firestore for Query constants
try:
    from firebase_admin import firestore
except ImportError:
    firestore = None

logger = logging.getLogger(__name__)

T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    """Base repository class for Firestore operations."""
    
    def __init__(self, collection_name: str):
        """
        Initialize repository with collection name.
        
        Args:
            collection_name: Name of the Firestore collection
        """
        self.collection_name = collection_name
        self._firestore = get_firestore_client()
    
    @property
    def collection(self):
        """Get Firestore collection reference."""
        if not self._firestore.is_available:
            return None
        return self._firestore.get_collection(self.collection_name)
    
    def create(self, document_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create a new document in Firestore.
        
        Args:
            document_id: Document ID
            data: Document data
            
        Returns:
            Created document data or None if failed
        """
        if not self._firestore.is_available:
            logger.warning(f"Firestore not available. Cannot create {self.collection_name}/{document_id}")
            return None
        
        try:
            doc_ref = self.collection.document(document_id)
            doc_ref.set(data)
            logger.info(f"Created document {self.collection_name}/{document_id}")
            return {**data, "id": document_id}
        except Exception as e:
            logger.error(f"Error creating document {self.collection_name}/{document_id}: {str(e)}")
            return None
    
    def get_by_id(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a document by ID.
        
        Args:
            document_id: Document ID
            
        Returns:
            Document data or None if not found
        """
        if not self._firestore.is_available:
            logger.warning(f"Firestore not available. Cannot get {self.collection_name}/{document_id}")
            return None
        
        try:
            doc_ref = self.collection.document(document_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                return None
            
            data = doc.to_dict()
            data["id"] = doc.id
            return data
        except Exception as e:
            error_str = str(e)
            if "SERVICE_DISABLED" in error_str or "has not been used" in error_str or "is disabled" in error_str:
                logger.warning(
                    f"Cloud Firestore API not enabled. "
                    f"Enable it at: https://console.developers.google.com/apis/api/firestore.googleapis.com/overview"
                )
            else:
                logger.error(f"Error getting document {self.collection_name}/{document_id}: {str(e)}")
            return None
    
    def update(self, document_id: str, data: Dict[str, Any], merge: bool = True) -> Optional[Dict[str, Any]]:
        """
        Update a document.
        
        Args:
            document_id: Document ID
            data: Data to update
            merge: Whether to merge with existing data (default: True)
            
        Returns:
            Updated document data or None if failed
        """
        if not self._firestore.is_available:
            logger.warning(f"Firestore not available. Cannot update {self.collection_name}/{document_id}")
            return None
        
        try:
            doc_ref = self.collection.document(document_id)
            
            if merge:
                doc_ref.update(data)
            else:
                doc_ref.set(data, merge=False)
            
            logger.info(f"Updated document {self.collection_name}/{document_id}")
            
            # Return updated document
            doc = doc_ref.get()
            if doc.exists:
                result = doc.to_dict()
                result["id"] = doc.id
                return result
            return None
        except Exception as e:
            logger.error(f"Error updating document {self.collection_name}/{document_id}: {str(e)}")
            return None
    
    def delete(self, document_id: str) -> bool:
        """
        Delete a document.
        
        Args:
            document_id: Document ID
            
        Returns:
            True if deleted successfully, False otherwise
        """
        if not self._firestore.is_available:
            logger.warning(f"Firestore not available. Cannot delete {self.collection_name}/{document_id}")
            return False
        
        try:
            doc_ref = self.collection.document(document_id)
            doc_ref.delete()
            logger.info(f"Deleted document {self.collection_name}/{document_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting document {self.collection_name}/{document_id}: {str(e)}")
            return False
    
    def get_all(self, limit: Optional[int] = None, order_by: Optional[str] = None, 
                direction: str = "asc") -> List[Dict[str, Any]]:
        """
        Get all documents from collection.
        
        Args:
            limit: Maximum number of documents to return
            order_by: Field to order by
            direction: Order direction ("asc" or "desc")
            
        Returns:
            List of documents
        """
        if not self._firestore.is_available:
            logger.warning(f"Firestore not available. Cannot get all from {self.collection_name}")
            return []
        
        try:
            query = self.collection
            
            if order_by:
                if direction == "desc":
                    query = query.order_by(order_by, direction=firestore.Query.DESCENDING)
                else:
                    query = query.order_by(order_by, direction=firestore.Query.ASCENDING)
            
            if limit:
                query = query.limit(limit)
            
            docs = query.stream()
            results = []
            
            for doc in docs:
                data = doc.to_dict()
                data["id"] = doc.id
                results.append(data)
            
            return results
        except Exception as e:
            logger.error(f"Error getting all documents from {self.collection_name}: {str(e)}")
            return []
    
    def query(self, filters: List[tuple], limit: Optional[int] = None, 
              order_by: Optional[str] = None, direction: str = "asc") -> List[Dict[str, Any]]:
        """
        Query documents with filters.
        
        Args:
            filters: List of (field, operator, value) tuples
                    Operators: ==, <, <=, >, >=, !=, in, array_contains
            limit: Maximum number of documents to return
            order_by: Field to order by
            direction: Order direction ("asc" or "desc")
            
        Returns:
            List of matching documents
        """
        if not self._firestore.is_available:
            logger.warning(f"Firestore not available. Cannot query {self.collection_name}")
            return []
        
        try:
            query = self.collection
            
            # Apply filters
            for field, operator, value in filters:
                if operator == "==":
                    query = query.where(field, "==", value)
                elif operator == "<":
                    query = query.where(field, "<", value)
                elif operator == "<=":
                    query = query.where(field, "<=", value)
                elif operator == ">":
                    query = query.where(field, ">", value)
                elif operator == ">=":
                    query = query.where(field, ">=", value)
                elif operator == "!=":
                    query = query.where(field, "!=", value)
                elif operator == "in":
                    query = query.where(field, "in", value)
                elif operator == "array_contains":
                    query = query.where(field, "array_contains", value)
            
            # Apply ordering
            if order_by:
                if direction == "desc":
                    query = query.order_by(order_by, direction=firestore.Query.DESCENDING)
                else:
                    query = query.order_by(order_by, direction=firestore.Query.ASCENDING)
            
            # Apply limit
            if limit:
                query = query.limit(limit)
            
            docs = query.stream()
            results = []
            
            for doc in docs:
                data = doc.to_dict()
                data["id"] = doc.id
                results.append(data)
            
            return results
        except Exception as e:
            error_str = str(e)
            # Check for API not enabled error
            if "SERVICE_DISABLED" in error_str or "has not been used" in error_str or "is disabled" in error_str:
                logger.warning(
                    f"Cloud Firestore API not enabled. "
                    f"Enable it at: https://console.developers.google.com/apis/api/firestore.googleapis.com/overview?project=finallineup-117a0"
                )
            else:
                logger.error(f"Error querying {self.collection_name}: {str(e)}")
            return []
    
    def count(self, filters: Optional[List[tuple]] = None) -> int:
        """
        Count documents matching filters.
        
        Args:
            filters: Optional list of (field, operator, value) tuples
            
        Returns:
            Count of matching documents
        """
        if not self._firestore.is_available:
            return 0
        
        try:
            if filters:
                results = self.query(filters)
                return len(results)
            else:
                # Use Firestore count query if available (Firestore v2.0+)
                try:
                    query = self.collection
                    count = len(list(query.stream()))
                    return count
                except:
                    # Fallback to get_all and count
                    return len(self.get_all())
        except Exception as e:
            logger.error(f"Error counting documents in {self.collection_name}: {str(e)}")
            return 0
