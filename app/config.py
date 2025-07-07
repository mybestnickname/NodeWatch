from typing import Any, List, Optional

from pydantic import BaseModel, Field, model_validator


class OneOfSetMixin(BaseModel):
    """Проверить, что в модели ровно одно поле не None."""
    @model_validator(mode="before")
    @classmethod
    def check_only_one_field_defined(cls, values: dict[str, Any]) -> dict[str, Any]:
        not_none_fields = [k for k, v in values.items() if v is not None]
        if len(not_none_fields) != 1:
            raise ValueError(f"Exactly one field should be set, got {not_none_fields}")
        return values


class CheckConfig(OneOfSetMixin):
    pass
    # TODO:
    # file_integrity: Optional[CheckFileIntegrityConfig]
    # tampering_control: Optional[CheckTamperingControlConfig]
    # fs_free_space: Optional[CheckFsFreeSpaceConfig]
    # device: Optional[CheckDeviceConfig]


class Check(BaseModel):
    name: str  # name to call via agent api
    config: CheckConfig
    timeout: int  # timeout for check run, seconds
    interval: int = 0  # interval how often to run check automatically, 0 - run only on demand
    # wait random number of seconds in [0, jitter] interval before run first check to avoid overload
    # (only for scheduled run, ignored while calling on demand)
    jitter: int = 15


class CTS(BaseModel):
    polling_interval: int = 2
    device: str = "/dev/ttyUSB0"
    persistence_interval: int = Field(10, description="Периодичность записи в СУБД")


class Services(BaseModel):
    cts: Optional[CTS]


class State(BaseModel):
    path: str  # sqlite db path


class Config(BaseModel):
    state: Optional[State]
    # список преднастроенных проверок, которые можно запускать через api
    checks: Optional[List[Check]]
    services: Optional[Services]
