from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class AddMedia(BaseModel):

    path: str
    tweet_id: int

    model_config = ConfigDict(from_attributes=True)


class AddTweet(BaseModel):

    tweet_data: str
    tweet_media: list[AddMedia]  = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class UserBase(BaseModel):

    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class UserDetail(UserBase):

    followers: list[UserBase] = []
    following: list[UserBase] = []


class UserInfo(BaseModel):

    result: str = "true"

    user: UserDetail
