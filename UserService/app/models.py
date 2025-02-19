from datetime import datetime

from app.extensions import db


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
    nickname = db.Column(db.String(50), nullable=False, unique=True)
    about = db.Column(db.Text, nullable=True)
    # TODO: Add default url image to profile_img_url
    profile_img_url = db.Column(db.Text,
                                default="https://media.istockphoto.com/id/1300845620/vector/user-icon-flat-isolated-on-white-background-user-symbol-vector-illustration.jpg?s=612x612&w=0&k=20&c=yBeyba0hUkh14_jgv1OKqIH0CCSWU_4ckRkAoy2p73o=")
    member_since = db.Column(db.DateTime, default=datetime.utcnow)

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
