from pydantic import BaseModel


class Config(BaseModel):
    """TODO"""
    # high-level options to run afick
    # any details must be skipped
    # afick config must be provided separately !
    # add some params to run afick on subset of configured files
