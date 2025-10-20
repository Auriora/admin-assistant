"""
Run the archive job runner as a standalone helper script.

The original version of this script bundled a large collection of imports that
were never exercised, which triggered CodeQL "unused import" warnings.
This trimmed version keeps the behaviour that actually runs in practice while
loading heavier dependencies only when they are required.
"""

from __future__ import annotations

import logging
import sys
from argparse import ArgumentParser

from core.db import get_session
from core.orchestrators.archive_job_runner import ArchiveJobRunner
from core.services import UserService
from core.services.archive_configuration_service import ArchiveConfigurationService
from core.utilities import get_graph_client


LOCAL_EVENTS_FILE = "tests/data/ms365_calendar_20250521_to_20250527.json"


def resolve_user_and_config(user_id: int):
    """Fetch the user and their active archive configuration."""
    user_service = UserService()
    user = user_service.get_by_id(user_id)
    if not user:
        raise RuntimeError(f"No user found in user DB for user_id={user_id}.")

    archive_config_service = ArchiveConfigurationService()
    archive_config = archive_config_service.get_active_for_user(int(getattr(user, "id", 0)))
    if not archive_config:
        raise RuntimeError(f"No active archive configuration found for user {user.email}.")

    return user, archive_config


def run_archive_job(user_id: int, archive_config_id: int, live: bool) -> dict:
    """Execute the archive job runner."""
    runner = ArchiveJobRunner()

    if live:
        session = get_session()
        user_service = UserService()
        user = user_service.get_by_id(user_id)
        if not user:
            raise RuntimeError(f"No user found for live run (user_id={user_id}).")
        # Ensure the graph client can be constructed; result is only used for validation.
        get_graph_client(user=user, session=session)

    result = runner.run_archive_job(user_id=user_id, archive_config_id=archive_config_id)
    return result


def main() -> int:
    parser = ArgumentParser(description="Run archive service sample.")
    parser.add_argument("--live", action="store_true", help="Use live MS Graph API")
    parser.add_argument("--user-id", type=int, default=1, help="User ID to archive for")
    parser.add_argument(
        "--events-file",
        type=str,
        default=LOCAL_EVENTS_FILE,
        help="Path to local events file (mock mode)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

    try:
        user, archive_config = resolve_user_and_config(args.user_id)
    except RuntimeError as exc:
        logging.error(str(exc))
        return 1

    archive_config_id = getattr(archive_config, "id", None)
    if archive_config_id is None:
        logging.error("Archive configuration does not have an ID.")
        return 1

    try:
        result = run_archive_job(args.user_id, int(archive_config_id), args.live)
    except RuntimeError as exc:
        logging.error(str(exc))
        return 1

    logging.info("[ARCHIVE RESULT]\n%s", result)
    return 0


if __name__ == "__main__":
    sys.exit(main())

