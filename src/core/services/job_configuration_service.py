"""
Service for business logic related to JobConfiguration entities.
"""

# Patch points for unit tests (will be replaced by mocks); real classes are imported lazily
UserRepository = None
JobConfigurationRepository = None
ArchiveConfigurationRepository = None

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.models.job_configuration import JobConfiguration
    from core.repositories.job_configuration_repository import JobConfigurationRepository as _JCRepo
    from core.repositories.archive_configuration_repository import ArchiveConfigurationRepository as _ACRepo
    from core.repositories.user_repository import UserRepository as _UserRepo


class JobConfigurationService:
    """
    Service for business logic related to JobConfiguration entities.
    """

    def __init__(
        self,
        repository: Optional["_JCRepo"] = None,
        archive_config_repository: Optional["_ACRepo"] = None,
        user_repository: Optional["_UserRepo"] = None,
    ):
        # If repositories are provided use them; otherwise create default instances now
        self._repository = repository
        self._archive_config_repository = archive_config_repository
        self._user_repository = user_repository

        # Eagerly create default repositories if not supplied so tests that patch the
        # module-level classes observe the constructor calls.
        if self._repository is None:
            global JobConfigurationRepository
            if JobConfigurationRepository is None:
                from core.repositories.job_configuration_repository import JobConfigurationRepository as _Repo

                JobConfigurationRepository = _Repo

            self._repository = JobConfigurationRepository()

        if self._archive_config_repository is None:
            global ArchiveConfigurationRepository
            if ArchiveConfigurationRepository is None:
                from core.repositories.archive_configuration_repository import ArchiveConfigurationRepository as _Repo

                ArchiveConfigurationRepository = _Repo

            self._archive_config_repository = ArchiveConfigurationRepository()

        if self._user_repository is None:
            global UserRepository
            if UserRepository is None:
                from core.repositories.user_repository import UserRepository as _Repo

                UserRepository = _Repo

            self._user_repository = UserRepository()

    @property
    def repository(self) -> "_JCRepo":
        if self._repository is None:
            # Use the module-level patch point so tests can patch JobConfigurationRepository
            global JobConfigurationRepository
            if JobConfigurationRepository is None:
                from core.repositories.job_configuration_repository import JobConfigurationRepository as _Repo

                JobConfigurationRepository = _Repo

            self._repository = JobConfigurationRepository()
        return self._repository

    @property
    def archive_config_repository(self) -> "_ACRepo":
        if self._archive_config_repository is None:
            # Use the module-level patch point so tests can patch ArchiveConfigurationRepository
            global ArchiveConfigurationRepository
            if ArchiveConfigurationRepository is None:
                from core.repositories.archive_configuration_repository import ArchiveConfigurationRepository as _Repo

                ArchiveConfigurationRepository = _Repo

            self._archive_config_repository = ArchiveConfigurationRepository()
        return self._archive_config_repository

    @property
    def user_repository(self) -> "_UserRepo":
        if self._user_repository is None:
            # Use the module-level patch point so tests can patch UserRepository
            global UserRepository
            if UserRepository is None:
                from core.repositories.user_repository import UserRepository as _Repo

                UserRepository = _Repo

            self._user_repository = UserRepository()
        return self._user_repository

    def get_by_id(self, job_config_id: int) -> Optional["JobConfiguration"]:
        """Retrieve a JobConfiguration by its ID."""
        return self.repository.get_by_id(job_config_id)

    def get_by_user_id(self, user_id: int) -> List["JobConfiguration"]:
        """Retrieve all JobConfigurations for a specific user."""
        return self.repository.get_by_user_id(user_id)

    def get_by_archive_config_id(
        self, archive_config_id: int
    ) -> List["JobConfiguration"]:
        """Retrieve all JobConfigurations for a specific archive configuration."""
        return self.repository.get_by_archive_config_id(archive_config_id)

    def get_active_by_user_id(self, user_id: int) -> List["JobConfiguration"]:
        """Retrieve all active JobConfigurations for a specific user."""
        return self.repository.get_active_by_user_id(user_id)

    def create(self, job_config: "JobConfiguration") -> "JobConfiguration":
        """Create a new JobConfiguration after validation."""
        self.validate(job_config)
        self._validate_relationships(job_config)

        # Check for existing configuration for the same user and archive config
        existing = self.repository.get_by_user_and_archive_config(
            job_config.user_id, job_config.archive_configuration_id
        )
        if existing:
            raise ValueError(
                f"JobConfiguration already exists for user {job_config.user_id} and archive config {job_config.archive_configuration_id}"
            )

        self.repository.add(job_config)
        return job_config

    def update(self, job_config: "JobConfiguration") -> "JobConfiguration":
        """Update an existing JobConfiguration after validation."""
        self.validate(job_config)
        self._validate_relationships(job_config)

        # Update the updated_at timestamp
        job_config.updated_at = datetime.now(UTC)

        self.repository.update(job_config)
        return job_config

    def delete(self, job_config_id: int) -> bool:
        """Delete a JobConfiguration by ID."""
        return self.repository.delete(job_config_id)

    def list(
        self, user_id: Optional[int] = None, is_active: Optional[bool] = None
    ) -> List["JobConfiguration"]:
        """List JobConfigurations with optional filters."""
        return self.repository.list(user_id=user_id, is_active=is_active)

    def activate(self, job_config_id: int) -> "JobConfiguration":
        """Activate a JobConfiguration."""
        job_config = self.get_by_id(job_config_id)
        if not job_config:
            raise ValueError(f"JobConfiguration with ID {job_config_id} not found")

        job_config.is_active = True
        job_config.updated_at = datetime.now(UTC)
        self.repository.update(job_config)
        return job_config

    def deactivate(self, job_config_id: int) -> "JobConfiguration":
        """Deactivate a JobConfiguration."""
        job_config = self.get_by_id(job_config_id)
        if not job_config:
            raise ValueError(f"JobConfiguration with ID {job_config_id} not found")

        job_config.is_active = False
        job_config.updated_at = datetime.now(UTC)
        self.repository.update(job_config)
        return job_config

    def get_scheduled_configs(
        self, schedule_type: Optional[str] = None
    ) -> List["JobConfiguration"]:
        """Get all active job configurations that have scheduled execution."""
        return self.repository.get_scheduled_configs(schedule_type=schedule_type)

    def create_default_for_archive_config(
        self,
        archive_config_id: int,
        schedule_type: str = "daily",
        schedule_hour: int = 23,
        schedule_minute: int = 59,
        schedule_day_of_week: Optional[int] = None,
        archive_window_days: int = 30,
    ) -> "JobConfiguration":
        """Create a default JobConfiguration for an ArchiveConfiguration."""
        # Get the archive configuration to validate it exists and get user_id
        archive_config = self.archive_config_repository.get_by_id(archive_config_id)
        if not archive_config:
            raise ValueError(
                f"ArchiveConfiguration with ID {archive_config_id} not found"
            )

        # Check if a job configuration already exists
        existing = self.repository.get_by_user_and_archive_config(
            archive_config.user_id, archive_config_id
        )
        if existing:
            raise ValueError(
                f"JobConfiguration already exists for archive config {archive_config_id}"
            )

        from core.models.job_configuration import JobConfiguration as _JC

        job_config = _JC(
            user_id=archive_config.user_id,
            archive_configuration_id=archive_config_id,
            archive_window_days=archive_window_days,
            schedule_type=schedule_type,
            schedule_hour=schedule_hour,
            schedule_minute=schedule_minute,
            schedule_day_of_week=schedule_day_of_week,
            is_active=True,
        )

        return self.create(job_config)

    def sync_with_archive_config_status(self, archive_config_id: int) -> Dict[str, Any]:
        """Sync JobConfiguration active status with ArchiveConfiguration active status."""
        archive_config = self.archive_config_repository.get_by_id(archive_config_id)
        if not archive_config:
            raise ValueError(
                f"ArchiveConfiguration with ID {archive_config_id} not found"
            )

        if archive_config.is_active:
            count = self.repository.activate_by_archive_config_id(archive_config_id)
            return {"action": "activated", "count": count}
        else:
            count = self.repository.deactivate_by_archive_config_id(archive_config_id)
            return {"action": "deactivated", "count": count}

    def validate(self, job_config: "JobConfiguration") -> None:
        """Validate a JobConfiguration."""
        if not job_config:
            raise ValueError("JobConfiguration cannot be None")

        # Use the model's built-in validation
        job_config.validate()

    def _validate_relationships(self, job_config: "JobConfiguration") -> None:
        """Validate that the related entities exist."""
        # Validate user exists
        user = self.user_repository.get_by_id(job_config.user_id)
        if not user:
            raise ValueError(f"User with ID {job_config.user_id} not found")

        # Validate archive configuration exists
        archive_config = self.archive_config_repository.get_by_id(
            job_config.archive_configuration_id
        )
        if not archive_config:
            raise ValueError(
                f"ArchiveConfiguration with ID {job_config.archive_configuration_id} not found"
            )

        # Validate that the archive configuration belongs to the same user
        if archive_config.user_id != job_config.user_id:
            raise ValueError(
                f"ArchiveConfiguration {job_config.archive_configuration_id} does not belong to user {job_config.user_id}"
            )

    def get_summary_for_user(self, user_id: int) -> Dict[str, Any]:
        """Get a summary of job configurations for a user."""
        all_configs = self.get_by_user_id(user_id)
        active_configs = [c for c in all_configs if c.is_active]

        schedule_types = {}
        for config in active_configs:
            schedule_types[config.schedule_type] = (
                schedule_types.get(config.schedule_type, 0) + 1
            )

        return {
            "total_configs": len(all_configs),
            "active_configs": len(active_configs),
            "inactive_configs": len(all_configs) - len(active_configs),
            "schedule_types": schedule_types,
            "configs": [
                {
                    "id": config.id,
                    "archive_config_id": config.archive_configuration_id,
                    "schedule_description": config.get_schedule_description(),
                    "archive_window_days": config.archive_window_days,
                    "is_active": config.is_active,
                }
                for config in all_configs
            ],
        }
