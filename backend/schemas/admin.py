from pydantic import BaseModel, Field
from typing import Literal


class PostReview(BaseModel):
    status: Literal[1, 2]


class CommentReview(BaseModel):
    status: Literal[1, 2]
