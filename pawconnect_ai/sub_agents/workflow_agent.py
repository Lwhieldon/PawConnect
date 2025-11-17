"""
Workflow Agent - Application Processing Manager
Handles adoption/foster applications and workflows.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from enum import Enum
from loguru import logger

from ..config import settings


class ApplicationStatus(str, Enum):
    """Application status values."""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    BACKGROUND_CHECK = "background_check"
    HOME_ASSESSMENT_SCHEDULED = "home_assessment_scheduled"
    HOME_ASSESSMENT_COMPLETE = "home_assessment_complete"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class WorkflowAgent:
    """
    Specialized agent for managing adoption/foster application workflows.
    """

    def __init__(self):
        """Initialize the workflow agent."""
        self.applications = {}  # In-memory storage (would use Firestore in production)

    def create_application(
        self,
        user_id: str,
        pet_id: str,
        application_type: str = "adoption"
    ) -> Dict[str, Any]:
        """
        Create a new application.

        Args:
            user_id: User identifier
            pet_id: Pet identifier
            application_type: Type of application (adoption or foster)

        Returns:
            Application dictionary
        """
        try:
            application_id = f"app_{user_id}_{pet_id}_{int(datetime.utcnow().timestamp())}"

            application = {
                "application_id": application_id,
                "user_id": user_id,
                "pet_id": pet_id,
                "type": application_type,
                "status": ApplicationStatus.DRAFT.value,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "form_data": {},
                "timeline": [
                    {
                        "status": ApplicationStatus.DRAFT.value,
                        "timestamp": datetime.utcnow().isoformat(),
                        "note": "Application created"
                    }
                ]
            }

            self.applications[application_id] = application

            logger.info(f"Created application {application_id}")
            return application

        except Exception as e:
            logger.error(f"Error creating application: {e}")
            raise

    def submit_application(
        self,
        application_id: str,
        form_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Submit an application with form data.

        Args:
            application_id: Application identifier
            form_data: Application form data

        Returns:
            Updated application dictionary
        """
        try:
            if application_id not in self.applications:
                raise ValueError(f"Application {application_id} not found")

            application = self.applications[application_id]

            # Validate form data
            is_valid, errors = self._validate_form_data(form_data, application["type"])
            if not is_valid:
                raise ValueError(f"Invalid form data: {errors}")

            # Update application
            application["form_data"] = form_data
            application["status"] = ApplicationStatus.SUBMITTED.value
            application["updated_at"] = datetime.utcnow().isoformat()
            application["submitted_at"] = datetime.utcnow().isoformat()

            # Add to timeline
            application["timeline"].append({
                "status": ApplicationStatus.SUBMITTED.value,
                "timestamp": datetime.utcnow().isoformat(),
                "note": "Application submitted for review"
            })

            logger.info(f"Application {application_id} submitted")

            # Trigger next workflow step
            self._advance_workflow(application_id)

            return application

        except Exception as e:
            logger.error(f"Error submitting application: {e}")
            raise

    def _validate_form_data(
        self,
        form_data: Dict[str, Any],
        application_type: str
    ) -> tuple[bool, List[str]]:
        """Validate application form data."""
        errors = []
        required_fields = [
            "first_name",
            "last_name",
            "email",
            "phone",
            "address",
            "city",
            "state",
            "zip_code",
            "home_type",
            "home_owned_rented"
        ]

        for field in required_fields:
            if field not in form_data or not form_data[field]:
                errors.append(f"Missing required field: {field}")

        # Application-specific validation
        if application_type == "adoption":
            if "adoption_reason" not in form_data:
                errors.append("Missing adoption reason")

        return len(errors) == 0, errors

    def _advance_workflow(self, application_id: str) -> None:
        """Advance application to next workflow step."""
        try:
            application = self.applications[application_id]
            current_status = application["status"]

            # Define workflow transitions
            if current_status == ApplicationStatus.SUBMITTED.value:
                # Move to under review
                self._update_status(
                    application_id,
                    ApplicationStatus.UNDER_REVIEW.value,
                    "Application under review by shelter staff"
                )

                # In production, would trigger background check
                # For now, simulate immediate transition
                self._update_status(
                    application_id,
                    ApplicationStatus.BACKGROUND_CHECK.value,
                    "Background check initiated"
                )

        except Exception as e:
            logger.error(f"Error advancing workflow: {e}")

    def _update_status(
        self,
        application_id: str,
        new_status: str,
        note: str
    ) -> None:
        """Update application status."""
        if application_id not in self.applications:
            return

        application = self.applications[application_id]
        application["status"] = new_status
        application["updated_at"] = datetime.utcnow().isoformat()

        application["timeline"].append({
            "status": new_status,
            "timestamp": datetime.utcnow().isoformat(),
            "note": note
        })

        logger.info(f"Application {application_id} status updated to {new_status}")

    def schedule_home_assessment(
        self,
        application_id: str,
        scheduled_time: datetime
    ) -> Dict[str, Any]:
        """
        Schedule a home assessment visit.

        Args:
            application_id: Application identifier
            scheduled_time: Scheduled visit time

        Returns:
            Updated application dictionary
        """
        try:
            if application_id not in self.applications:
                raise ValueError(f"Application {application_id} not found")

            application = self.applications[application_id]

            application["home_assessment"] = {
                "scheduled_time": scheduled_time.isoformat(),
                "status": "scheduled"
            }

            self._update_status(
                application_id,
                ApplicationStatus.HOME_ASSESSMENT_SCHEDULED.value,
                f"Home assessment scheduled for {scheduled_time.strftime('%Y-%m-%d %H:%M')}"
            )

            return application

        except Exception as e:
            logger.error(f"Error scheduling home assessment: {e}")
            raise

    def complete_home_assessment(
        self,
        application_id: str,
        passed: bool,
        notes: str = ""
    ) -> Dict[str, Any]:
        """
        Record home assessment results.

        Args:
            application_id: Application identifier
            passed: Whether assessment passed
            notes: Assessment notes

        Returns:
            Updated application dictionary
        """
        try:
            if application_id not in self.applications:
                raise ValueError(f"Application {application_id} not found")

            application = self.applications[application_id]

            application["home_assessment"]["status"] = "completed"
            application["home_assessment"]["passed"] = passed
            application["home_assessment"]["notes"] = notes
            application["home_assessment"]["completed_at"] = datetime.utcnow().isoformat()

            if passed:
                self._update_status(
                    application_id,
                    ApplicationStatus.HOME_ASSESSMENT_COMPLETE.value,
                    "Home assessment passed"
                )
                # Approve application
                self.approve_application(application_id)
            else:
                self._update_status(
                    application_id,
                    ApplicationStatus.REJECTED.value,
                    f"Home assessment did not pass: {notes}"
                )

            return application

        except Exception as e:
            logger.error(f"Error completing home assessment: {e}")
            raise

    def approve_application(self, application_id: str) -> Dict[str, Any]:
        """Approve an application."""
        try:
            if application_id not in self.applications:
                raise ValueError(f"Application {application_id} not found")

            self._update_status(
                application_id,
                ApplicationStatus.APPROVED.value,
                "Application approved - ready for adoption/foster"
            )

            application = self.applications[application_id]
            application["approved_at"] = datetime.utcnow().isoformat()

            return application

        except Exception as e:
            logger.error(f"Error approving application: {e}")
            raise

    def reject_application(
        self,
        application_id: str,
        reason: str
    ) -> Dict[str, Any]:
        """Reject an application."""
        try:
            if application_id not in self.applications:
                raise ValueError(f"Application {application_id} not found")

            self._update_status(
                application_id,
                ApplicationStatus.REJECTED.value,
                f"Application rejected: {reason}"
            )

            application = self.applications[application_id]
            application["rejected_at"] = datetime.utcnow().isoformat()
            application["rejection_reason"] = reason

            return application

        except Exception as e:
            logger.error(f"Error rejecting application: {e}")
            raise

    def get_application(self, application_id: str) -> Optional[Dict[str, Any]]:
        """Get application by ID."""
        return self.applications.get(application_id)

    def get_user_applications(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all applications for a user."""
        return [
            app for app in self.applications.values()
            if app["user_id"] == user_id
        ]

    def get_application_status(self, application_id: str) -> Optional[str]:
        """Get current status of an application."""
        application = self.applications.get(application_id)
        return application["status"] if application else None
