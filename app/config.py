"""Application configuration models and loader.

Configuration is read from a JSON file whose path is taken from the
``NODEWATCH_CONFIG`` environment variable (falling back to ``config.json`` and
then to the bundled ``config.example.json``). Using the standard library only
keeps the runtime dependency-free.
"""
import json
import logging
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.checks.file_integrity.config import Config as FileIntegrityConfig
from app.checks.fs_free_space.config import Config as FsFreeSpaceConfig

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATHS = ("config.json", "config.example.json")


class OneOfSetMixin(BaseModel):
    """Validate that exactly one field of the model is set (not ``None``)."""

    @model_validator(mode="before")
    @classmethod
    def check_only_one_field_defined(cls, values: dict[str, Any]) -> dict[str, Any]:
        not_none_fields = [k for k, v in values.items() if v is not None]
        if len(not_none_fields) != 1:
            raise ValueError(f"Exactly one check config must be set, got: {not_none_fields}")
        return values


class CheckConfig(OneOfSetMixin):
    """Typed configuration for a single check.

    Each field name MUST match the corresponding ``Check.name`` so that
    ``create_app`` can resolve a check's config by convention.
    """

    file_integrity: FileIntegrityConfig | None = None
    fs_free_space: FsFreeSpaceConfig | None = None
    # TODO: tampering_control: Optional[TamperingControlConfig] = None


class Check(BaseModel):
    name: str  # check name, used to call it via the agent API
    config: CheckConfig
    timeout: int  # per-run timeout, seconds
    interval: int = 0  # how often to run automatically; 0 means on-demand only
    # Wait a random number of seconds in [0, jitter] before the first scheduled
    # run to avoid a thundering herd across many hosts (ignored for on-demand runs).
    jitter: int = 15


class CTS(BaseModel):
    polling_interval: int = 2
    device: str = "/dev/ttyUSB0"
    persistence_interval: int = Field(10, description="How often to persist readings to the DB")


class Services(BaseModel):
    cts: CTS | None = None


class State(BaseModel):
    path: str  # sqlite db path


class Config(BaseModel):
    state: State | None = None
    # Pre-configured checks that can be triggered through the API.
    checks: list[Check] = Field(default_factory=list)
    services: Services | None = None


def load_config(path: str | None = None) -> Config:
    """Load configuration from JSON, returning an empty config if none is found."""
    candidates = [path] if path else [os.getenv("NODEWATCH_CONFIG"), *DEFAULT_CONFIG_PATHS]
    for candidate in filter(None, candidates):
        config_path = Path(candidate)
        if not config_path.is_file():
            continue
        logger.info("Loading configuration from %s", config_path)
        data = json.loads(config_path.read_text(encoding="utf-8"))
        return Config.model_validate(data)

    logger.warning("No configuration file found; starting with an empty config.")
    return Config()
