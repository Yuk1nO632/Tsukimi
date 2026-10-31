"""Small bounded decoder for AniCh's published Protobuf wire fields.

Reference: https://github.com/Sle2p/AniCh/blob/main/lib/protobuf/bangumi.pbjson.dart
Unknown fields are skipped; truncated or unsupported wire data fails closed.
"""
import base64
from urllib.parse import urlsplit
LIMIT = 2 * 1024 * 1024


def fields(data):
    """Bounded Protobuf wire reader; retain unknown fields without interpreting them."""
    if len(data) > LIMIT:
        raise ValueError("Response exceeds probe limit")
    position = 0

    def varint():
        nonlocal position
        result = 0
        for shift in range(0, 70, 7):
            if position >= len(data):
                raise ValueError("Truncated varint")
            value = data[position]
            position += 1
            result |= (value & 127) << shift
            if value < 128:
                return result
        raise ValueError("Oversized varint")

    while position < len(data):
        tag = varint()
        number, wire = tag >> 3, tag & 7
        if number == 0:
            raise ValueError("Invalid field number")
        if wire == 0:
            value = varint()
        elif wire in (1, 2, 5):
            size = varint() if wire == 2 else (8 if wire == 1 else 4)
            if position + size > len(data):
                raise ValueError("Truncated field")
            value = data[position:position + size]
            position += size
        else:
            raise ValueError(f"Unsupported wire type {wire}")
        yield number, value


def decode_url(encoded):
    # Exactly the public client's urlDecode rule: remove character at index 3.
    value = encoded[:3] + encoded[4:]
    url = base64.b64decode(value + "=" * (-len(value) % 4), validate=True).decode("utf-8")
    if urlsplit(url).scheme not in ("http", "https"):
        raise ValueError("Not an HTTP media URL")
    return url
