"""AdaptisHome для Home Assistant: сталі."""
from datetime import timedelta

DOMAIN = "adaptishome"
VERSION = "0.2.0"                            # = manifest.json; у посиланні на картку, щоб браузер не брав стару з кешу
CARD_URL = "/adaptishome/adaptishome-card.js"
CONF_HUB = "hub"
CONF_OBJECTS = "objects"
SCAN_INTERVAL = timedelta(seconds=30)        # пристрій шле стан раз на 30 с, частіше немає сенсу
EVENT = "adaptishome_event"                  # подія на шині HA: перемикання, повернення, перезавантаження, конфігурація
