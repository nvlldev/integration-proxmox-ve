"""Constants for the Proxmox VE integration."""
from datetime import timedelta

DOMAIN = "proxmox_ve"
NAME = "Proxmox VE"
VERSION = "1.0.0"

# Configuration
CONF_HOST = "host"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_TOKEN_NAME = "token_name"
CONF_TOKEN_VALUE = "token_value"
CONF_PORT = "port"
CONF_VERIFY_SSL = "verify_ssl"
CONF_UPDATE_INTERVAL = "update_interval"

# Defaults
DEFAULT_PORT = 8006
DEFAULT_VERIFY_SSL = False
DEFAULT_UPDATE_INTERVAL = 30

# Update interval limits
MIN_UPDATE_INTERVAL = 10
MAX_UPDATE_INTERVAL = 300

# Data keys
DATA_COORDINATOR = "coordinator"
DATA_CLIENT = "client"

# Platforms
PLATFORMS = ["sensor", "button"]

# Update interval
UPDATE_INTERVAL = timedelta(seconds=DEFAULT_UPDATE_INTERVAL)