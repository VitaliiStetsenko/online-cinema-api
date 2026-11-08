"""Cart models."""

from datetime import UTC, datetime
from sqlalchemy import Column, Integer, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.session import Base


class Cart(Base):
    """Shopping cart table."""

    __tablename__ = "carts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    user = relationship("User", backref="cart")
    items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")


class CartItem(Base):
    """Cart items table."""

    __tablename__ = "cart_items"
    __table_args__ = (UniqueConstraint("cart_id", "movie_id", name="uq_cart_movie"),)

    id = Column(Integer, primary_key=True, index=True)
    cart_id = Column(Integer, ForeignKey("carts.id"), nullable=False)
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=False)
    added_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    cart = relationship("Cart", back_populates="items")
    movie = relationship("Movie", backref="in_carts")
