from typing import Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from application.database import Base


class Tweet(Base):

    __tablename__ = "tweet"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tweet_data: Mapped[str] = mapped_column(String(280), nullable=False)  #
    tweet_media_ids: Mapped[list["Media"]] = relationship(
        back_populates="tweet", cascade="all, delete-orphan"
    )

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    author: Mapped["User"] = relationship(back_populates="tweets")

    # Отношение к пользователям, которые лайкнули этот твит
    liked_by_users: Mapped[list["Likes"]] = relationship(back_populates="tweet")
    # Если вы хотите получить сразу объекты User, а не Likes:
    likes: Mapped[list["User"]] = relationship(
        "User",
        secondary="likes",  # Используем таблицу Likes как промежуточную
        primaryjoin="Tweet.id == Likes.tweet_id",  # Твит связан с лайком по tweet_id
        secondaryjoin="User.id == Likes.user_id",  # Лайк связан с юзером по user_id
        viewonly=True,  # Рекомендуется, так как это дублирующая связь для чтения
        overlaps="liked_by_users",
    )


class Media(Base):
    __tablename__ = "media"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    path: Mapped[str] = mapped_column(String(1024))
    tweet_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tweet.id"))

    tweet: Mapped[Optional["Tweet"]] = relationship(back_populates="tweet_media_ids")


class FollowLink(Base):
    __tablename__ = "followers"

    follower_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    followed_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)


class Likes(Base):
    __tablename__ = "likes"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    tweet_id: Mapped[int] = mapped_column(ForeignKey("tweet.id"), primary_key=True)

    user: Mapped["User"] = relationship(back_populates="likes")  # hoo liked
    tweet: Mapped["Tweet"] = relationship(
        back_populates="liked_by_users"
    )  # к какому твиту


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50))
    api_key: Mapped[str] = mapped_column(String(200), index=True)
    role: Mapped[str] = mapped_column(String(100), default="user")
    tweets: Mapped[list["Tweet"]] = relationship(back_populates="author")
    followers: Mapped[list["User"]] = relationship(
        "User",
        secondary="followers",
        primaryjoin="User.id ==  FollowLink.followed_id",
        secondaryjoin="User.id ==  FollowLink.follower_id",
        back_populates="following",
    )

    following: Mapped[list["User"]] = relationship(
        "User",
        secondary="followers",
        primaryjoin="User.id ==  FollowLink.follower_id",
        secondaryjoin="User.id == FollowLink.followed_id",
        back_populates="followers",
    )

    likes: Mapped[list["Likes"]] = relationship(back_populates="user")
