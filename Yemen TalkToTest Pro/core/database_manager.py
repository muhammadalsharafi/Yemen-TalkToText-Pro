"""
Database Management Module for TalkToText Pro-v1.0 Engine
Handles all MongoDB database operations including user management and job tracking.
"""

import datetime
from typing import Any, Dict, List
import bcrypt
from pymongo import MongoClient, errors, ReturnDocument
from bson.objectid import ObjectId

from utils.custom_exceptions import ProjectBaseException
from core.message_system import MessageSystem, MessageCode

class DatabaseManager:
    """
    Handles all interactions with MongoDB database for user management and job tracking.
    """
    
    def __init__(self, connection_string: str, db_name: str = "TalkToTextDB"):
        """
        Initialize database connection and setup collections.
        """
        try:
            self.client = MongoClient(connection_string)
            self.client.admin.command('ismaster')
            
            self.db = self.client[db_name]
            self.users = self.db.users
            self.jobs = self.db.jobs
            
            self.users.create_index("email", unique=True)
            
            MessageSystem.log_success(MessageCode.DB_CONNECTION_SUCCESS)
            
        except errors.ConnectionFailure as e:
            MessageSystem.log_error(MessageCode.DB_CONNECTION_FAILED, details=str(e))
            raise ProjectBaseException(f"Could not connect to MongoDB: {e}")

    def create_user(self, first_name: str, last_name: str, email: str, plain_text_password: str, profile_picture_url: str = None) -> ObjectId:
        """
        Create new user or return existing user ID if email already exists.
        """
        try:
            hashed_password = bcrypt.hashpw(plain_text_password.encode('utf-8'), bcrypt.gensalt())
            
            user_doc = {
                "firstName": first_name,
                "lastName": last_name,
                "email": email.lower(),
                "passwordHash": hashed_password,
                "profilePictureUrl": profile_picture_url,
                "createdAt": datetime.datetime.now(datetime.timezone.utc)
            }
            
            user_id = self.users.insert_one(user_doc).inserted_id
            MessageSystem.log_success(MessageCode.DB_USER_CREATED, user_id=user_id)
            return user_id
            
        except errors.DuplicateKeyError:
            existing_user = self.get_user_by_email(email)
            if existing_user:
                MessageSystem.log_info(MessageCode.DB_USER_EXISTS, user_id=existing_user.get('_id'))
                return existing_user.get('_id')
            raise

    def get_user_by_email(self, email: str) -> Dict[str, Any]:
        """
        Retrieve user document by email address.
        """
        return self.users.find_one({"email": email.lower()})

    def create_job(self, user_id: ObjectId, source_type: str, source_value: str) -> ObjectId:
        """
        Create new processing job for a user with 'visible' status.
        """
        current_time = datetime.datetime.now(datetime.timezone.utc)
        
        job_doc = {
            "userId": user_id,
            "createdAt": current_time,
            "updatedAt": current_time,
            "status": "pending",
            "visibility": "visible", # <-- New field for soft delete
            "source": {"type": source_type, "value": source_value},
            "processing": {},
            "errorDetails": None,
            "eventLog": []
        }
        
        job_id = self.jobs.insert_one(job_doc).inserted_id
        MessageSystem.log_success(MessageCode.DB_JOB_CREATED, job_id=job_id)
        return job_id

    def get_user_jobs(self, user_id: ObjectId) -> List[Dict[str, Any]]:
        """
        Retrieve all VISIBLE jobs for a specific user, sorted by most recent.
        """
        return list(self.jobs.find({"userId": user_id, "visibility": "visible"}).sort("createdAt", -1))

    # --- START: SOFT DELETE METHODS ---
    def soft_delete_job(self, job_id: ObjectId, user_id: ObjectId) -> bool:
        """
        Soft deletes a single job by setting its visibility to 'hidden'.
        Ensures the job belongs to the user requesting the delete.
        """
        result = self.jobs.update_one(
            {"_id": job_id, "userId": user_id},
            {"$set": {"visibility": "hidden"}}
        )
        return result.modified_count > 0

    def soft_delete_all_user_jobs(self, user_id: ObjectId) -> int:
        """
        Soft deletes all of a user's jobs.
        Returns the number of jobs that were hidden.
        """
        result = self.jobs.update_many(
            {"userId": user_id, "visibility": "visible"},
            {"$set": {"visibility": "hidden"}}
        )
        return result.modified_count
    # --- END: SOFT DELETE METHODS ---

    def add_log_entry(self, job_id: ObjectId, stage: str, step: str, status: str, 
                        start_time: datetime.datetime, end_time: datetime.datetime, message: str = ""):
        """
        Add detailed, timed event entry to job's execution log.
        """
        duration = round((end_time - start_time).total_seconds(), 2)
        
        event = {
            "stage": stage,
            "step": step,
            "status": status,
            "startTime": start_time,
            "endTime": end_time,
            "durationSeconds": duration,
            "message": message
        }
        
        self.jobs.update_one(
            {"_id": job_id}, 
            {"$push": {"eventLog": event}}
        )
        
    def update_job_processing_data(self, job_id: ObjectId, field_to_update: dict):
        """
        Updates a specific field within the 'processing' sub-document of a job.
        """
        update_doc = {
            "$set": {f"processing.{key}": value for key, value in field_to_update.items()}
        }
        self.jobs.update_one({"_id": job_id}, update_doc)
        
    def update_job_status(self, job_id: ObjectId, new_status: str, error_stage: str = None, error_message: str = None):
        """
        Update job status and optionally record error details.
        """
        update_doc = {
            "$set": {
                "status": new_status,
                "updatedAt": datetime.datetime.now(datetime.timezone.utc)
            }
        }
        
        if new_status == "failed" and error_stage and error_message:
            update_doc["$set"]["errorDetails"] = {
                "stage": error_stage,
                "message": error_message
            }
        
        self.jobs.update_one({"_id": job_id}, update_doc)
        MessageSystem.log_success(MessageCode.DB_JOB_UPDATED, job_id=job_id, status=new_status.upper())

    def _deep_merge_dicts(self, base: dict, new: dict) -> dict:
        """
        Recursively merge two dicts.
        """
        merged = dict(base)
        for k, v in new.items():
            if k in merged and isinstance(merged[k], dict) and isinstance(v, dict):
                merged[k] = self._deep_merge_dicts(merged[k], v)
            else:
                merged[k] = v
        return merged

    def save_job_results(self, job_id: ObjectId, processing_data: dict):
        """
        Save final processing results to job document.
        """
        existing_doc = self.jobs.find_one({"_id": job_id}, {"processing": 1}) or {}
        existing_processing = existing_doc.get("processing", {}) or {}

        merged_processing = self._deep_merge_dicts(existing_processing, processing_data)

        update_doc = {
            "$set": {
                "processing": merged_processing,
                "status": "completed",
                "updatedAt": datetime.datetime.now(datetime.timezone.utc)
            }
        }

        self.jobs.update_one({"_id": job_id}, update_doc)
        MessageSystem.log_success(MessageCode.DB_RESULTS_SAVED, job_id=job_id)