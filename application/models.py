from typing import Optional

from sqlalchemy import JSON, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from application.database import Base


class Tweet(Base):

    __tablename__ = 'tweet'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tweet_data: Mapped[str] = mapped_column(String(280), nullable=False)#
    #tweet_media: Mapped[list['Media']] = relationship(back_populates='tweet')
    tweet_media_ids: Mapped[list['Media']] = relationship(back_populates='tweet')

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    author: Mapped["User"] = relationship(back_populates="tweets")


class Media(Base):
    __tablename__ = 'media'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    path: Mapped[str] = mapped_column(String(1024))
    tweet_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tweet.id"))

    tweet: Mapped[Optional["Tweet"]] = relationship(back_populates="tweet_media_ids")


class FollowLink(Base):
    __tablename__ = "followers"


    follower_id: Mapped[int] = mapped_column(ForeignKey("users.id"),
                                             primary_key=True)
    followed_id: Mapped[int] = mapped_column(ForeignKey("users.id"),
                                             primary_key=True)



class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50))
    api_key: Mapped[str] = mapped_column(String(200), index=True)
    role: Mapped[str] = mapped_column(String(100), default="user")
    tweets: Mapped[list["Tweet"]] = relationship(back_populates="author")
    followers: Mapped[list["User"]] = relationship("User",
                                                   secondary="followers",
                                                   primaryjoin="User.id == followers.c.followed_id",
                                                   secondaryjoin="User.id == followers.c.follower_id",
                                                   back_populates="following")

    following: Mapped[list["User"]] = relationship("User",

                                                   secondary="followers",
                                                   primaryjoin="User.id == FollowLink.follower_id",
                                                   secondaryjoin="User.id == FollowLink.followed_id",
                                                   back_populates="followers")

