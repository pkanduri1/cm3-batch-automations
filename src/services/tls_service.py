"""TLS certificate resolution service with pluggable strategy support.

Implements a strategy pattern so that switching TLS mode requires only a
``config/ui.yml`` change — no code modifications needed.

Supported strategies
--------------------
- ``manual``       — use pre-existing cert/key files at configured paths
- ``self_signed``  — generate a self-signed cert at server startup
- ``enterprise_ca``— fetch cert/key from an enterprise CA REST API

Usage::

    from src.services.tls_service import resolve_tls

    tls_result = resolve_tls(ui_yml_tls_section)
    if tls_result:
        cert_path, key_path = tls_result
        uvicorn.run(..., ssl_certfile=str(cert_path), ssl_keyfile=str(key_path))
"""
import datetime
import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path

logger = logging.getLogger(__name__)


class TLSStrategy(ABC):
    """Abstract base for TLS certificate resolution strategies.

    Subclasses must implement :meth:`resolve` and return a
    ``(cert_path, key_path)`` tuple.
    """

    @abstractmethod
    def resolve(self, config: dict) -> tuple:
        """Resolve cert and key paths, generating or fetching as needed.

        Args:
            config: The ``tls`` section dict from ``ui.yml``.

        Returns:
            Tuple of ``(cert_path, key_path)`` as :class:`pathlib.Path` objects.

        Raises:
            RuntimeError: If the cert cannot be resolved.
        """


class ManualTLSStrategy(TLSStrategy):
    """Use pre-existing cert/key files at paths specified in ``ui.yml``.

    The paths must exist on disk before the server starts.  No generation
    or network calls are made.

    Required config keys:
        ``cert_path`` — absolute path to the PEM certificate.
        ``key_path``  — absolute path to the PEM private key.
    """

    def resolve(self, config: dict) -> tuple:
        """Return the configured cert/key paths after verifying they exist.

        Args:
            config: The ``tls`` section dict from ``ui.yml``.

        Returns:
            ``(cert_path, key_path)`` as :class:`pathlib.Path` objects.

        Raises:
            RuntimeError: If either file does not exist.
        """
        cert = Path(config["cert_path"])
        key = Path(config["key_path"])
        if not cert.exists():
            raise RuntimeError(f"TLS cert not found: {cert}")
        if not key.exists():
            raise RuntimeError(f"TLS key not found: {key}")
        return cert, key


class SelfSignedTLSStrategy(TLSStrategy):
    """Generate a self-signed TLS certificate at server startup.

    Requires the ``cryptography`` package (``pip install cryptography``).
    The certificate is written to the configured paths and is valid for
    365 days.  The ``cn`` and ``san`` config keys control the certificate
    subject / SANs.

    Optional config keys:
        ``cert_path`` — destination PEM cert file (default:
            ``/tmp/valdo-tls/cert.pem``).
        ``key_path``  — destination PEM key file (default:
            ``/tmp/valdo-tls/key.pem``).
        ``cn``        — common name (default: ``localhost``).
        ``san``       — list of DNS names or IP addresses for the SAN
            extension (default: ``[cn]``).
    """

    def resolve(self, config: dict) -> tuple:
        """Generate a self-signed cert/key pair and return their paths.

        Args:
            config: The ``tls`` section dict from ``ui.yml``.

        Returns:
            ``(cert_path, key_path)`` as :class:`pathlib.Path` objects.

        Raises:
            RuntimeError: If the ``cryptography`` package is not installed.
        """
        try:
            from cryptography import x509
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.x509.oid import NameOID
        except ImportError as exc:
            raise RuntimeError(
                "cryptography package required for self_signed TLS. "
                "Install with: pip install cryptography"
            ) from exc

        cert_path = Path(config.get("cert_path", "/tmp/valdo-tls/cert.pem"))
        key_path = Path(config.get("key_path", "/tmp/valdo-tls/key.pem"))
        cn = config.get("cn", "localhost")
        san_names = config.get("san", [cn])

        cert_path.parent.mkdir(parents=True, exist_ok=True)
        key_path.parent.mkdir(parents=True, exist_ok=True)

        # Generate private key
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        key_path.write_bytes(
            private_key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.TraditionalOpenSSL,
                serialization.NoEncryption(),
            )
        )

        # Build SAN list — split IP addresses from DNS names
        subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])
        san_list = []
        for name in san_names:
            try:
                import ipaddress as _ip
                san_list.append(x509.IPAddress(_ip.ip_address(name)))
            except ValueError:
                san_list.append(x509.DNSName(name))

        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.utcnow())
            .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365))
            .add_extension(x509.SubjectAlternativeName(san_list), critical=False)
            .sign(private_key, hashes.SHA256())
        )
        cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        logger.info("Self-signed TLS cert generated: %s (CN=%s)", cert_path, cn)
        return cert_path, key_path


class EnterpriseCAStrategy(TLSStrategy):
    """Fetch a TLS certificate from an enterprise certificate authority API.

    On first call the strategy POSTs a JSON request to ``ca_api_url`` and
    caches the returned cert/key to disk.  On subsequent calls it returns
    the cached cert if its remaining validity exceeds ``expiry_warn_days``.

    Required config keys:
        ``ca_api_url``       — URL of the CA issuance endpoint.

    Optional config keys:
        ``cert_path``        — destination PEM cert (default:
            ``/tmp/valdo-tls/cert.pem``).
        ``key_path``         — destination PEM key (default:
            ``/tmp/valdo-tls/key.pem``).
        ``cn``               — common name sent in the API request
            (default: ``localhost``).
        ``san``              — SAN list sent in the API request
            (default: ``[cn]``).
        ``ca_api_token_env`` — name of the env var holding the bearer token
            (default: ``CA_API_TOKEN``).
        ``expiry_warn_days`` — minimum days of validity required to use the
            cached cert (default: ``30``).
    """

    def resolve(self, config: dict) -> tuple:
        """Return cert/key paths, using cache if valid or fetching from CA.

        Args:
            config: The ``tls`` section dict from ``ui.yml``.

        Returns:
            ``(cert_path, key_path)`` as :class:`pathlib.Path` objects.

        Raises:
            RuntimeError: If the CA API returns an error or the response
                cannot be parsed.
        """
        import json
        import urllib.request

        ca_api_url = config["ca_api_url"]
        token_env = config.get("ca_api_token_env", "CA_API_TOKEN")
        token = os.getenv(token_env, "")
        cert_path = Path(config.get("cert_path", "/tmp/valdo-tls/cert.pem"))
        key_path = Path(config.get("key_path", "/tmp/valdo-tls/key.pem"))
        cn = config.get("cn", "localhost")
        san_names = config.get("san", [cn])
        warn_days = config.get("expiry_warn_days", 30)

        # Return cached cert if still sufficiently valid
        if cert_path.exists() and key_path.exists():
            cached_expiry = _cert_expiry(cert_path)
            if cached_expiry and cached_expiry > datetime.datetime.utcnow() + datetime.timedelta(
                days=warn_days
            ):
                logger.info(
                    "Using cached enterprise cert (expires %s)", cached_expiry.date()
                )
                return cert_path, key_path

        # Fetch from CA API
        payload = json.dumps({"cn": cn, "san": san_names}).encode()
        req = urllib.request.Request(
            ca_api_url,
            data=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())

        cert_path.parent.mkdir(parents=True, exist_ok=True)
        key_path.parent.mkdir(parents=True, exist_ok=True)
        cert_path.write_text(data["cert"])
        key_path.write_text(data["key"])
        logger.info("Enterprise CA cert fetched and cached to %s", cert_path)
        return cert_path, key_path


def _cert_expiry(cert_path: Path):
    """Return the expiry :class:`datetime.datetime` of a PEM cert, or ``None``.

    Args:
        cert_path: Path to the PEM-encoded X.509 certificate.

    Returns:
        A naive UTC :class:`datetime.datetime` representing the
        ``notAfter`` field, or ``None`` if the cert cannot be read or
        the ``cryptography`` package is unavailable.
    """
    try:
        from cryptography import x509 as _x509

        cert = _x509.load_pem_x509_certificate(cert_path.read_bytes())
        # not_valid_after_utc is available in cryptography >= 42; fall back
        # to not_valid_after for older installs.
        try:
            return cert.not_valid_after_utc.replace(tzinfo=None)
        except AttributeError:
            return cert.not_valid_after  # type: ignore[attr-defined]
    except Exception:  # pragma: no cover
        return None


_STRATEGIES: dict = {
    "manual": ManualTLSStrategy,
    "self_signed": SelfSignedTLSStrategy,
    "enterprise_ca": EnterpriseCAStrategy,
}


def resolve_tls(tls_config: dict):
    """Resolve TLS cert and key from the ``tls`` section of ``ui.yml``.

    This is the primary public entry-point used by the ``valdo serve``
    command.  If TLS is disabled (or the config is empty) it returns
    ``None`` and the server starts in plain HTTP mode.

    Args:
        tls_config: The ``tls`` dict parsed from ``config/ui.yml``.
            Pass ``{}`` or ``None`` for no TLS.

    Returns:
        A ``(cert_path, key_path)`` tuple of :class:`pathlib.Path` objects,
        or ``None`` when TLS is disabled.

    Raises:
        RuntimeError: If the strategy name is unrecognised or cert
            resolution fails.

    Example::

        result = resolve_tls({"enabled": True, "strategy": "self_signed",
                               "cn": "valdo.internal"})
        if result:
            cert_path, key_path = result
    """
    if not tls_config or not tls_config.get("enabled", False):
        return None

    strategy_name = tls_config.get("strategy", "manual")
    strategy_cls = _STRATEGIES.get(strategy_name)
    if not strategy_cls:
        raise RuntimeError(
            f"Unknown TLS strategy: {strategy_name!r}. Valid: {list(_STRATEGIES)}"
        )

    strategy = strategy_cls()
    cert_path, key_path = strategy.resolve(tls_config)

    # Log cert info and warn if near expiry
    expiry = _cert_expiry(cert_path)
    warn_days = tls_config.get("expiry_warn_days", 30)
    logger.info(
        "TLS strategy=%s cert=%s expires=%s",
        strategy_name,
        cert_path,
        expiry.date() if expiry else "unknown",
    )
    if expiry:
        days_left = (expiry - datetime.datetime.utcnow()).days
        if days_left < warn_days:
            logger.warning(
                "TLS cert expires in %d days (threshold: %d)", days_left, warn_days
            )

    return cert_path, key_path
