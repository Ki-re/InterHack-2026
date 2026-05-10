from pydantic import BaseModel


class AgentResponse(BaseModel):
    id: int
    name: str
    email: str
    zone: str  # north / east / south / canary / balearic
    managerId: int

    model_config = {"from_attributes": True}
