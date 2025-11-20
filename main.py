import os
from datetime import datetime
from typing import List, Optional, Any, Dict

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import User, Opening, Application, Notification

app = FastAPI(title="Campus Internship & Placement Portal API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Helpers
class IdModel(BaseModel):
    id: str


def to_collection_name(model_cls: Any) -> str:
    return model_cls.__name__.lower()


def serialize_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    out = {**doc}
    _id = out.pop("_id", None)
    if _id is not None:
        out["id"] = str(_id)
    # Convert datetimes to isoformat strings
    for k, v in list(out.items()):
        if isinstance(v, datetime):
            out[k] = v.isoformat()
    return out


@app.get("/")
def read_root():
    return {"message": "Campus Internship & Placement API running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": [],
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, "name") else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:80]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"

    return response


# Users
@app.post("/users", response_model=IdModel)
def create_user(user: User):
    user_id = create_document(to_collection_name(User), user)
    return {"id": user_id}


@app.get("/users")
def list_users(role: Optional[str] = None, email: Optional[str] = None):
    filt: Dict[str, Any] = {}
    if role:
        filt["role"] = role
    if email:
        filt["email"] = email
    docs = get_documents(to_collection_name(User), filt)
    return [serialize_doc(d) for d in docs]


# Openings
@app.post("/openings", response_model=IdModel)
def create_opening(opening: Opening):
    opening_id = create_document(to_collection_name(Opening), opening)
    return {"id": opening_id}


@app.get("/openings")
def list_openings(department: Optional[str] = None, skill: Optional[str] = None):
    filt: Dict[str, Any] = {}
    if department:
        filt["department"] = department
    if skill:
        filt["skills_required"] = {"$in": [skill]}
    docs = get_documents(to_collection_name(Opening), filt)
    return [serialize_doc(d) for d in docs]


@app.get("/openings/recommendations")
def recommend_openings(student_id: str, limit: int = 10):
    # Fetch student
    student = db[to_collection_name(User)].find_one({"_id": ObjectId(student_id)})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    student_skills = set(student.get("skills", []))
    openings = list(db[to_collection_name(Opening)].find({}))
    scored = []
    for o in openings:
        req = set(o.get("skills_required", []))
        overlap = len(student_skills & req)
        score = overlap + (1 if (student.get("department") and student.get("department") == o.get("department")) else 0)
        scored.append((score, o))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [serialize_doc(o) | {"match_score": s} for s, o in scored[:limit]]


# Applications
@app.post("/applications", response_model=IdModel)
def create_application(apply: Application):
    # Prevent duplicate application per student/opening
    existing = db[to_collection_name(Application)].find_one(
        {"student_id": apply.student_id, "opening_id": apply.opening_id}
    )
    if existing:
        raise HTTPException(status_code=400, detail="Application already exists")
    app_id = create_document(to_collection_name(Application), apply)
    # Notify placement/mentor later if configured
    return {"id": app_id}


class ApplicationUpdate(BaseModel):
    status: Optional[str] = None
    mentor_id: Optional[str] = None
    interview_datetime: Optional[datetime] = None
    interview_location: Optional[str] = None
    feedback: Optional[str] = None


@app.get("/applications")
def list_applications(
    student_id: Optional[str] = None,
    opening_id: Optional[str] = None,
    mentor_id: Optional[str] = None,
):
    filt: Dict[str, Any] = {}
    if student_id:
        filt["student_id"] = student_id
    if opening_id:
        filt["opening_id"] = opening_id
    if mentor_id:
        filt["mentor_id"] = mentor_id
    docs = get_documents(to_collection_name(Application), filt)
    return [serialize_doc(d) for d in docs]


@app.patch("/applications/{application_id}")
def update_application(application_id: str, payload: ApplicationUpdate):
    try:
        _id = ObjectId(application_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid application id")

    update_dict = {k: v for k, v in payload.model_dump().items() if v is not None}

    # If completed with feedback, generate certificate link (stub)
    if update_dict.get("status") == "completed":
        update_dict["certificate_url"] = f"https://certs.example.com/{application_id}.pdf"

    update_dict["updated_at"] = datetime.utcnow()

    res = db[to_collection_name(Application)].update_one({"_id": _id}, {"$set": update_dict})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Application not found")

    doc = db[to_collection_name(Application)].find_one({"_id": _id})
    return serialize_doc(doc)


# Notifications (simple)
@app.post("/notifications", response_model=IdModel)
def create_notification(note: Notification):
    note_id = create_document(to_collection_name(Notification), note)
    return {"id": note_id}


@app.get("/notifications")
def list_notifications(user_id: str, unread_only: bool = False):
    filt: Dict[str, Any] = {"user_id": user_id}
    if unread_only:
        filt["read"] = False
    docs = get_documents(to_collection_name(Notification), filt)
    return [serialize_doc(d) for d in docs]


@app.patch("/notifications/{notification_id}")
def mark_notification_read(notification_id: str):
    try:
        _id = ObjectId(notification_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid notification id")
    res = db[to_collection_name(Notification)].update_one({"_id": _id}, {"$set": {"read": True}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    doc = db[to_collection_name(Notification)].find_one({"_id": _id})
    return serialize_doc(doc)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
