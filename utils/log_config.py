import sys
from utils.Settings import BASE_DIR, ConfigManager


LogConfig = dict(  # no cov
    version=1,
    disable_existing_loggers=False,
    loggers={
        "sanic.root": {"level": "INFO", "handlers": ["console"]},
        "sanic.error": {
            "level": "INFO",
            "handlers": ["error_file", "error_console"],
            "propagate": True,
            "qualname": "sanic.error",
        },
        "sanic.access": {
            "level": "INFO",
            "handlers": ["access_file", "access_console"],
            "propagate": True,
            "qualname": "sanic.access",
        },
        "sanic.server": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": True,
            "qualname": "sanic.server",
        },
    },
    handlers={
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "generic",
            "stream": sys.stdout,
        },
        "error_console": {
            "class": "logging.StreamHandler",
            "formatter": "generic",
            "stream": sys.stderr,
        },
        "access_console": {
            "class": "logging.StreamHandler",
            "formatter": "access",
            "stream": sys.stdout,
        },
        "error_file": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "formatter": "generic",
            "filename": str(BASE_DIR) + ConfigManager().get_config('LogSetting', 'log_dir') + "/error.log",
            "when": ConfigManager().get_config('LogSetting', 'rotate_time'),
            "backupCount": int(ConfigManager().get_config('LogSetting', 'backup_count')),
            "encoding": "utf-8"
        },
        "access_file": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "formatter": "access",
            "filename": str(BASE_DIR) + ConfigManager().get_config('LogSetting', 'log_dir') + '/access.log',
            "when": ConfigManager().get_config('LogSetting', 'rotate_time'),
            "backupCount": int(ConfigManager().get_config('LogSetting', 'backup_count')),
            "encoding": "utf-8"
        },
    },
    formatters={
        "generic": {
            "format": "%(asctime)s [%(process)d] [%(levelname)s] %(message)s",
            "datefmt": "[%Y-%m-%d %H:%M:%S %z]",
            "class": "logging.Formatter",
        },
        "access": {
            "format": "%(asctime)s - (%(name)s)[%(levelname)s][%(host)s]: "
                      + "%(request)s %(message)s %(status)d",
            "datefmt": "[%Y-%m-%d %H:%M:%S %z]",
            "class": "logging.Formatter",
        },
    },
)
