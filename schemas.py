"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime

# Core role-based user schema
class User(BaseModel):
    """
    Users collection schema
    Collection name: "user" (lowercase of class name)
    """
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    role: Literal["student", "mentor", "placement", "recruiter"] = Field(
        "student", description="Role-based access control role"
    )
    department: Optional[str] = Field(None, description="Department or program")
    skills: List[str] = Field(default_factory=list, description="List of skills/tags")
    resume_url: Optional[str] = Field(None, description="Link to resume PDF")
    is_active: bool = Field(True, description="Whether user is active")

# Internship/Industrial training openings posted by placement cell
class Opening(BaseModel):
    title: str = Field(..., description="Role title")
    company: str = Field(..., description="Company/Organization name")
    department: Optional[str] = Field(None, description="Target department")
    description: Optional[str] = Field(None, description="Role description")
    skills_required: List[str] = Field(default_factory=list, description="Required skills")
    stipend_min: Optional[int] = Field(None, ge=0, description="Minimum stipend")
    stipend_max: Optional[int] = Field(None, ge=0, description="Maximum stipend")
    placement_conversion_prob: Optional[int] = Field(
        0, ge=0, le=100, description="Estimated conversion probability in %"
    )
    deadline: Optional[datetime] = Field(None, description="Application deadline")
    created_by: Optional[str] = Field(None, description="Placement user id")

# Student applications to openings
class Application(BaseModel):
    student_id: str = Field(..., description="Student user id")
    opening_id: str = Field(..., description="Opening id")
    status: Literal[
        "applied",
        "under_review",
        "approved",
        "rejected",
        "interview_scheduled",
        "offered",
        "accepted",
        "rejected_offer",
        "completed",
    ] = Field("applied", description="Current application status")
    mentor_id: Optional[str] = Field(None, description="Assigned mentor id")
    interview_datetime: Optional[datetime] = Field(None, description="Interview date/time")
    interview_location: Optional[str] = Field(None, description="Interview location or link")
    feedback: Optional[str] = Field(None, description="Supervisor/mentor feedback")
    certificate_url: Optional[str] = Field(None, description="Generated certificate URL")

# Lightweight notifications
class Notification(BaseModel):
    user_id: str = Field(..., description="Recipient user id")
    message: str = Field(..., description="Notification text")
    read: bool = Field(False, description="Read status")

# Add further schemas as the project expands
