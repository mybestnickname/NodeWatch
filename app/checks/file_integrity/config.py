from pydantic import BaseModel, Field


class Config(BaseModel):
    """High-level options for the file-integrity check.

    The detailed afick ruleset (which paths to watch, which attributes to
    compare) lives in afick's own configuration file. Here we only keep the
    high-level knobs that the service needs.
    """

    use_sudo: bool = Field(True, description="Run afick via sudo (required when watching root-owned paths)")
    # Optional comma-separated list of afick aliases to restrict the scan to a
    # subset of the configured files. Empty means "use the full afick config".
    aliases: str = Field("", description="Restrict the scan to these afick aliases")
