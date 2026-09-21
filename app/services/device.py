import re


MOBILE_RE = re.compile(
    r"android.*mobile|iphone|ipod|blackberry|iemobile|opera mini|mobile",
    re.IGNORECASE,
)
TABLET_RE = re.compile(r"ipad|tablet|android(?!.*mobile)|kindle|silk|playbook", re.IGNORECASE)


def detect_device(headers):
    user_agent = headers.get("User-Agent", "")
    ch_mobile = headers.get("Sec-CH-UA-Mobile", "").strip().lower()
    ch_platform = headers.get("Sec-CH-UA-Platform", "").strip().strip('"').lower()

    if ch_mobile == "?1":
        tipo = "mobile"
    elif "ipad" in user_agent.lower() or "tablet" in user_agent.lower() or ch_platform in {"ipad", "android"} and TABLET_RE.search(user_agent):
        tipo = "tablet"
    elif TABLET_RE.search(user_agent):
        tipo = "tablet"
    elif MOBILE_RE.search(user_agent):
        tipo = "mobile"
    else:
        tipo = "desktop"

    return {
        "tipo": tipo,
        "is_mobile": tipo == "mobile",
        "is_tablet": tipo == "tablet",
        "is_desktop": tipo == "desktop",
        "user_agent": user_agent,
        "client_hints": {
            "mobile": ch_mobile or None,
            "platform": ch_platform or None,
        },
    }
