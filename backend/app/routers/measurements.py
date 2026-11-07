from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import AwareDatetime
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from .. import models
from ..db import get_db
from ..problems import logger
from ..schemas import MeasurementInput, MeasurementOut, measurement_out
from ..security import current_sensor

router = APIRouter(prefix="/api/measurements", tags=["measurements"])

MAX_CLOCK_SKEW = timedelta(minutes=5)


def parse_series_ids(series: str) -> list[int]:
    try:
        return [int(part) for part in series.split(",") if part.strip()]
    except ValueError:
        raise HTTPException(400, "Parameter 'series' must be a comma-separated list of ids")


@router.get("", response_model=list[MeasurementOut])
def list_measurements(
    series: str | None = None,
    from_: AwareDatetime | None = Query(default=None, alias="from"),
    to: AwareDatetime | None = None,
    sort: Literal["timestamp", "-timestamp"] = "timestamp",
    limit: int = Query(default=1000, ge=1, le=10000),
    db: DbSession = Depends(get_db),
):
    query = select(models.Measurement)
    if series is not None:
        query = query.where(models.Measurement.series_id.in_(parse_series_ids(series)))
    if from_ is not None:
        query = query.where(models.Measurement.timestamp >= from_)
    if to is not None:
        query = query.where(models.Measurement.timestamp <= to)
    if sort == "timestamp":
        query = query.order_by(models.Measurement.timestamp, models.Measurement.id)
    else:
        query = query.order_by(models.Measurement.timestamp.desc(), models.Measurement.id.desc())
    return [measurement_out(m) for m in db.scalars(query.limit(limit))]


@router.post("", status_code=201, response_model=MeasurementOut)
def add_measurement(
    data: MeasurementInput,
    response: Response,
    sensor: models.Sensor = Depends(current_sensor),
    db: DbSession = Depends(get_db),
):
    series = db.get(models.Series, sensor.series_id)
    now = datetime.now(timezone.utc)
    timestamp = data.timestamp or now

    if not series.min_value <= data.value <= series.max_value:
        logger.warning(
            "Rejected measurement from sensor %s: value %s outside [%s, %s] of series %s",
            sensor.id, data.value, series.min_value, series.max_value, series.id,
        )
        raise HTTPException(
            422, f"Value {data.value} is outside the allowed range [{series.min_value}, {series.max_value}]"
        )
    if timestamp > now + MAX_CLOCK_SKEW:
        logger.warning("Rejected measurement from sensor %s: timestamp %s is in the future", sensor.id, timestamp)
        raise HTTPException(422, "Timestamp is more than 5 minutes in the future")

    measurement = models.Measurement(series_id=series.id, sensor_id=sensor.id, value=data.value, timestamp=timestamp)
    db.add(measurement)
    db.commit()
    response.headers["Location"] = f"/api/measurements/{measurement.id}"
    return measurement_out(measurement)


@router.get("/{measurement_id}", response_model=MeasurementOut)
def get_measurement(measurement_id: int, db: DbSession = Depends(get_db)):
    measurement = db.get(models.Measurement, measurement_id)
    if measurement is None:
        raise HTTPException(404, "Measurement not found")
    return measurement_out(measurement)
