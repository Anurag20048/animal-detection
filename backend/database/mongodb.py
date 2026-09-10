import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class MongoDBClient:
    """Optional MongoDB client.

    Import, connection, and write failures are recorded in status and never
    raised to the detection pipeline.
    """

    COLLECTIONS = {"animals", "detections", "embeddings", "alerts", "system_logs"}

    def __init__(self, settings: Any) -> None:
        self.enabled = bool(getattr(settings, "enable_mongodb", True))
        self.available = False
        self.error: Optional[str] = None
        self.last_error: Optional[str] = None
        self.client: Any = None
        self.db: Any = None
        self._ascending: Any = None

        if not self.enabled:
            self._set_error("MongoDB disabled by settings.")
            return

        try:
            from pymongo import ASCENDING, MongoClient
        except Exception as exc:
            self._set_error(f"pymongo import failed: {exc}")
            return

        self._ascending = ASCENDING
        try:
            self.client = MongoClient(
                getattr(settings, "mongodb_uri", "mongodb://localhost:27017"),
                serverSelectionTimeoutMS=int(getattr(settings, "mongodb_timeout_ms", 1500)),
            )
            self.client.admin.command("ping")
            self.db = self.client[getattr(settings, "mongodb_database", "livestock_monitoring")]
            self._ensure_indexes()
            self.available = True
            self.error = None
            self.last_error = None
        except Exception as exc:
            self.available = False
            self._set_error(f"MongoDB connection failed: {exc}")

    def insert_one(self, collection: str, document: Dict[str, Any]) -> bool:
        if not self._can_use(collection):
            return False
        try:
            payload = self._clean_document(document)
            payload.setdefault("created_at", datetime.utcnow().isoformat())
            self.db[collection].insert_one(payload)
            return True
        except Exception as exc:
            self.available = False
            self._set_error(f"MongoDB insert failed for {collection}: {exc}")
            return False

    def upsert_one(
        self,
        collection: str,
        query: Dict[str, Any],
        document: Dict[str, Any],
    ) -> bool:
        if not self._can_use(collection):
            return False
        try:
            payload = self._clean_document(document)
            payload.setdefault("updated_at", datetime.utcnow().isoformat())
            self.db[collection].update_one(
                self._clean_document(query),
                {"$set": payload},
                upsert=True,
            )
            return True
        except Exception as exc:
            self.available = False
            self._set_error(f"MongoDB upsert failed for {collection}: {exc}")
            return False

    def find_many(
        self,
        collection: str,
        query: Optional[Dict[str, Any]] = None,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        if not self._can_use(collection):
            return []
        try:
            cursor = self.db[collection].find(
                self._clean_document(query or {}),
                {"_id": 0},
            ).limit(max(1, int(limit)))
            return [dict(record) for record in cursor]
        except Exception as exc:
            self.available = False
            self._set_error(f"MongoDB query failed for {collection}: {exc}")
            return []

    def status(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "available": self.available,
            "error": self.error,
        }

    def close(self) -> None:
        if self.client is None:
            return
        try:
            self.client.close()
        except Exception:
            pass

    def _ensure_indexes(self) -> None:
        if self.db is None or self._ascending is None:
            return
        for collection in self.COLLECTIONS:
            self.db[collection]
        self.db.animals.create_index([("animal_id", self._ascending)], unique=True)
        self.db.embeddings.create_index([("animal_id", self._ascending)], unique=True)
        self.db.detections.create_index([("timestamp", self._ascending)])
        self.db.alerts.create_index([("timestamp", self._ascending)])
        self.db.system_logs.create_index([("timestamp", self._ascending)])

    def _can_use(self, collection: str) -> bool:
        if collection not in self.COLLECTIONS:
            self._set_error(f"Unsupported MongoDB collection: {collection}")
            return False
        return bool(self.enabled and self.available and self.db is not None)

    def _set_error(self, message: str) -> None:
        self.error = message
        self.last_error = message

    def _clean_document(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): self._clean_document(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._clean_document(item) for item in value]
        if isinstance(value, tuple):
            return [self._clean_document(item) for item in value]
        if isinstance(value, (datetime, Path)):
            return str(value)
        try:
            return json.loads(json.dumps(value, default=str))
        except Exception:
            return str(value)
