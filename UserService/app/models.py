from datetime import datetime

from extensions import db


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
    nickname = db.Column(db.String(50), nullable=False, unique=True)
    about = db.Column(db.Text, nullable=True)
    # TODO: Add default url image to profile_img_url
    profile_img_url = db.Column(db.Text, default="https://s3.amazonaws.com/default_profile.jpg")
    member_since = db.Column(db.DateTime, default=datetime.utcnow)

    # Define relationships for followers and following
    followers = db.relationship(
        "Follower",
        foreign_keys="[Follower.user_id]",
        backref="followed_user",
        lazy="dynamic"
    )
    following = db.relationship(
        "Follower",
        foreign_keys="[Follower.follower_id]",
        backref="following_user",
        lazy="dynamic"
    )


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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Unique constraint to prevent duplicate follows
    __table_args__ = (
        db.UniqueConstraint("user_id", "follower_id", name="unique_follow"),
    )
