import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from uex_library import UEXManager

_uex = UEXManager()


def get_uex() -> UEXManager:
    return _uex


def records_without_nan(df) -> list:
    """DataFrame.to_dict('records'), with NaN (nullable SQL columns) mapped to
    None — the default JSON encoder rejects float('nan') outright."""
    records = df.to_dict("records")
    for row in records:
        for key, value in row.items():
            if isinstance(value, float) and value != value:  # NaN != NaN
                row[key] = None
    return records
