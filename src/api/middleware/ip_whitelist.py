"""IP whitelist middleware for enterprise VDI environments."""
import ipaddress
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """Middleware that restricts access to configured IP ranges.

    When ip_whitelist is empty or not configured, all IPs are allowed
    (backwards compatible default-open behaviour).

    Args:
        app: The ASGI application.
        whitelist: List of IP addresses and/or CIDR ranges as strings.
            E.g. ["10.0.0.0/8", "192.168.1.50"].
        trust_proxy: If True, use X-Forwarded-For header as client IP
            (first entry). Default False.
    """

    def __init__(self, app, whitelist: list = None, trust_proxy: bool = False):
        """Initialise the middleware, parsing whitelist entries into network objects.

        Args:
            app: The ASGI application to wrap.
            whitelist: List of IP addresses and/or CIDR ranges as strings.
                Invalid entries are logged as warnings and skipped.
            trust_proxy: If True, use X-Forwarded-For header as client IP.
        """
        super().__init__(app)
        self.trust_proxy = trust_proxy
        self._networks = []
        for entry in (whitelist or []):
            try:
                self._networks.append(ipaddress.ip_network(entry, strict=False))
            except ValueError:
                logger.warning("Invalid IP whitelist entry ignored: %s", entry)

    def _is_allowed(self, client_ip: str) -> bool:
        """Return True if client_ip is in the whitelist (or whitelist is empty).

        Args:
            client_ip: The IP address string to check.

        Returns:
            True if the IP is permitted or no whitelist is configured;
            False if the IP is blocked.
        """
        if not self._networks:
            return True
        try:
            addr = ipaddress.ip_address(client_ip)
        except ValueError:
            return False
        return any(addr in net for net in self._networks)

    async def dispatch(self, request: Request, call_next):
        """Check client IP against the whitelist before forwarding the request.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware/route handler in the chain.

        Returns:
            A 403 JSONResponse if the client IP is not permitted, otherwise
            the response from the downstream handler.
        """
        if self.trust_proxy:
            forwarded = request.headers.get("X-Forwarded-For", "")
            client_ip = forwarded.split(",")[0].strip() if forwarded else (
                request.client.host if request.client else ""
            )
        else:
            client_ip = request.client.host if request.client else ""

        if not self._is_allowed(client_ip):
            logger.warning("Blocked request from %s — not in IP whitelist", client_ip)
            return JSONResponse(
                status_code=403,
                content={"error": "Forbidden", "detail": "Your IP address is not permitted."},
            )
        return await call_next(request)
