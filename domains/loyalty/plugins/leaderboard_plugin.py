from typing import Optional
from pydantic import BaseModel, Field
from core.base_plugin import BasePlugin


class LeaderboardEntry(BaseModel):
    rank: int
    twitch_id: str
    display_name: str
    points: int
    total_earned: int


class LeaderboardResponse(BaseModel):
    success: bool
    data: Optional[list[LeaderboardEntry]] = None
    error: Optional[str] = None


class LeaderboardPlugin(BasePlugin):
    """GET /loyalty/leaderboard — Top viewers by current points. Query param: limit (default 10)."""

    def __init__(self, http, db, logger):
        self.http = http
        self.db = db
        self.logger = logger

    async def on_boot(self):
        self.http.add_endpoint(
            "/loyalty/leaderboard", "GET", self.execute,
            tags=["Loyalty"],
            response_model=LeaderboardResponse,
        )

    async def execute(self, data: dict, context=None):
        try:
            limit = max(1, min(int(data.get("limit", 10)), 100))
            rows = await self.db.query(
                """SELECT twitch_id, display_name, points, total_earned
                   FROM viewer_points ORDER BY points DESC LIMIT $1""",
                [limit],
            )
            leaderboard = [
                {"rank": i + 1, **row} for i, row in enumerate(rows)
            ]
            return {"success": True, "data": leaderboard}
        except Exception as e:
            self.logger.error(f"[Leaderboard] {e}")
            return {"success": False, "error": str(e)}
