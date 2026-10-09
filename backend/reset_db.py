"""Reset the working database to the original.

    python reset_db.py        (from backend/)

Copies data/campus_customs.db over data/campus_customs_new.db. The original is
never modified. The audit trail is NOT touched (it is append-only).
"""

import shutil

from config import ORIGINAL_DB, WORKING_DB


def reset() -> None:
    for suffix in ("-wal", "-shm", "-journal"):
        WORKING_DB.with_name(WORKING_DB.name + suffix).unlink(missing_ok=True)
    shutil.copyfile(ORIGINAL_DB, WORKING_DB)


if __name__ == "__main__":
    reset()
    print(f"Reset {WORKING_DB.name} from {ORIGINAL_DB.name}")
