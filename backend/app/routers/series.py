from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from .. import models
from ..db import get_db
from ..schemas import SeriesInput, SeriesOut, series_out
from ..security import current_session

router = APIRouter(prefix="/api/series", tags=["series"])


def get_series_or_404(db: DbSession, series_id: int) -> models.Series:
    series = db.get(models.Series, series_id)
    if series is None:
        raise HTTPException(404, "Series not found")
    return series


def check_range(data: SeriesInput):
    if data.minValue >= data.maxValue:
        raise HTTPException(422, "minValue must be lower than maxValue")


@router.get("", response_model=list[SeriesOut])
def list_series(db: DbSession = Depends(get_db)):
    return [series_out(s) for s in db.scalars(select(models.Series).order_by(models.Series.id))]


@router.post("", status_code=201, response_model=SeriesOut, dependencies=[Depends(current_session)])
def create_series(data: SeriesInput, response: Response, db: DbSession = Depends(get_db)):
    check_range(data)
    series = models.Series(
        name=data.name, min_value=data.minValue, max_value=data.maxValue,
        color=data.color, icon=data.icon, unit=data.unit,
    )
    db.add(series)
    db.commit()
    response.headers["Location"] = f"/api/series/{series.id}"
    return series_out(series)


@router.get("/{series_id}", response_model=SeriesOut)
def get_series(series_id: int, db: DbSession = Depends(get_db)):
    return series_out(get_series_or_404(db, series_id))


@router.put("/{series_id}", response_model=SeriesOut, dependencies=[Depends(current_session)])
def update_series(series_id: int, data: SeriesInput, db: DbSession = Depends(get_db)):
    series = get_series_or_404(db, series_id)
    check_range(data)

    lowest, highest = db.execute(
        select(func.min(models.Measurement.value), func.max(models.Measurement.value))
        .where(models.Measurement.series_id == series_id)
    ).one()
    if lowest is not None and (lowest < data.minValue or highest > data.maxValue):
        raise HTTPException(409, "New range excludes measurements already stored in this series")

    series.name = data.name
    series.min_value = data.minValue
    series.max_value = data.maxValue
    series.color = data.color
    series.icon = data.icon
    series.unit = data.unit
    db.commit()
    return series_out(series)


@router.delete("/{series_id}", status_code=204, dependencies=[Depends(current_session)])
def delete_series(series_id: int, db: DbSession = Depends(get_db)):
    series = get_series_or_404(db, series_id)
    # Measurements and sensors are removed by ON DELETE CASCADE.
    db.delete(series)
    db.commit()
    return Response(status_code=204)
