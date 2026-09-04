from app.extensions import db
from app.models.campus import House, HouseScore


def award_house_points(house_id: int, points: int, reason: str,
                       category: str = None, source_type: str = "manual",
                       source_id: int = None) -> HouseScore:
    """
    Award points to a house and update the denormalized running total.
    All point changes flow through this function so the total stays consistent.
    """
    if points == 0:
        raise ValueError("Points must be non-zero")

    house = db.session.get(House, house_id)
    if not house:
        raise ValueError("House not found")

    score = HouseScore(
        house_id=house_id,
        points=points,
        reason=reason,
        category=category,
        source_type=source_type,
        source_id=source_id,
    )
    db.session.add(score)

    house.house_points = (house.house_points or 0) + points
    db.session.commit()
    return score


def recalculate_house_points(house_id: int) -> int:
    """Recompute the denormalized total from HouseScore rows. Use if totals drift."""
    total = db.session.query(db.func.coalesce(db.func.sum(HouseScore.points), 0))\
        .filter(HouseScore.house_id == house_id).scalar()
    house = db.session.get(House, house_id)
    house.house_points = total
    db.session.commit()
    return total


def house_of_the_week() -> House | None:
    """
    House with the most points awarded in the last 7 days.
    Returns None if no points were awarded this week.
    """
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import func

    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    rows = db.session.query(
        HouseScore.house_id,
        func.sum(HouseScore.points).label("week_points"),
    ).filter(
        HouseScore.created_at >= cutoff,
        HouseScore.points > 0,
    ).group_by(HouseScore.house_id)\
     .order_by(db.text("week_points DESC"))\
     .first()

    if not rows:
        return None
    return db.session.get(House, rows.house_id)