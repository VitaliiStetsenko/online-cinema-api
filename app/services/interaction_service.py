"""Services for movie ratings, comments, and reactions."""

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.interaction import Comment, CommentLike, MovieReaction, Notification, Rating
from app.models.movie import Movie


async def set_rating(db: AsyncSession, user_id: int, movie_id: int, score: int) -> Rating:
    """Create or update the user's rating for a movie."""
    if not await db.get(Movie, movie_id):
        raise ValueError("Movie not found")
    rating = await db.scalar(select(Rating).where(Rating.user_id == user_id, Rating.movie_id == movie_id))
    if rating:
        rating.score = score
    else:
        rating = Rating(user_id=user_id, movie_id=movie_id, score=score)
        db.add(rating)
    await db.commit()
    await db.refresh(rating)
    return rating


async def get_rating_summary(db: AsyncSession, user_id: int, movie_id: int) -> dict:
    """Calculate aggregate and current-user movie ratings."""
    if not await db.get(Movie, movie_id):
        raise ValueError("Movie not found")
    result = await db.execute(select(func.avg(Rating.score), func.count(Rating.id)).where(Rating.movie_id == movie_id))
    average, count = result.one()
    user_score = await db.scalar(select(Rating.score).where(Rating.user_id == user_id, Rating.movie_id == movie_id))
    return {
        "movie_id": movie_id,
        "average_score": round(float(average), 2) if average is not None else None,
        "ratings_count": count,
        "user_score": user_score,
    }


async def create_comment(
    db: AsyncSession, user_id: int, movie_id: int, text: str, parent_comment_id: int | None = None
) -> Comment:
    """Create a comment for a movie."""
    if not await db.get(Movie, movie_id):
        raise ValueError("Movie not found")
    if parent_comment_id is not None:
        parent = await get_comment(db, parent_comment_id)
        if not parent or parent.movie_id != movie_id:
            raise ValueError("Parent comment not found")
    comment = Comment(user_id=user_id, movie_id=movie_id, text=text, parent_comment_id=parent_comment_id)
    db.add(comment)
    if parent_comment_id is not None and parent.user_id != user_id:
        db.add(Notification(user_id=parent.user_id, message="Someone replied to your comment"))
    await db.commit()
    return await get_comment(db, comment.id)


async def get_comment(db: AsyncSession, comment_id: int) -> Comment | None:
    """Get a comment with its reactions."""
    return await db.scalar(
        select(Comment)
        .where(Comment.id == comment_id)
        .options(selectinload(Comment.likes))
        .execution_options(populate_existing=True)
    )


async def list_comments(db: AsyncSession, movie_id: int) -> Sequence[Comment]:
    """List comments for a movie from newest to oldest."""
    result = await db.execute(
        select(Comment)
        .where(Comment.movie_id == movie_id)
        .options(selectinload(Comment.likes))
        .order_by(Comment.created_at.desc())
    )
    return result.scalars().unique().all()


async def update_comment(db: AsyncSession, comment: Comment, text: str) -> Comment:
    """Update a user's comment text."""
    comment.text = text
    await db.commit()
    return await get_comment(db, comment.id)


async def delete_comment(db: AsyncSession, comment: Comment) -> None:
    """Delete a comment and its reactions."""
    await db.delete(comment)
    await db.commit()


async def set_comment_reaction(db: AsyncSession, user_id: int, comment_id: int, is_like: bool) -> Comment:
    """Create or replace the user's like or dislike for a comment."""
    comment = await get_comment(db, comment_id)
    if not comment:
        raise ValueError("Comment not found")
    reaction = await db.scalar(
        select(CommentLike).where(CommentLike.user_id == user_id, CommentLike.comment_id == comment_id)
    )
    reaction_changed = not reaction or reaction.is_like != is_like
    if reaction:
        reaction.is_like = is_like
    else:
        db.add(CommentLike(user_id=user_id, comment_id=comment_id, is_like=is_like))
    if reaction_changed and comment.user_id != user_id:
        action = "liked" if is_like else "disliked"
        db.add(Notification(user_id=comment.user_id, message=f"Someone {action} your comment"))
    await db.commit()
    return await get_comment(db, comment_id)


async def set_movie_reaction(db: AsyncSession, user_id: int, movie_id: int, is_like: bool) -> dict:
    """Create or replace a like or dislike for a movie."""
    if not await db.get(Movie, movie_id):
        raise ValueError("Movie not found")
    reaction = await db.scalar(
        select(MovieReaction).where(MovieReaction.user_id == user_id, MovieReaction.movie_id == movie_id)
    )
    if reaction:
        reaction.is_like = is_like
    else:
        db.add(MovieReaction(user_id=user_id, movie_id=movie_id, is_like=is_like))
    await db.commit()
    return await get_movie_reaction_summary(db, movie_id, is_like)


async def get_movie_reaction_summary(db: AsyncSession, movie_id: int, is_like: bool | None = None) -> dict:
    """Calculate movie like and dislike totals."""
    likes = (
        await db.scalar(
            select(func.count(MovieReaction.id)).where(
                MovieReaction.movie_id == movie_id, MovieReaction.is_like.is_(True)
            )
        )
        or 0
    )
    dislikes = (
        await db.scalar(
            select(func.count(MovieReaction.id)).where(
                MovieReaction.movie_id == movie_id, MovieReaction.is_like.is_(False)
            )
        )
        or 0
    )
    return {"movie_id": movie_id, "is_like": is_like, "likes_count": likes, "dislikes_count": dislikes}


async def list_notifications(db: AsyncSession, user_id: int) -> Sequence[Notification]:
    """List notifications for a user from newest to oldest."""
    result = await db.execute(
        select(Notification).where(Notification.user_id == user_id).order_by(Notification.created_at.desc())
    )
    return result.scalars().all()


async def mark_notification_read(db: AsyncSession, user_id: int, notification_id: int) -> Notification | None:
    """Mark a user's notification as read."""
    notification = await db.scalar(
        select(Notification).where(Notification.id == notification_id, Notification.user_id == user_id)
    )
    if notification:
        notification.is_read = True
        await db.commit()
        await db.refresh(notification)
    return notification


def serialize_comment(comment: Comment, current_user_id: int) -> dict:
    """Prepare comment data including the current user's reaction."""
    likes_count = sum(1 for reaction in comment.likes if reaction.is_like)
    dislikes_count = len(comment.likes) - likes_count
    reaction = next((item.is_like for item in comment.likes if item.user_id == current_user_id), None)
    return {
        "id": comment.id,
        "user_id": comment.user_id,
        "movie_id": comment.movie_id,
        "text": comment.text,
        "created_at": comment.created_at,
        "updated_at": comment.updated_at,
        "likes_count": likes_count,
        "dislikes_count": dislikes_count,
        "current_user_reaction": reaction,
    }
