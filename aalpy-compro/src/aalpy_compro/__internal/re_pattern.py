import re

NAMESPACE_PATTERN = re.compile(r"[A-Za-z_]+[0-9A-Za-z_]*")
KEY_PATTERN = re.compile(r"[0-9A-Za-z_]+")
