import json
import uuid
from datetime import datetime

from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


def gen_uuid():
    return uuid.uuid4().hex[:12]


class User(db.Model):
    """Stores registered users."""

    __tablename__ = "users"

    id = db.Column(db.String(12), primary_key=True, default=gen_uuid)
    name = db.Column(db.String(100), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class VideoAnalysis(db.Model):
    """Stores a processed YouTube video and the AI-generated study material."""

    __tablename__ = "video_analyses"

    id = db.Column(
        db.String(12),
        primary_key=True,
        default=gen_uuid
    )

    # User who created this analysis
    user_id = db.Column(
        db.String(12),
        db.ForeignKey("users.id"),
        nullable=True,
        index=True
    )

    user = db.relationship(
        "User",
        backref=db.backref("analyses", lazy=True)
    )

    # Source video info
    video_id = db.Column(
        db.String(20),
        nullable=False,
        index=True
    )

    video_url = db.Column(
        db.String(500),
        nullable=False
    )

    video_title = db.Column(
        db.String(500),
        default="Untitled video"
    )

    channel_name = db.Column(
        db.String(300),
        default=""
    )

    thumbnail_url = db.Column(
        db.String(500),
        default=""
    )

    # Raw material
    transcript_text = db.Column(
        db.Text,
        default=""
    )

    transcript_language = db.Column(
        db.String(20),
        default="en"
    )

    # AI-generated study material
    # Stored as JSON strings
    summary = db.Column(
        db.Text,
        default=""
    )

    key_points_json = db.Column(
        db.Text,
        default="[]"
    )

    quiz_json = db.Column(
        db.Text,
        default="[]"
    )

    flashcards_json = db.Column(
        db.Text,
        default="[]"
    )

    glossary_json = db.Column(
        db.Text,
        default="[]"
    )

    status = db.Column(
        db.String(20),
        default="pending"
    )

    error_message = db.Column(
        db.Text,
        default=""
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    # ---------------------------------------------------------
    # Convenience helpers
    # ---------------------------------------------------------

    @property
    def key_points(self):
        return json.loads(self.key_points_json or "[]")

    @key_points.setter
    def key_points(self, value):
        self.key_points_json = json.dumps(value)

    @property
    def quiz(self):
        return json.loads(self.quiz_json or "[]")

    @quiz.setter
    def quiz(self, value):
        self.quiz_json = json.dumps(value)

    @property
    def flashcards(self):
        return json.loads(self.flashcards_json or "[]")

    @flashcards.setter
    def flashcards(self, value):
        self.flashcards_json = json.dumps(value)

    @property
    def glossary(self):
        return json.loads(self.glossary_json or "[]")

    @glossary.setter
    def glossary(self, value):
        self.glossary_json = json.dumps(value)

    def to_dict(self):
        return {
            "id": self.id,
            "video_id": self.video_id,
            "video_url": self.video_url,
            "video_title": self.video_title,
            "channel_name": self.channel_name,
            "thumbnail_url": self.thumbnail_url,
            "summary": self.summary,
            "key_points": self.key_points,
            "quiz": self.quiz,
            "flashcards": self.flashcards,
            "glossary": self.glossary,
            "status": self.status,
            "error_message": self.error_message,
            "created_at": self.created_at.strftime(
                "%b %d, %Y %H:%M"
            ),
        }