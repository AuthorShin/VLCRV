"""Entry point: print the phone-friendly URL (and QR code), then serve the UI."""

import socket

import qrcode
import uvicorn

from src import settings


def lan_ip() -> str:
    """Best-effort detection of the IP the phone should connect to."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Does not send any packets; just asks the OS which interface routes out.
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return "127.0.0.1"
    finally:
        sock.close()


def remote_url() -> str:
    if settings.PUBLIC_URL:
        return settings.PUBLIC_URL.rstrip("/")
    return f"http://{lan_ip()}:{settings.PORT}"


def main() -> None:
    url = remote_url()
    print("\n" + "=" * 64)
    print(f" VLC remote control  ->  controlling VLC at "
          f"{settings.VLC_HOST}:{settings.VLC_HTTP_PORT}")
    print(f" Open this on your phone (same LAN as this VM): {url}")
    print(" (scan the QR code below, or just type the URL)")
    print("=" * 64 + "\n")

    try:
        qr = qrcode.QRCode()
        qr.add_data(url)
        qr.print_ascii()
    except Exception as exc:  # QR output is a convenience, not a requirement.
        print(f"(QR code unavailable: {exc})")

    uvicorn.run(
        "src.app:app",
        host=settings.HOST,
        port=settings.PORT,
        log_level=settings.LOG_LEVEL,
    )


if __name__ == "__main__":
    main()
