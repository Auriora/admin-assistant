"""
Calendar resolution utility for resolving calendar URIs to actual calendar IDs.

This module handles the resolution of calendar URIs (both new format and legacy)
to actual calendar IDs across different providers.
"""

import logging
import requests
from typing import Optional, Dict, Any, List
from core.utilities.uri_utility import (
    parse_resource_uri, 
    ParsedURI, 
    URIParseError,
    normalize_calendar_name_for_lookup,
    create_legacy_compatible_lookup_key,
    migrate_legacy_uri
)

logger = logging.getLogger(__name__)


class CalendarResolutionError(Exception):
    """Raised when calendar resolution fails."""
    pass


class CalendarResolver:
    """Resolves calendar URIs to actual calendar IDs."""
    
    def __init__(self, user, access_token: Optional[str] = None):
        """
        Initialize calendar resolver.
        
        Args:
            user: User object
            access_token: MS Graph access token (required for msgraph:// URIs)
        """
        self.user = user
        self.access_token = access_token
        self._calendar_cache: Dict[str, List[Dict[str, Any]]] = {}
    
    def resolve_calendar_uri(self, uri: str) -> str:
        """
        Resolve a calendar URI to the actual calendar ID.

        Args:
            uri: Calendar URI to resolve

        Returns:
            Actual calendar ID

        Raises:
            CalendarResolutionError: If resolution fails
        """
        if not uri:
            return ""

        try:
            # Try to parse as new format first
            try:
                parsed = parse_resource_uri(uri)
            except URIParseError:
                # Fall back to legacy format migration
                logger.debug(f"Failed to parse URI as new format, attempting legacy migration: {uri}")
                migrated_uri = migrate_legacy_uri(uri)
                parsed = parse_resource_uri(migrated_uri)

            # Validate account context if present
            if parsed.account:
                self._validate_account_context(parsed.account)

            # Validate namespace
            if parsed.namespace != 'calendars':
                raise CalendarResolutionError(f"Unsupported namespace '{parsed.namespace}' for calendar URI: {uri}")

            # Route to appropriate resolver
            if parsed.scheme == 'msgraph':
                return self._resolve_msgraph_calendar(parsed)
            elif parsed.scheme == 'local':
                return self._resolve_local_calendar(parsed)
            else:
                raise CalendarResolutionError(f"Unsupported scheme '{parsed.scheme}' for calendar URI: {uri}")

        except Exception as e:
            logger.error(f"Failed to resolve calendar URI '{uri}': {e}")
            raise CalendarResolutionError(f"Failed to resolve calendar URI '{uri}': {e}") from e

    def resolve_calendar(self, uri: str) -> str:
        """
        Alias for resolve_calendar_uri for backward compatibility.

        Args:
            uri: Calendar URI to resolve

        Returns:
            Actual calendar ID

        Raises:
            CalendarResolutionError: If resolution fails
        """
        return self.resolve_calendar_uri(uri)

    def _validate_account_context(self, account: str) -> None:
        """
        Validate that the URI account context matches the user.

        Args:
            account: Account identifier from the URI

        Raises:
            CalendarResolutionError: If account doesn't match the user
        """
        if not account or not account.strip():
            logger.debug("Empty account context provided, skipping validation")
            return

        account = account.strip()

        # Check against user email (primary match, case-insensitive)
        if self.user.email and account.lower() == self.user.email.lower():
            logger.debug(f"Account context '{account}' validated against user email")
            return

        # Check against user username (secondary match, case-sensitive)
        if self.user.username and account == self.user.username:
            logger.debug(f"Account context '{account}' validated against username")
            return

        # Check against user ID (tertiary match)
        if account == str(self.user.id):
            logger.debug(f"Account context '{account}' validated against user ID")
            return

        # If no matches found, raise error
        user_identifiers = []
        if self.user.email:
            user_identifiers.append(f"email: {self.user.email}")
        if self.user.username:
            user_identifiers.append(f"username: {self.user.username}")
        user_identifiers.append(f"ID: {self.user.id}")

        logger.warning(f"Account context validation failed: URI account '{account}' does not match user ({', '.join(user_identifiers)})")
        raise CalendarResolutionError(
            f"Account context mismatch: URI account '{account}' does not match the current user. "
            f"Expected one of: {', '.join(user_identifiers)}"
        )

    def _resolve_msgraph_calendar(self, parsed: ParsedURI) -> str:
        """
        Resolve MS Graph calendar URI.

        Args:
            parsed: Parsed URI object

        Returns:
            MS Graph calendar ID
        """
        if not self.access_token:
            raise CalendarResolutionError("MS Graph access token required for msgraph:// URIs")

        # If identifier looks like a real MS Graph ID, return as-is
        if not parsed.is_friendly_name:
            # Handle special case for primary calendar even when treated as technical ID
            if parsed.identifier in ('primary', 'calendar', ''):
                logger.debug(f"Technical ID '{parsed.identifier}' is primary calendar, returning empty string")
                return ""  # Empty string represents primary calendar in MS Graph
            logger.debug(f"Identifier appears to be a technical ID, using as-is: {parsed.identifier}")
            return parsed.identifier

        # Resolve friendly name to actual calendar ID
        calendars = self._get_msgraph_calendars()

        # Try exact name match first
        for cal in calendars:
            if cal.get('name', '') == parsed.identifier:
                calendar_id = cal.get('id', '')
                logger.debug(f"Resolved '{parsed.identifier}' to calendar ID via exact match: {calendar_id}")
                return calendar_id

        # Try normalized name matching
        target_normalized = normalize_calendar_name_for_lookup(parsed.identifier)
        for cal in calendars:
            cal_normalized = normalize_calendar_name_for_lookup(cal.get('name', ''))
            if cal_normalized == target_normalized:
                calendar_id = cal.get('id', '')
                logger.debug(f"Resolved '{parsed.identifier}' to calendar ID via normalized match: {calendar_id}")
                return calendar_id

        # Try legacy-compatible matching for backward compatibility
        target_legacy = create_legacy_compatible_lookup_key(parsed.identifier)
        for cal in calendars:
            cal_legacy = create_legacy_compatible_lookup_key(cal.get('name', ''))
            if cal_legacy == target_legacy:
                calendar_id = cal.get('id', '')
                logger.debug(f"Resolved '{parsed.identifier}' to calendar ID via legacy match: {calendar_id}")
                return calendar_id

        # Handle special cases only if no actual calendar was found with that name
        if parsed.identifier in ('primary', 'calendar', ''):
            logger.debug(f"No calendar found with name '{parsed.identifier}', treating as primary calendar")
            return ""  # Empty string represents primary calendar in MS Graph

        # If not found, return the identifier as-is (might be a valid ID we don't recognize)
        logger.warning(f"Calendar '{parsed.identifier}' not found in user's calendars, using as-is")
        return parsed.identifier
    
    def _resolve_local_calendar(self, parsed: ParsedURI) -> str:
        """
        Resolve local database calendar URI.
        
        Args:
            parsed: Parsed URI object
            
        Returns:
            Local calendar ID
        """
        # For local calendars, the identifier is typically the calendar ID or name
        # This would need to be implemented based on your local calendar repository
        logger.debug(f"Resolving local calendar: {parsed.identifier}")
        
        # If identifier is numeric, assume it's a calendar ID
        if parsed.identifier.isdigit():
            return parsed.identifier
        
        # Otherwise, it's a calendar name that needs to be resolved
        # This would require querying the local calendar repository
        # For now, return as-is
        return parsed.identifier
    
    def _get_msgraph_calendars(self) -> List[Dict[str, Any]]:
        """
        Get list of calendars from MS Graph API.
        
        Returns:
            List of calendar data dictionaries
        """
        cache_key = f"msgraph_calendars_{self.user.email}"
        
        if cache_key in self._calendar_cache:
            return self._calendar_cache[cache_key]
        
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            url = f"https://graph.microsoft.com/v1.0/users/{self.user.email}/calendars?$select=id,name,isDefaultCalendar"
            response = requests.get(url, headers=headers)
            
            if response.status_code != 200:
                raise CalendarResolutionError(f"Failed to fetch calendars from MS Graph: {response.status_code} {response.text}")
            
            calendars_data = response.json()
            calendars = calendars_data.get('value', [])
            
            # Cache the results
            self._calendar_cache[cache_key] = calendars
            
            logger.debug(f"Retrieved {len(calendars)} calendars from MS Graph for user {self.user.email}")
            return calendars
            
        except requests.RequestException as e:
            raise CalendarResolutionError(f"Network error while fetching calendars: {e}") from e
        except Exception as e:
            raise CalendarResolutionError(f"Unexpected error while fetching calendars: {e}") from e
    
    def clear_cache(self):
        """Clear the calendar cache."""
        self._calendar_cache.clear()
    
    def list_available_calendars(self, scheme: str = 'msgraph') -> List[Dict[str, str]]:
        """
        List available calendars with their URIs.
        
        Args:
            scheme: Calendar scheme to list
            
        Returns:
            List of calendar info dictionaries
        """
        if scheme == 'msgraph':
            calendars = self._get_msgraph_calendars()
            result = []
            
            for cal in calendars:
                name = cal.get('name', '')
                is_default = cal.get('isDefaultCalendar', False)
                
                if is_default:
                    uri = 'msgraph://calendars/primary'
                else:
                    # Use the actual name (URL-encoded in the URI)
                    from core.utilities.uri_utility import construct_resource_uri
                    uri = construct_resource_uri('msgraph', 'calendars', name)
                
                result.append({
                    'name': name,
                    'uri': uri,
                    'is_primary': is_default,
                    'scheme': 'msgraph'
                })
            
            return result
        
        elif scheme == 'local':
            # This would need to be implemented based on your local calendar repository
            return []
        
        else:
            raise ValueError(f"Unsupported scheme: {scheme}")


def resolve_calendar_uri(uri: str, user, access_token: Optional[str] = None) -> str:
    """
    Convenience function to resolve a calendar URI.
    
    Args:
        uri: Calendar URI to resolve
        user: User object
        access_token: MS Graph access token (if needed)
        
    Returns:
        Resolved calendar ID
    """
    resolver = CalendarResolver(user, access_token)
    return resolver.resolve_calendar_uri(uri)
