"""
Category Processing Service for Outlook Calendar Management Workflow

This service handles parsing and validation of Outlook categories according to the
documented workflow format: '<customer name> - <billing type>'
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from core.models.appointment import Appointment

logger = logging.getLogger(__name__)


class CategoryProcessingService:
    """
    Service for processing Outlook categories according to workflow format.

    Supports flexible category formats:
    - Standard format: "Customer Name - billing type" (e.g., "Modena - billable")
    - Alternative format: "billing type - Customer Name" (e.g., "Billable - Modena")

    Both formats are automatically parsed to extract customer name and billing type.
    """

    # Valid billing types according to workflow
    VALID_BILLING_TYPES = {"billable", "non-billable"}

    # Special categories that don't follow the standard format
    SPECIAL_CATEGORIES = {"admin - non-billable", "break - non-billable", "online"}

    def __init__(self):
        """Initialize the category processing service."""
        self.logger = logger

    def parse_outlook_category(
        self, category_string: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Parse category string in format '<customer name> - <billing type>' or '<billing type> - <customer name>'

        Args:
            category_string: Category string to parse

        Returns:
            Tuple of (customer_name, billing_type) or (None, None) if invalid

        Examples:
            "Acme Corp - billable" -> ("Acme Corp", "billable")
            "billable - Acme Corp" -> ("Acme Corp", "billable")
            "Client XYZ - non-billable" -> ("Client XYZ", "non-billable")
            "non-billable - Client XYZ" -> ("Client XYZ", "non-billable")
            "Invalid Category" -> (None, None)
        """
        if not category_string or not isinstance(category_string, str):
            return None, None

        # Clean and normalize the category string
        category_clean = category_string.strip().lower()

        # Check if it's a special category first
        if category_clean in self.SPECIAL_CATEGORIES:
            if category_clean == "online":
                return "Online", "online"
            else:
                # Extract customer name from special categories like "admin - non-billable"
                parts = category_clean.split(" - ", 1)
                if len(parts) == 2:
                    return parts[0].title(), parts[1]

        # Check for standard format: '<customer name> - <billing type>' or '<billing type> - <customer name>'
        if " - " not in category_string:
            return None, None

        # Split on ' - ' (space-dash-space) - should have exactly 2 parts
        parts = category_string.split(" - ")
        if len(parts) != 2:
            return None, None

        part1 = parts[0].strip()
        part2 = parts[1].strip()

        # Normalize both parts for comparison
        part1_lower = part1.lower()
        part2_lower = part2.lower()

        # Validate both parts are not empty
        if not part1 or not part2:
            return None, None

        # Try to determine which part is the billing type
        # Format 1: '<customer name> - <billing type>' (original format)
        if part2_lower in self.VALID_BILLING_TYPES:
            return part1, part2_lower

        # Format 2: '<billing type> - <customer name>' (alternative format)
        elif part1_lower in self.VALID_BILLING_TYPES:
            return part2, part1_lower

        # Neither part is a valid billing type
        return None, None

    def validate_category_format(self, categories: List[str]) -> Dict[str, List[str]]:
        """
        Validate list of categories and return validation results

        Args:
            categories: List of category strings to validate

        Returns:
            Dictionary with keys:
            - 'valid': List of valid categories
            - 'invalid': List of invalid categories
            - 'issues': List of specific validation issues
        """
        result = {"valid": [], "invalid": [], "issues": []}

        if not categories:
            return result

        for category in categories:
            if not category or not isinstance(category, str):
                result["invalid"].append(str(category))
                result["issues"].append(f"Empty or non-string category: {category}")
                continue

            customer, billing_type = self.parse_outlook_category(category)

            if customer is not None and billing_type is not None:
                result["valid"].append(category)
            else:
                result["invalid"].append(category)

                # Provide specific issue details
                if " - " not in category:
                    result["issues"].append(
                        f"Missing ' - ' separator in category: {category}"
                    )
                elif len(category.split(" - ")) != 2:
                    result["issues"].append(
                        f"Too many ' - ' separators in category: {category}"
                    )
                elif not category.split(" - ")[0].strip():
                    result["issues"].append(
                        f"Empty customer name in category: {category}"
                    )
                elif (
                    category.split(" - ")[1].strip().lower()
                    not in self.VALID_BILLING_TYPES
                    and category.lower() not in self.SPECIAL_CATEGORIES
                ):
                    result["issues"].append(
                        f"Invalid billing type in category: {category}"
                    )

        return result

    def extract_customer_billing_info(self, appointment: Appointment) -> Dict[str, Any]:
        """
        Extract customer and billing information from appointment

        Args:
            appointment: Appointment model instance

        Returns:
            Dictionary with keys:
            - 'customer': Customer name (str or None)
            - 'billing_type': Billing type (str or None)
            - 'is_valid': Whether category format is valid (bool)
            - 'issues': List of validation issues
            - 'categories_found': List of all categories found
            - 'is_personal': Whether this is a personal appointment
        """
        result = {
            "customer": None,
            "billing_type": None,
            "is_valid": False,
            "issues": [],
            "categories_found": [],
            "is_personal": False,
        }

        # Extract categories from appointment
        categories = self._extract_categories_from_appointment(appointment)
        result["categories_found"] = categories

        if not categories:
            # No categories found - this is likely a personal appointment
            result["is_personal"] = True
            result["issues"].append(
                "No categories found - treating as personal appointment"
            )
            return result

        # Validate all categories
        validation_result = self.validate_category_format(categories)

        if validation_result["valid"]:
            # Use the first valid category for customer/billing info
            first_valid = validation_result["valid"][0]
            customer, billing_type = self.parse_outlook_category(first_valid)

            result["customer"] = customer
            result["billing_type"] = billing_type
            result["is_valid"] = True

            # Log if multiple valid categories found
            if len(validation_result["valid"]) > 1:
                result["issues"].append(
                    f"Multiple valid categories found, using first: {first_valid}"
                )

        # Add any validation issues
        result["issues"].extend(validation_result["issues"])

        # If no valid categories but categories exist, it's likely misconfigured work appointment
        if not validation_result["valid"] and categories:
            result["is_personal"] = False  # Has categories but invalid format

        return result

    def is_special_category(self, category: str) -> bool:
        """
        Check if category is special (Admin, Break, Online)

        Args:
            category: Category string to check

        Returns:
            True if category is special, False otherwise
        """
        if not category or not isinstance(category, str):
            return False

        return category.strip().lower() in self.SPECIAL_CATEGORIES

    def should_mark_private(self, appointment: Appointment) -> bool:
        """
        Determine if appointment should be marked as private based on categories

        Args:
            appointment: Appointment model instance

        Returns:
            True if appointment should be marked as private, False otherwise
        """
        customer_info = self.extract_customer_billing_info(appointment)

        # Mark as private if it's a personal appointment (no valid categories)
        return customer_info["is_personal"]

    def _extract_categories_from_appointment(
        self, appointment: Appointment
    ) -> List[str]:
        """
        Extract categories from appointment model

        Args:
            appointment: Appointment model instance

        Returns:
            List of category strings
        """
        if not appointment:
            return []

        # Handle the categories field which is stored as JSON
        categories = getattr(appointment, "categories", None)

        if not categories:
            return []

        # Categories can be stored as JSON array or string
        if isinstance(categories, list):
            return [str(cat) for cat in categories if cat]
        elif isinstance(categories, str):
            # Single category as string
            return [categories] if categories.strip() else []
        else:
            # Try to handle other formats
            try:
                # Might be a JSON string that needs parsing
                import json

                if isinstance(categories, str):
                    parsed = json.loads(categories)
                    if isinstance(parsed, list):
                        return [str(cat) for cat in parsed if cat]
            except (json.JSONDecodeError, TypeError):
                pass

        return []

    def get_category_statistics(
        self, appointments: List[Appointment]
    ) -> Dict[str, Any]:
        """
        Generate statistics about categories across multiple appointments

        Args:
            appointments: List of appointment model instances

        Returns:
            Dictionary with category statistics
        """
        stats = {
            "total_appointments": len(appointments),
            "appointments_with_categories": 0,
            "personal_appointments": 0,
            "valid_categories": 0,
            "invalid_categories": 0,
            "customers": set(),
            "billing_types": {},
            "issues": [],
        }

        for appointment in appointments:
            customer_info = self.extract_customer_billing_info(appointment)

            if customer_info["categories_found"]:
                stats["appointments_with_categories"] += 1

            if customer_info["is_personal"]:
                stats["personal_appointments"] += 1

            if customer_info["is_valid"]:
                stats["valid_categories"] += 1
                if customer_info["customer"]:
                    stats["customers"].add(customer_info["customer"])
                if customer_info["billing_type"]:
                    billing_type = customer_info["billing_type"]
                    stats["billing_types"][billing_type] = (
                        stats["billing_types"].get(billing_type, 0) + 1
                    )
            else:
                stats["invalid_categories"] += 1

            stats["issues"].extend(customer_info["issues"])

        # Convert set to list for JSON serialization
        stats["customers"] = list(stats["customers"])

        return stats

    def process_appointments(self, appointments: List[Appointment]) -> List[Appointment]:
        """
        Process appointments by applying category validation and privacy settings.

        This method processes each appointment to:
        - Validate category formats
        - Extract customer and billing information
        - Apply privacy settings based on categories

        Args:
            appointments: List of appointment model instances to process

        Returns:
            List of processed appointments (same instances, potentially modified)
        """
        processed_appointments = []

        for appointment in appointments:
            # Extract customer and billing information
            customer_info = self.extract_customer_billing_info(appointment)

            # Apply privacy settings if needed
            if self.should_mark_private(appointment):
                # Mark personal appointments as private by setting sensitivity
                if hasattr(appointment, 'sensitivity'):
                    appointment.sensitivity = 'private'

            # Note: Category validation issues are available in customer_info['issues']
            # but not stored on the appointment model as it doesn't have a metadata field

            processed_appointments.append(appointment)

        return processed_appointments
