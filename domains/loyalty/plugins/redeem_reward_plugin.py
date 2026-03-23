from typing import Optional
from pydantic import BaseModel, Field
from core.base_plugin import BasePlugin


class RedeemRequest(BaseModel):
    twitch_id: str = Field(min_length=1)
    reward_id: int = Field(gt=0)


class RedeemResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


class RedeemRewardPlugin(BasePlugin):
    """POST /loyalty/redeem — Spend points to redeem a reward."""

    def __init__(self, http, event_bus, db, logger):
        self.http = http
        self.bus = event_bus
        self.db = db
        self.logger = logger

    async def on_boot(self):
        self.http.add_endpoint(
            "/loyalty/redeem", "POST", self.execute,
            tags=["Loyalty"],
            request_model=RedeemRequest,
            response_model=RedeemResponse,
        )

    async def execute(self, data: dict, context=None):
        try:
            req = RedeemRequest(**data)

            async with self.db.transaction() as tx:
                reward = await tx.query_one(
                    "SELECT * FROM loyalty_rewards WHERE id=$1 AND enabled=1", [req.reward_id]
                )
                if not reward:
                    if context:
                        context.set_status(404)
                    return {"success": False, "error": "Reward not found or disabled"}

                viewer = await tx.query_one(
                    "SELECT points FROM viewer_points WHERE twitch_id=$1", [req.twitch_id]
                )
                if not viewer:
                    return {"success": False, "error": "Viewer not found"}

                if viewer["points"] < reward["cost"]:
                    return {"success": False, "error": f"Not enough points. Need {reward['cost']}, have {viewer['points']}"}

                await tx.execute(
                    """UPDATE viewer_points SET points=points-$1, updated_at=datetime('now')
                       WHERE twitch_id=$2""",
                    [reward["cost"], req.twitch_id],
                )
                await tx.execute(
                    "INSERT INTO points_transactions (twitch_id, amount, reason) VALUES ($1,$2,$3)",
                    [req.twitch_id, -reward["cost"], f"redeem:{reward['name']}"],
                )

            await self.bus.publish("loyalty.reward.redeemed", {
                "twitch_id": req.twitch_id,
                "reward_id": req.reward_id,
                "reward_name": reward["name"],
                "cost": reward["cost"],
            })
            return {"success": True, "data": {"reward": reward["name"], "cost": reward["cost"]}}
        except Exception as e:
            self.logger.error(f"[RedeemReward] {e}")
            return {"success": False, "error": str(e)}
