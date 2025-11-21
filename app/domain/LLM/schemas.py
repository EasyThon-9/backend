from pydantic import BaseModel

class GetLLMMessageRequest(BaseModel):
    character_id: int
    episode_id: int
    user_message: str

class GetLLMMessageResponse(BaseModel):
    task_id: str

# 피드백이나 결과 관련 스키마가 있다면 여기에 추가
class GetLLMFeedbackRequest(BaseModel):
    pass