import dataclasses
from pathlib import Path


@dataclasses.dataclass
class Config:
    id_rsa: str
    storage: Path
    gitea_token: str
    gitea_host: str
    gitea_secret_key: str
