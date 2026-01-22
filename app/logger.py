import logging
import sys
import os
from logging.handlers import RotatingFileHandler
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

# ====================================================
# LOGIN LOGGER - File log khusus untuk login events
# ====================================================

# Create logs directory if not exists
logs_dir = "logs"
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

# Login log format: lebih detail dan mudah di-parse
login_log_format = "%(asctime)s | %(levelname)-8s | %(message)s"
login_log_date_format = "%Y-%m-%d %H:%M:%S"

# Create login logger
login_logger = logging.getLogger("wireguard-backend-login")
login_logger.setLevel(logging.DEBUG)  # Always log all login events

# Create rotating file handler untuk login log (max 10MB, keep 5 files)
login_file_handler = RotatingFileHandler(
    filename=os.path.join(logs_dir, "login.log"),
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=5,
    encoding="utf-8"
)
login_file_handler.setLevel(logging.DEBUG)

# Set format untuk login logger
login_formatter = logging.Formatter(login_log_format, datefmt=login_log_date_format)
login_file_handler.setFormatter(login_formatter)

# Add handler ke login logger (hanya file handler, tidak ke console)
login_logger.addHandler(login_file_handler)
login_logger.propagate = False  # Jangan propagate ke root logger (hindari duplikasi)