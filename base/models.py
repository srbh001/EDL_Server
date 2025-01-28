from pydantic import BaseModel


class User(BaseModel):
    username: str
    email: str
    full_name: str = None
    disabled: bool = False


class Board(BodeModel):
    name: str
    description: str = None
    owner: User
