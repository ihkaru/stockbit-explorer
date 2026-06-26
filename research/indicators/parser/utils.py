def clean_int(val):
    """Pembersih string numerik berformat (e.g. '6,025' -> 6025, '-' -> 0, '3.8e7' -> 38000000)."""
    if not val or val == "-":
        return 0
    val_str = str(val).replace(",", "").strip()
    try:
        return int(val_str)
    except ValueError:
        try:
            return int(float(val_str))
        except ValueError:
            return 0


def clean_float(val):
    """Pembersih string float berformat (e.g. '0.96' -> 0.96, '-' -> 0.0)."""
    if not val or val == "-":
        return 0.0
    try:
        return float(str(val).replace(",", "").strip())
    except ValueError:
        return 0.0


def parse_date_str(date_str):
    """Konversi '20260625' -> '2026-06-25'."""
    if not date_str or len(str(date_str)) != 8:
        return date_str
    s = str(date_str)
    return f"{s[:4]}-{s[4:6]}-{s[6:]}"
