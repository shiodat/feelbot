from pydantic import BaseModel


class SlackBase(BaseModel):
    token: str


class SlackCommand(SlackBase):
    command: str
    text: str
    response_url: str
    trigger_id: str
    user_id: str
    user_name: str
    team_id: str
    channel_id: str
