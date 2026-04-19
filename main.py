import os
import logging
from dotenv import load_dotenv

# Local imports
from src.config import load_full_config
from loaders.gdrive_loader import GDriveConnector
from loaders.onedrive_loader import OneDriveConnector
from src.generator import CVGenerator

# Logging configuration
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    # 1. Initialization (Load .env FIRST, then YAML config)
    load_dotenv()
    try:
        config = load_full_config("config.yaml")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        return

    # Simplified access via Pydantic object
    tpl_cfg = config.template
    source = tpl_cfg.source

    # 2. Template Synchronization
    if source == "gdrive":
        logger.info(f"🔄 Syncing from GDrive: {tpl_cfg.filename}")
        try:
            loader = GDriveConnector()
            loader.download_file_by_name(tpl_cfg.filename, tpl_cfg.local_path)
        except Exception as e:
            logger.error(f"GDrive error: {e}. Falling back to local cache.")

    elif source == "onedrive":
        logger.info(f"🔄 Syncing from OneDrive: {tpl_cfg.filename}")
        try:
            loader = OneDriveConnector()
            loader.download_file_by_name(tpl_cfg.filename, tpl_cfg.local_path)
        except Exception as e:
            logger.error(f"OneDrive error: {e}. Falling back to local cache.")

    elif source == "local":
        logger.info("📁 Using local template mode.")

    # 3. Resume Generation
    if not os.path.exists(tpl_cfg.local_path):
        logger.error(f"Template not found at {tpl_cfg.local_path}. Aborting.")
        return

    # Pass the config dictionary to the generator
    # (Using model_dump() ensures compatibility with dict-based generators)
    try:
        generator = CVGenerator(config.model_dump())
        generator.generate()
        logger.info("✨ Generation completed successfully.")
    except Exception as e:
        logger.error(f"Generation failed: {e}")


if __name__ == "__main__":
    main()
