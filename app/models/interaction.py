"""Models for favorites, ratings and comments."""

from datetime import UTC, datetime
from sqlalchemy import Column, Integer, ForeignKey, DateTime, Text, Boolean, String, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import relationship
from app.db.session import Base


class Favorite(Base):
    """User favorites table."""

    __tablename__ = "favorites"
    __table_args__ = (UniqueConstraint("user_id", "movie_id", name="uq_user_movie_favorite"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=False)
    added_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    user = relationship("User", backref="favorites")
    movie = relationship("Movie", backref="favorited_by")


class Rating(Base):
    """Movie ratings table."""

    __tablename__ = "ratings"
    __table_args__ = (
        UniqueConstraint("user_id", "movie_id", name="uq_user_movie_rating"),
        CheckConstraint("score >= 1 AND score <= 10", name="check_rating_score"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=False)
    score = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    user = relationship("User", backref="ratings")
    movie = relationship("Movie", backref="ratings")


class Comment(Base):
    """Movie comments table."""

    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=False)
    text = Column(Text, nullable=False)
    parent_comment_id = Column(Integer, ForeignKey("comments.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False
    )

    user = relationship("User", backref="comments")
    movie = relationship("Movie", backref="comments")
    likes = relationship("CommentLike", back_populates="comment", cascade="all, delete-orphan")
    parent = relationship("Comment", remote_side=[id], backref="replies")


class CommentLike(Base):
    """Comment likes table."""

    __tablename__ = "comment_likes"
    __table_args__ = (UniqueConstraint("user_id", "comment_id", name="uq_user_comment_like"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    comment_id = Column(Integer, ForeignKey("comments.id"), nullable=False)
    is_like = Column(Boolean, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    user = relationship("User", backref="comment_likes")
    comment = relationship("Comment", back_populates="likes")


class MovieReaction(Base):
    """Movie likes and dislikes table."""

    __tablename__ = "movie_reactions"
    __table_args__ = (UniqueConstraint("user_id", "movie_id", name="uq_user_movie_reaction"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=False)
    is_like = Column(Boolean, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


class Notification(Base):
    """User notifications table."""

    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    message = Column(String(500), nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
