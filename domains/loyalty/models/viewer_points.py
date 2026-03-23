from typing import Optional
from pydantic import BaseModel


class ViewerPointsEntity(BaseModel):
    """DB mirror of the viewer_points table."""
    id: int
    twitch_id: str
    display_name: str
    points: int
    total_earned: int
    updated_at: str


class PointsTransactionEntity(BaseModel):
    """DB mirror of the points_transactions table."""
    id: int
    twitch_id: str
    amount: int
    reason: str
    created_at: str


class LoyaltyRewardEntity(BaseModel):
    """DB mirror of the loyalty_rewards table."""
    id: int
    name: str
    description: Optional[str]
    cost: int
    enabled: int
    created_at: str
