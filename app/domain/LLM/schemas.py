from pydantic import BaseModel

class GetLLMMessageRequest(BaseModel):
    character_id: int
    episode_id: int
    user_message: str

class GetLLMMessageResponse(BaseModel):
    task_id: str

class GetLLMFeedbackResponse(BaseModel):
    task_id: str

class GetLLMResultResponse(BaseModel):
    result: str
    name: str
    room_id: int

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    result: str = None