from pydantic import AwareDatetime, BaseModel, Field

from . import models


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    accessToken: str
    tokenType: str = "Bearer"
    expiresIn: int


class PasswordChange(BaseModel):
    currentPassword: str
    newPassword: str = Field(min_length=8)


class SeriesInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    minValue: float
    maxValue: float
    color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    icon: str | None = Field(default=None, max_length=50)
    unit: str | None = Field(default=None, max_length=20)


class SeriesOut(SeriesInput):
    id: int


class MeasurementInput(BaseModel):
    value: float
    timestamp: AwareDatetime | None = None


class MeasurementOut(BaseModel):
    id: int
    seriesId: int
    sensorId: int | None
    value: float
    timestamp: AwareDatetime


class SensorInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    seriesId: int


class SensorOut(BaseModel):
    id: int
    name: str
    seriesId: int
    createdAt: AwareDatetime


class SensorCreated(SensorOut):
    apiKey: str


def series_out(s: models.Series) -> SeriesOut:
    return SeriesOut(
        id=s.id, name=s.name, minValue=s.min_value, maxValue=s.max_value,
        color=s.color, icon=s.icon, unit=s.unit,
    )


def measurement_out(m: models.Measurement) -> MeasurementOut:
    return MeasurementOut(
        id=m.id, seriesId=m.series_id, sensorId=m.sensor_id, value=m.value, timestamp=m.timestamp,
    )


def sensor_out(s: models.Sensor) -> SensorOut:
    return SensorOut(id=s.id, name=s.name, seriesId=s.series_id, createdAt=s.created_at)
