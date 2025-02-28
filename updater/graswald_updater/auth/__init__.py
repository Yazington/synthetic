try:
    from .https import HTTPS
except ImportError:
    HTTPS = None

try:
    from .aws import AWS
except ImportError:
    aws = None

from .auth import Authentication
