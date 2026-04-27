"""Constants for ForsyningOnline integration."""

from datetime import timedelta

DOMAIN = "forsyningonline"
DEFAULT_NAME = "ForsyningOnline"

# Scan intervals
SCAN_INTERVAL_DAILY = timedelta(hours=1)

# Attributes
ATTR_LOCATION = "location"
ATTR_UTILITY_NAME = "utility_name"

# History import options (days to import on first run)
HISTORY_DAYS_OPTIONS = {
    "7": 7,
    "30": 30,
    "90": 90,
    "180": 180,
    "365": 365,
    "all": 0,  # 0 = all available data
}
DEFAULT_HISTORY_DAYS = "30"

# Debug mode
ATTR_DEBUG_MODE = "debug_mode"
DEBUG_MODE_DEFAULT = False
