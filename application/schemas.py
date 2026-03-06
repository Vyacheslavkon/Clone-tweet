from pydantic import BaseModel, ConfigDict, Field, field_validator


class UploadMedia(BaseModel):

    media_id: int

    model_config = ConfigDict(from_attributes=True)


class GetMedia(BaseModel):

    path: str

    model_config = ConfigDict(from_attributes=True)


class AddTweet(BaseModel):

    tweet_data: str

    tweet_media_ids: list[int] = Field(default_factory=list, alias="tweet_media_ids")

    model_config = ConfigDict(from_attributes=True)


class UserBase(BaseModel):

    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class UserDetail(UserBase):

    followers: list[UserBase] = []
    following: list[UserBase] = []

    model_config = ConfigDict(from_attributes=True)


class UserInfo(BaseModel):

    result: str = "true"

    user: UserDetail

    model_config = ConfigDict(from_attributes=True)


class AddUser(BaseModel):

    name: str
    api_key: str


class DeleteTweet(BaseModel):

    id: int

    model_config = ConfigDict(from_attributes=True)


class Like(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int = Field(validation_alias="id")
    name: str = Field(validation_alias="name")

    @field_validator("name", mode="before")
    @classmethod
    def get_name_from_user_relation(cls, v, info):
        # Если 'v' это объект пользователя из связи Like.user
        if hasattr(v, "name"):
            return v.name
        return v


class AddLike(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    user_id: int
    tweet_id: int = Field(alias="id")


class Tweet(BaseModel):

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int

    tweet_data: str = Field(
        serialization_alias="content", validation_alias="tweet_data"
    )

    # tweet_media_ids: list[GetMedia] = Field(alias="attachments")
    attachments: list[str] = Field(validation_alias="tweet_media_ids")

    author: UserBase = Field(validation_alias="author")

    likes: list[Like]

    @field_validator("attachments", mode="before")
    @classmethod
    def transform_media_to_links(cls, v):

        if isinstance(v, list):
            return [f"{media.path}" for media in v if hasattr(media, "path")]

        return v


class GetTweets(BaseModel):

    result: bool = True

    tweets: list[Tweet]

    model_config = ConfigDict(from_attributes=True)


class FollowlinkSchem(BaseModel):

    follower_id: int
    followed_id: int

    model_config = ConfigDict(from_attributes=True)
