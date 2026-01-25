"""Firebase Firestore client wrapper for LineUp backend."""

from __future__ import annotations

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Firebase Admin SDK (optional - graceful degradation)
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    FIREBASE_AVAILABLE = True
except ImportError:
    firebase_admin = None
    firestore = None
    FIREBASE_AVAILABLE = False
    logger.warning("Firebase Admin SDK not available. Will use in-memory storage.")


class FirestoreClient:
    """Wrapper for Firebase Firestore client with initialization and error handling."""
    
    _instance: Optional[FirestoreClient] = None
    _client: Optional[firestore.Client] = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._client = None
            self._initialized = True
            self._initialize()
    
    def _initialize(self) -> None:
        """Initialize Firebase Firestore client."""
        if not FIREBASE_AVAILABLE:
            logger.warning("Firebase Admin SDK not available. Firestore operations will fail.")
            return
        
        if self._client is not None:
            logger.info("Firestore client already initialized")
            return
        
        try:
            import os
            
            # Check if Firebase app is already initialized
            try:
                self._client = firestore.client()
                logger.info("Using existing Firebase app instance")
                return
            except ValueError:
                # App not initialized, need to initialize
                pass
            
            # Get credentials from environment
            firebase_credentials = os.environ.get("FIREBASE_CREDENTIALS")
            
            if not firebase_credentials:
                logger.warning("FIREBASE_CREDENTIALS not found. Firestore will not be available.")
                return
            
            # Parse and initialize credentials
            cred_dict = json.loads(firebase_credentials)
            cred = credentials.Certificate(cred_dict)
            
            # Initialize Firebase app
            firebase_admin.initialize_app(cred)
            self._client = firestore.client()
            
            logger.info("Firebase Firestore initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Firestore: {str(e)}")
            self._client = None
    
    @property
    def client(self) -> Optional[firestore.Client]:
        """Get the Firestore client instance."""
        return self._client
    
    @property
    def is_available(self) -> bool:
        """Check if Firestore is available."""
        return FIREBASE_AVAILABLE and self._client is not None
    
    def get_collection(self, collection_name: str) -> Optional[firestore.CollectionReference]:
        """Get a Firestore collection reference."""
        if not self.is_available:
            return None
        try:
            return self._client.collection(collection_name)
        except Exception as e:
            logger.error(f"Error getting collection {collection_name}: {str(e)}")
            return None
    
    def get_document(self, collection_name: str, document_id: str) -> Optional[firestore.DocumentReference]:
        """Get a Firestore document reference."""
        if not self.is_available:
            return None
        try:
            collection = self.get_collection(collection_name)
            if collection is None:
                return None
            return collection.document(document_id)
        except Exception as e:
            logger.error(f"Error getting document {collection_name}/{document_id}: {str(e)}")
            return None


# Singleton instance
_firestore_client: Optional[FirestoreClient] = None


def get_firestore_client() -> FirestoreClient:
    """Get the singleton FirestoreClient instance."""
    global _firestore_client
    if _firestore_client is None:
        _firestore_client = FirestoreClient()
    return _firestore_client
