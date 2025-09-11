import logging
import os

import yaml
from dotenv import load_dotenv

from config.models import RootConfig

_ = load_dotenv()

APP_CONFIG_FILE = os.path.join(os.path.dirname(__file__), os.pardir, "app-config.yaml")


logger = logging.getLogger(__name__)


def load_config(app_config_path: str) -> RootConfig:
    """
    Load the application configuration from a YAML file with environment variable expansion.

    Args:
        config_path (str): Path to the YAML configuration file.

    Returns:
        dict: The loaded configuration dictionary.

    Raises:
        FileNotFoundError: If the configuration file does not exist.
        yaml.YAMLError: If there's an issue parsing the YAML file.
        Exception: For any other unforeseen errors.
    """
    config: dict[str, str]

    try:
        # Resolve absolute path of the config file
        full_path_app_config = os.path.abspath(app_config_path)

        if not os.path.exists(full_path_app_config):
            raise FileNotFoundError(
                f"Application configuration file not found: {full_path_app_config}"
            )

        with open(full_path_app_config, "r") as f:
            raw_content = f.read()

        # Expand environment variables and load YAML content
        expanded_content = os.path.expandvars(raw_content)
        config = yaml.safe_load(expanded_content)

        # Ignore type checking for the AppConfig model because nested classes
        validated_config = RootConfig(**config)  # pyright: ignore[reportArgumentType]
        logger.info(
            "Configuration loaded and validated successfully: %s", full_path_app_config
        )
        return validated_config
    except FileNotFoundError as e:
        logger.error("Configuration file not found: %s", e)
        raise
    except yaml.YAMLError as e:
        logger.error("Error parsing YAML configuration: %s", e)
        raise
    except Exception as e:
        logger.exception("Unexpected error loading configuration: %s", e)
        raise


# Load the application configuration
try:
    root_config = load_config(APP_CONFIG_FILE)
    logger.info(f"Application configuration: {root_config.model_dump_json(indent=4)}")
except Exception as e:
    logger.critical("Failed to load application configuration: %s", e)
    raise e
