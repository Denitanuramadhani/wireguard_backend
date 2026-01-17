import logging
import sys
import os
from app.config import ENVIRONMENT, LOG_LEVEL

# Determine log level from config
log_level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)

# Configure logging format
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
date_format = "%Y-%m-%d %H:%M:%S"

# Configure handlers
handlers = []

# In production or Docker, log to stdout/stderr for container logging
if ENVIRONMENT == "production" or os.getenv("DOCKER_CONTAINER"):
    # Log to stdout for info and below, stderr for warnings and above
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.DEBUG)
    stdout_handler.addFilter(lambda record: record.levelno <= logging.INFO)
    
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.WARNING)
    
    handlers = [stdout_handler, stderr_handler]
else:
    # In development, log to file
    file_handler = logging.FileHandler("backend.log")
    handlers = [file_handler]

# Configure root logger
logging.basicConfig(
    level=log_level,
    format=log_format,
    datefmt=date_format,
    handlers=handlers
)

# Create logger for application
logger = logging.getLogger("wireguard-backend")