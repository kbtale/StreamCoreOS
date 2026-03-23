from typing import Optional
from pydantic import BaseModel
from core.base_plugin import BasePlugin


class RewardData(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    cost: int
    enabled: bool


class ListRewardsResponse(BaseModel):
    success: bool
    data: Optional[list[RewardData]] = None
    error: Optional[str] = None


class ListRewardsPlugin(BasePlugin):
    """GET /loyalty/rewards — List all rewards. Query param: enabled_only (default true)."""

    def __init__(self, http, db, logger):
        self.http = http
        self.db = db
        self.logger = logger

    async def on_boot(self):
        self.http.add_endpoint(
            "/loyalty/rewards", "GET", self.execute,
            tags=["Loyalty"],
            response_model=ListRewardsResponse,
        )

    async def execute(self, data: dict, context=None):
        try:
            enabled_only = data.get("enabled_only", "true").lower() != "false"
            sql = "SELECT id, name, description, cost, enabled FROM loyalty_rewards"
            params = []
            if enabled_only:
                sql += " WHERE enabled=1"
            sql += " ORDER BY cost ASC"
            rows = await self.db.query(sql, params or None)
            rewards = [{**r, "enabled": bool(r["enabled"])} for r in rows]
            return {"success": True, "data": rewards}
        except Exception as e:
            self.logger.error(f"[ListRewards] {e}")
            return {"success": False, "error": str(e)}
