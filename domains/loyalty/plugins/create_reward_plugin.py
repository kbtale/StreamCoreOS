from typing import Optional
from pydantic import BaseModel, Field
from core.base_plugin import BasePlugin


class CreateRewardRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=300)
    cost: int = Field(gt=0)


class RewardData(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    cost: int
    enabled: bool


class CreateRewardResponse(BaseModel):
    success: bool
    data: Optional[RewardData] = None
    error: Optional[str] = None


class CreateRewardPlugin(BasePlugin):
    """POST /loyalty/rewards — Create a new redeemable reward."""

    def __init__(self, http, db, logger):
        self.http = http
        self.db = db
        self.logger = logger

    async def on_boot(self):
        self.http.add_endpoint(
            "/loyalty/rewards", "POST", self.execute,
            tags=["Loyalty"],
            request_model=CreateRewardRequest,
            response_model=CreateRewardResponse,
        )

    async def execute(self, data: dict, context=None):
        try:
            req = CreateRewardRequest(**data)
            reward_id = await self.db.execute(
                "INSERT INTO loyalty_rewards (name, description, cost) VALUES ($1,$2,$3) RETURNING id",
                [req.name, req.description, req.cost],
            )
            return {"success": True, "data": {
                "id": reward_id, "name": req.name,
                "description": req.description, "cost": req.cost, "enabled": True,
            }}
        except Exception as e:
            self.logger.error(f"[CreateReward] {e}")
            return {"success": False, "error": str(e)}
