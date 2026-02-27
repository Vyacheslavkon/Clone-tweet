from pydantic import BaseModel, ConfigDict, Field, field_validator


class UploadMedia(BaseModel):

    media_id: int

    model_config = ConfigDict(from_attributes=True)


class GetMedia(BaseModel):

    path: str


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


class UserInfo(BaseModel):

    result: str = "true"

    user: UserDetail


class DeleteTweet(BaseModel):

    id: int

    model_config = ConfigDict(from_attributes=True)


class Like(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    name: str = Field(validation_alias="user_name")  # Ожидаем под таким именем

    @field_validator("name", mode="before")
    @classmethod
    def get_name_from_user_relation(cls, v, info):
        # Если 'v' это объект пользователя из связи Like.user
        if hasattr(v, "name"):
            return v.name
        return v


class Tweet(BaseModel):

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int

    # tweet_data: str = Field(alias="content")
    tweet_data: str = Field(
        serialization_alias="content", validation_alias="tweet_data"
    )

    tweet_media_ids: list[GetMedia] = Field(alias="attachments")

    user_id: UserBase = Field(serialization_alias="author")
    # author: UserBase = Field(validation_alias="user")

    likes: list[Like]


class GetTweets(BaseModel):

    result: bool = True

    tweets: list[Tweet]

    model_config = ConfigDict(from_attributes=True)
