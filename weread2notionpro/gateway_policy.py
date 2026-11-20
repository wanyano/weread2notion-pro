"""Policy helpers for the official WeRead agent gateway."""

WEREAD_SKILL_VERSION = "1.0.6"


def _safe_version(value):
    """Return a short log-safe version label for GitHub Actions."""
    text = str(value or "")
    safe = "".join(char for char in text if char.isalnum() or char in ".-_")
    return safe[:32] or "unknown"


def validate_gateway_response(api_name, data):
    """Validate a gateway response and return an optional non-blocking warning."""
    if not isinstance(data, dict):
        raise ValueError("WeRead gateway response must be a JSON object")

    errcode = data.get("errcode", 0)
    if errcode != 0:
        raise RuntimeError(
            f"WeRead gateway request failed: {api_name}, code={errcode}"
        )

    upgrade_info = data.get("upgrade_info")
    if not upgrade_info:
        return None

    if isinstance(upgrade_info, dict):
        current = _safe_version(
            upgrade_info.get("current_version") or WEREAD_SKILL_VERSION
        )
        latest = _safe_version(upgrade_info.get("latest_version"))
        version_detail = f"current={current}, latest={latest}; "
    else:
        version_detail = ""

    return (
        "WeRead gateway reported a non-blocking skill update; "
        f"{version_detail}using the current {api_name} response"
    )
