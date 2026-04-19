import os
import yaml
import logging
from jinja2 import Template
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


class TemplateConfig(BaseModel):
    """Configuration for the resume template source and paths."""

    source: str
    filename: str
    local_path: str


class PathsConfig(BaseModel):
    """Directory structure configuration."""

    configs: str
    resumes: str
    output: str


class AppConfig(BaseModel):
    """Root configuration object."""

    model_config = ConfigDict(extra="allow")
    template: TemplateConfig
    paths: PathsConfig


def load_full_config(path: str = "config.yaml") -> AppConfig:
    """
    Loads YAML config, renders Jinja2 environment variables,
    and validates the result with Pydantic.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        # Pre-process YAML with Jinja2 to support {{ env.VAR }}
        content = f.read()
        template = Template(content)
        rendered = template.render(env=os.environ)

        raw_data = yaml.safe_load(rendered)
        # Validate data against Pydantic schemas
        return AppConfig(**raw_data)
