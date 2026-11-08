"""
High-Speed QR Payload Router & Protocol Dissector.
Parses incoming strings in < 0.1ms into structured UPI parameters, Payment URLs, or Web URLs,
detecting protocol tampering, payment redirects, and disguised collect scams.
"""

import re
from urllib.parse import urlparse, parse_qs
from backend.schemas import PayloadType

URL_REGEX = re.compile(
    r"^(https?://|(?:www\.)|(?:[a-zA-Z0-9-]+\.(?:com|org|in|net|xyz|top|ru|io|site|online|club|biz)))",
    re.IGNORECASE
)

KNOWN_PAYMENT_DOMAINS = {
    "upiqr.in", "paytm.me", "p.paytm.me", "phon.pe", "phonepe.com",
    "gpay.app", "pay.google.com", "razorpay.me", "rzp.io",
    "instamojo.com", "cashfree.com", "bharatpe.com", "bhimupi.org.in",
    "cred.club", "mobikwik.com", "payu.in", "billdesk.com",
    "paytm.com", "bhimupi.com", "freecharge.in"
}

PAYMENT_PATH_KEYWORDS = {
    "pay", "payment", "checkout", "upi", "bill", "billpay",
    "donate", "collect", "transfer", "gateway", "recharge"
}


class QRPayloadRouter:
    """Dissects and routes QR payloads to the appropriate AI security engine."""

    @classmethod
    def _dissect_url(cls, url: str) -> dict:
        """Inspects an HTTP/HTTPS URL to detect if it is a financial payment URL or generic web URL."""
        parsed = urlparse(url)
        domain = parsed.netloc.lower().split(":")[0]
        path = parsed.path.lower()
        query_dict = parse_qs(parsed.query)
        # Flatten query dictionary to lower-case single values
        query_params = {k.lower(): v[0] for k, v in query_dict.items() if v}

        # 1. Detection of UPI Payee VPA in query parameters (e.g. ?pa=store@icici)
        payee_vpa = (
            query_params.get("pa", "").strip() or
            query_params.get("vpa", "").strip() or
            query_params.get("to", "").strip()
        )

        # 1b. Detection of embedded VPA in URL path (e.g. razorpay.me/@fresh_mule77)
        if not payee_vpa and "@" in path:
            match = re.search(r"@([a-zA-Z0-9._-]+)", path)
            if match:
                extracted = match.group(1)
                payee_vpa = extracted if "@" in extracted else f"{extracted}@razorpay"

        # 2. Domain matching known payment gateways
        is_payment_domain = any(pd in domain for pd in KNOWN_PAYMENT_DOMAINS)

        # 3. Path contains payment endpoints
        path_segments = set(re.split(r"[/_-]", path))
        has_payment_path = bool(path_segments.intersection(PAYMENT_PATH_KEYWORDS))

        # 4. Financial parameters present
        has_financial_params = any(k in query_params for k in ["am", "amount", "mc", "pn", "tr", "tid", "cu"])

        # Decide whether this URL is a financial payment URL
        is_payment_url = (
            bool(payee_vpa) or
            is_payment_domain or
            (has_payment_path and has_financial_params) or
            "upi" in query_params or
            ("pay" in path and len(query_params) > 0)
        )

        # Extract transaction parameters
        payee_name = (
            query_params.get("pn", "").strip() or
            query_params.get("name", "").strip() or
            query_params.get("merchant", "").strip()
        )
        mcc = query_params.get("mc", "").strip() or query_params.get("mcc", "").strip()
        amount_str = query_params.get("am", "").strip() or query_params.get("amount", "").strip()
        amount = None
        if amount_str:
            cleaned_amt = amount_str.replace(",", "").replace("$", "").replace("₹", "")
            if cleaned_amt.replace(".", "", 1).isdigit():
                try:
                    amount = float(cleaned_amt)
                except ValueError:
                    amount = None

        is_collect_scam = (
            "collect" in path or
            query_params.get("mode") == "collect" or
            query_params.get("intent") == "collect"
        )

        return {
            "payload_type": PayloadType.URL,
            "is_payment_url": is_payment_url,
            "target_entity": payee_vpa or domain,
            "url": url,
            "domain": domain,
            "payee_vpa": payee_vpa,
            "payee_name": payee_name,
            "mcc": mcc,
            "amount": amount,
            "is_collect_scam": is_collect_scam,
            "params": query_params,
            "is_embedded": False,
            "warnings": []
        }

    @classmethod
    def route(cls, raw_payload: str) -> dict:
        clean_text = raw_payload.strip()
        parsed = urlparse(clean_text)
        scheme = parsed.scheme.lower()

        # CASE 1: Standard Web URLs (http or https)
        if scheme in ["http", "https"]:
            return cls._dissect_url(clean_text)

        # CASE 2: NPCI UPI Payment Strings (upi://pay or upi://collect)
        elif scheme == "upi":
            path = parsed.netloc.lower() or parsed.path.lower()
            query_params = {k: v[0] for k, v in parse_qs(parsed.query).items()}
            warnings = []

            # Protocol Anomaly 1: Disguised Collect Request (Reverse-Charge Scam)
            is_collect_scam = False
            if "collect" in path or query_params.get("mode") == "collect":
                is_collect_scam = True
                warnings.append("Reverse-Charge Scam: QR is formatted as a 'collect' request to deduct funds.")

            # Protocol Anomaly 2: Embedded Trojan Link in note or url parameter
            embedded_url = None
            if "url" in query_params:
                embedded_url = query_params["url"]
            elif "tn" in query_params and URL_REGEX.search(query_params["tn"]):
                embedded_url = query_params["tn"]

            payee_vpa = query_params.get("pa", "").strip()
            payee_name = query_params.get("pn", "").strip()
            mcc = query_params.get("mc", "").strip()
            amount = query_params.get("am")

            return {
                "payload_type": PayloadType.UPI,
                "is_payment_url": False,
                "target_entity": payee_vpa or "unknown_payee",
                "payee_vpa": payee_vpa,
                "payee_name": payee_name,
                "mcc": mcc,
                "amount": float(amount) if amount and amount.replace(".", "", 1).isdigit() else None,
                "is_collect_scam": is_collect_scam,
                "embedded_url": embedded_url,
                "params": query_params,
                "warnings": warnings
            }

        # CASE 3: Plain text matching domain pattern (e.g. upiqr.in/pay or bit.ly/claim or google.com)
        elif URL_REGEX.search(clean_text):
            normalized_url = clean_text if clean_text.startswith("http") else f"https://{clean_text}"
            return cls._dissect_url(normalized_url)

        # CASE 4: Plain VPA string without upi:// scheme (e.g. merchant@icici)
        elif "@" in clean_text and not " " in clean_text and "." in clean_text:
            return {
                "payload_type": PayloadType.UPI,
                "is_payment_url": False,
                "target_entity": clean_text.lower(),
                "payee_vpa": clean_text.lower(),
                "payee_name": "",
                "mcc": "",
                "amount": None,
                "is_collect_scam": False,
                "embedded_url": None,
                "params": {"pa": clean_text.lower()},
                "warnings": []
            }

        # UNRECOGNIZED FORMAT
        else:
            return {
                "payload_type": PayloadType.UNKNOWN,
                "is_payment_url": False,
                "target_entity": clean_text[:50],
                "raw": clean_text,
                "warnings": ["Unrecognized QR format: Not a valid UPI payment string or web URL."]
            }
