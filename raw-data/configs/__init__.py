import logging
import os
import re
from typing import Any

import yaml
from dotenv import load_dotenv
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from pydantic import BaseModel

from .mongo_config import MongoConfig

# HACK: This service needs to initialize the logging instrumentor before any logging is done.
# Still not sure why this service has to do this.
LoggingInstrumentor().instrument(set_logging_format=True)

_ = load_dotenv()


def get_logger(name: str):
    return logging.getLogger(name)


logger = get_logger("config")


def expand_env_vars(obj: Any) -> Any:
    """
    Recursively expand environment variables in configuration values.
    """
    if isinstance(obj, dict):
        return {k: expand_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [expand_env_vars(i) for i in obj]
    elif isinstance(obj, str):
        return re.sub(
            r"\$\{([^}^{]+)\}",
            lambda m: os.getenv(m.group(1), m.group(0)),
            obj,
        )
    else:
        return obj


class AppConfig(BaseModel):
    mongo: MongoConfig


def load_config(config_path: str = "app-config.yaml") -> AppConfig:
    """
    Load YAML config file and return as AppConfig, with env var expansion.

    Args:
        config_path: Path to the configuration file

    Returns:
        AppConfig: Loaded configuration object

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If config file is invalid YAML
        ValidationError: If config doesn't match expected schema
    """
    config_file = config_path
    if not os.path.isabs(config_file):
        # Try to find config file relative to current directory
        config_file = os.path.join(os.path.dirname(__file__), "..", config_path)
        config_file = os.path.abspath(config_file)

    logger.info(f"Loading configuration from: {config_file}")

    try:
        with open(config_file, "r") as f:
            config = yaml.safe_load(f)

        # Expand environment variables
        config = expand_env_vars(config)

        # Validate and return config
        return AppConfig(**config)

    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_file}")
        raise
    except yaml.YAMLError as e:
        logger.error(f"Invalid YAML in configuration file: {e}")
        raise
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        raise


# Load configuration on module import
try:
    _config = load_config()
    logger.info("Configuration loaded successfully")
except Exception as e:
    logger.error(f"Failed to load configuration: {e}")
    _config = None

mongo_config = _config.mongo if _config else None
