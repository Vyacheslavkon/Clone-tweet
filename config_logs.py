dict_config = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'formatter': {
            'format':  '%(name)s | %(levelname)s | %(message)s | %(pathname)s | %(lineno)d'
        }
    },
    'handlers': {
        'root_handler': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'formatter': 'formatter'
        },
        'hand_routes_log': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'formatter': 'formatter'
        },
        'file' : {
            'class': 'logging.FileHandler',
            'level': 'DEBUG',
            'formatter': 'formatter',
            'filename': 'routes_logs.log',
            'mode': 'a'
        }

    },

    'loggers': {
        "": {
            'level': 'DEBUG',
            'handlers': ['root_handler']
        },
        'routes_log': {
            'level': 'INFO',
            'handlers': ['hand_routes_log', 'file']
        }

    }
}