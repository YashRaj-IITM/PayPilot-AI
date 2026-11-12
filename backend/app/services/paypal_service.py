import os
import json
import base64
import uuid
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


class PayPalError(Exception):
    """Raised when a PayPal API operation fails."""


def _base_url():
    mode = os.getenv("PAYPAL_MODE", "sandbox").lower()

    if mode == "sandbox":
        return "https://api-m.sandbox.paypal.com"

    if mode == "live":
        return "https://api-m.paypal.com"

    raise PayPalError("Invalid PAYPAL_MODE configuration.")


def _request(method, path, payload=None, access_token=None,
             request_id=None, form_data=None):
    url = _base_url() + path

    headers = {
        "Accept": "application/json",
    }

    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"

    if form_data is not None:
        body = form_data.encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    else:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers["Content-Type"] = "application/json"

    if request_id:
        headers["PayPal-Request-Id"] = request_id

    req = Request(url, data=body, headers=headers, method=method)

    try:
        with urlopen(req, timeout=30) as response:
            response_body = response.read().decode("utf-8")
            return json.loads(response_body) if response_body else {}

    except HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        raise PayPalError(
            f"PayPal API returned HTTP {error.code}: {details[:1000]}"
        ) from error

    except (URLError, TimeoutError) as error:
        raise PayPalError(f"Unable to connect to PayPal: {error}") from error

    except json.JSONDecodeError as error:
        raise PayPalError("PayPal returned an invalid response.") from error


def get_access_token():
    client_id = os.getenv("PAYPAL_CLIENT_ID")
    client_secret = os.getenv("PAYPAL_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise PayPalError("PayPal credentials are not configured.")

    credentials = f"{client_id}:{client_secret}".encode("utf-8")
    encoded_credentials = base64.b64encode(credentials).decode("ascii")

    response = _request(
        "POST",
        "/v1/oauth2/token",
        form_data="grant_type=client_credentials",
    ) if False else None

    # OAuth uses HTTP Basic authentication.
    url = _base_url() + "/v1/oauth2/token"
    body = b"grant_type=client_credentials"

    req = Request(
        url,
        data=body,
        headers={
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(req, timeout=30) as result:
            data = json.loads(result.read().decode("utf-8"))
            token = data.get("access_token")

            if not token:
                raise PayPalError("PayPal did not return an access token.")

            return token

    except HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        raise PayPalError(
            f"PayPal authentication failed (HTTP {error.code}): {details[:500]}"
        ) from error

    except (URLError, TimeoutError) as error:
        raise PayPalError(f"PayPal authentication connection failed: {error}") from error


def create_order(amount, currency, description, procurement_id, transaction_id=None):
    token = get_access_token()

    return_url = os.getenv(
        "PAYPAL_RETURN_URL",
        "http://localhost:5173/payment/success"
    )
    if transaction_id is not None:
        from urllib.parse import urlencode
        return_url = (
            f"{return_url}?{urlencode({'transaction_id': transaction_id})}"
        )

    cancel_url = os.getenv(
        "PAYPAL_CANCEL_URL",
        "http://localhost:5173/payment/cancel"
    )

    payload = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "custom_id": str(procurement_id),
                "description": description[:127],
                "amount": {
                    "currency_code": currency,
                    "value": str(amount),
                },
            }
        ],
        "application_context": {
            "brand_name": "PayPilot AI",
            "user_action": "PAY_NOW",
            "return_url": return_url,
            "cancel_url": cancel_url,
            "shipping_preference": "NO_SHIPPING",
        },
    }

    return _request(
        "POST",
        "/v2/checkout/orders",
        payload=payload,
        access_token=token,
        request_id=str(uuid.uuid4()),
    )


def capture_order(order_id):
    if not order_id or len(order_id) > 100:
        raise PayPalError("Invalid PayPal order ID.")

    token = get_access_token()

    return _request(
        "POST",
        f"/v2/checkout/orders/{order_id}/capture",
        payload={},
        access_token=token,
        request_id=f"capture-{order_id}"[:38],
    )
