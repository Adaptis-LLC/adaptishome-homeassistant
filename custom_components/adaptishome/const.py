"""AdaptisHome для Home Assistant: сталі."""
from datetime import timedelta

DOMAIN = "adaptishome"
CONF_HUB = "hub"
CONF_OBJECTS = "objects"
SCAN_INTERVAL = timedelta(seconds=30)        # пристрій шле стан раз на 30 с, частіше немає сенсу
EVENT = "adaptishome_event"                  # подія на шині HA: перемикання, повернення, перезавантаження, конфігурація
