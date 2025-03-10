from datetime import datetime

from app.extensions import db

from werkzeug.security import generate_password_hash, check_password_hash


class Follower(db.Model):
    """
    Represents the many-to-many relationship for followers.

    Attributes:
        id (int): Primary key for the relationship.
        user_id (int): The user who is being followed.
        follower_id (int): The user who follows another user.
        created_at (datetime): Timestamp of when the follow action occurred.
    """
    __tablename__ = "followers"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    follower_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Unique constraint to prevent duplicate follows
    __table_args__ = (
        db.UniqueConstraint("user_id", "follower_id", name="unique_follow"),
    )


class User(db.Model):
    """
    Represents a user profile in the system.

    Attributes:
        id (int): Primary key, uniquely identifies a user.
        name (str): The full name of the user.
        nickname (str): A unique nickname for searching and mentions.
        about (str, optional): User bio or description.
        profile_img_url (str, optional): Profile image stored in AWS S3.
        member_since (datetime): The date when the user registered.
    """
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    nickname = db.Column(db.String(50), nullable=False, unique=True)
    about = db.Column(db.Text, nullable=True)
    profile_img_url = db.Column(db.Text, default="https://shorturl.at/xA1LB")
    member_since = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, raw_password):
        """Hash the password before saving it."""
        self.password = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        """Check if the provided password matches the hashed password."""
        return check_password_hash(self.password, raw_password)

    followers = db.relationship(
        "Follower",
        foreign_keys=[Follower.user_id],
        backref="followed_user",
        lazy="dynamic"
    )
    following = db.relationship(
        "Follower",
        foreign_keys=[Follower.follower_id],
        backref="following_user",
        lazy="dynamic"
    )
