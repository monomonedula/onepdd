from pathlib import Path

import yaml
from fastapi import FastAPI
from starlette.templating import Jinja2Templates

from onepdd.config import Config
from onepdd.hooks.gitea import HookGitea


def load_config() -> Config:
    conf = yaml.safe_load("config.yaml")
    return Config(
        id_rsa=conf["id_rsa"],
        storage=conf["storage_dir"],
        gitea_token=conf["gitea"]["token"],
        gitea_host=conf["gitea"]["host"],
        gitea_secret_key=conf["gitea"]["secret_key"],
    )


def make_app():
    config = load_config()
    templates = Jinja2Templates((Path(__file__).parent.parent / "templates").resolve())
    api = FastAPI()
    api.add_route("/hook/gitea", HookGitea(config=config, templates=templates).handle)

    return api


app = make_app()
