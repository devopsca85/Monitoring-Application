"""Shared utility functions."""


def enum_val(val, default=""):
    """Safely get string value from an Enum or plain string. Never crashes."""
    if val is None:
        return default
    if hasattr(val, 'value'):
        return val.value
    return str(val)
