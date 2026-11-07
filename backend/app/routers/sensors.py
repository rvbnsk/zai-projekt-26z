from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from .. import models
from ..db import get_db
from ..schemas import SensorCreated, SensorInput, SensorOut, sensor_out
from ..security import current_session, new_secret, sha256

router = APIRouter(prefix="/api/sensors", tags=["sensors"], dependencies=[Depends(current_session)])


def get_sensor_or_404(db: DbSession, sensor_id: int) -> models.Sensor:
    sensor = db.get(models.Sensor, sensor_id)
    if sensor is None:
        raise HTTPException(404, "Sensor not found")
    return sensor


@router.get("", response_model=list[SensorOut])
def list_sensors(db: DbSession = Depends(get_db)):
    return [sensor_out(s) for s in db.scalars(select(models.Sensor).order_by(models.Sensor.id))]


@router.post("", status_code=201, response_model=SensorCreated)
def register_sensor(data: SensorInput, response: Response, db: DbSession = Depends(get_db)):
    if db.get(models.Series, data.seriesId) is None:
        raise HTTPException(422, "Series does not exist")

    # The plain key is returned only once; the database keeps its SHA-256 hash.
    api_key = new_secret()
    sensor = models.Sensor(
        name=data.name, series_id=data.seriesId, api_key_hash=sha256(api_key),
        created_at=datetime.now(timezone.utc),
    )
    db.add(sensor)
    db.commit()
    response.headers["Location"] = f"/api/sensors/{sensor.id}"
    return SensorCreated(**sensor_out(sensor).model_dump(), apiKey=api_key)


@router.get("/{sensor_id}", response_model=SensorOut)
def get_sensor(sensor_id: int, db: DbSession = Depends(get_db)):
    return sensor_out(get_sensor_or_404(db, sensor_id))


@router.delete("/{sensor_id}", status_code=204)
def unregister_sensor(sensor_id: int, db: DbSession = Depends(get_db)):
    sensor = get_sensor_or_404(db, sensor_id)
    # Collected measurements stay; their sensor_id becomes NULL (ON DELETE SET NULL).
    db.delete(sensor)
    db.commit()
    return Response(status_code=204)
