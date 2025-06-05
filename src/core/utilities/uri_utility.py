"""
URI utility functions for handling resource URIs across different providers.

This module provides utilities for parsing and constructing URIs that reference
resources like calendars, contacts, emails, etc. across different providers
(MS Graph, local database, Google, etc.).

URI Format: <scheme>://<namespace>/<identifier>

User-Friendly Input Formats:
- msgraph://calendars/Activity\\ Archive           # Backslash escaping
- msgraph://calendars/"Activity Archive"          # Quoted strings
- msgraph://calendars/'Activity Archive'          # Single quoted strings
- msgraph://calendars/Activity Archive            # Unescaped (if no conflicts)
- msgraph://calendars/primary                     # Simple identifiers

Internal Storage Format (URL-encoded):
- msgraph://calendars/Activity%20Archive
- msgraph://calendars/primary

Output Format (user-friendly):
- msgraph://calendars/"Activity Archive"          # Quoted if contains spaces/special chars
- msgraph://calendars/primary                     # Unquoted if simple
"""

import re
import urllib.parse
from dataclasses import dataclass
from typing import Optional


@dataclass
class ParsedURI:
    """Represents a parsed resource URI."""
    scheme: str  # e.g., 'msgraph', 'local', 'google'
    namespace: str  # e.g., 'calendars', 'contacts', 'emails'
    identifier: str  # e.g., 'Activity Archive', 'AQMkADAwATM3ZmYAZS05ZmQzLTljNjAtMDACLTAwCg...', '123'
    raw_uri: str  # Original URI
    
    @property
    def is_friendly_name(self) -> bool:
        """Check if identifier appears to be a friendly name vs. a technical ID."""
        # Technical IDs are typically long, contain special chars, or are numeric
        if self.identifier.isdigit():
            return False
        if len(self.identifier) > 50 and ('=' in self.identifier or '+' in self.identifier):
            return False
        return True
    
    @property
    def url_encoded_identifier(self) -> str:
        """Get URL-encoded version of the identifier."""
        return urllib.parse.quote(self.identifier, safe='')


class URIParseError(Exception):
    """Raised when a URI cannot be parsed."""
    pass


def parse_user_friendly_identifier(identifier: str) -> str:
    """
    Parse a user-friendly identifier that may contain quotes or backslash escaping.

    Supported formats:
    - "Activity Archive"     -> Activity Archive
    - 'Activity Archive'     -> Activity Archive
    - Activity\\ Archive      -> Activity Archive
    - Activity Archive       -> Activity Archive (if no parsing conflicts)
    - primary                -> primary

    Args:
        identifier: User input identifier

    Returns:
        Parsed identifier string
    """
    if not identifier:
        return identifier

    identifier = identifier.strip()

    # Handle quoted strings (double quotes)
    if identifier.startswith('"') and identifier.endswith('"') and len(identifier) >= 2:
        return identifier[1:-1]

    # Handle quoted strings (single quotes)
    if identifier.startswith("'") and identifier.endswith("'") and len(identifier) >= 2:
        return identifier[1:-1]

    # Handle backslash escaping
    if '\\' in identifier:
        # Unescape common characters
        result = identifier.replace('\\ ', ' ')  # Escaped space
        result = result.replace('\\/', '/')      # Escaped slash
        result = result.replace('\\\\', '\\')    # Escaped backslash
        result = result.replace('\\"', '"')      # Escaped quote
        result = result.replace("\\'", "'")      # Escaped single quote
        return result

    # Return as-is for simple identifiers
    return identifier


def format_user_friendly_identifier(identifier: str, force_quotes: bool = False) -> str:
    """
    Format an identifier for user-friendly display.

    Args:
        identifier: Identifier to format
        force_quotes: Force quoting even for simple identifiers

    Returns:
        User-friendly formatted identifier
    """
    if not identifier:
        return identifier

    # Check if identifier needs quoting (contains spaces or special characters)
    needs_quotes = (
        force_quotes or
        ' ' in identifier or
        '/' in identifier or
        '"' in identifier or
        "'" in identifier or
        '\\' in identifier or
        identifier.startswith('-') or
        identifier.endswith('-')
    )

    if needs_quotes:
        # Escape any existing quotes and wrap in double quotes
        escaped = identifier.replace('"', '\\"')
        return f'"{escaped}"'

    return identifier


def parse_resource_uri(uri: str) -> ParsedURI:
    """
    Parse a resource URI into its components.
    
    Args:
        uri: URI to parse (e.g., 'msgraph://calendars/Activity%20Archive')
        
    Returns:
        ParsedURI object with parsed components
        
    Raises:
        URIParseError: If URI format is invalid
    """
    if not uri:
        raise URIParseError("URI cannot be empty")
    
    # Handle legacy URIs for backward compatibility
    if uri in ('', 'calendar', 'primary'):
        return ParsedURI(
            scheme='msgraph',
            namespace='calendars',
            identifier='primary',
            raw_uri=uri
        )
    
    # Parse standard URI format
    try:
        parsed = urllib.parse.urlparse(uri)
        if not parsed.scheme:
            raise URIParseError(f"URI missing scheme: {uri}")

        # Handle the case where netloc contains the namespace (e.g., msgraph://calendars/identifier)
        # In this case, netloc = 'calendars' and path = '/identifier'
        if parsed.netloc and parsed.path:
            namespace = parsed.netloc
            raw_identifier = parsed.path.lstrip('/')
            if not raw_identifier:
                raise URIParseError(f"URI missing identifier: {uri}")
        else:
            # Handle case where everything is in the path (e.g., scheme:///namespace/identifier)
            path = parsed.path.lstrip('/')
            if not path:
                raise URIParseError(f"URI missing path: {uri}")

            path_parts = path.split('/', 1)
            if len(path_parts) < 2:
                raise URIParseError(f"URI path must have format 'namespace/identifier': {uri}")

            namespace = path_parts[0]
            raw_identifier = path_parts[1]

        # First try URL decoding (for backward compatibility with URL-encoded URIs)
        try:
            url_decoded = urllib.parse.unquote(raw_identifier)
            # If URL decoding changed the string, use the decoded version
            if url_decoded != raw_identifier:
                identifier = url_decoded
            else:
                # Otherwise, parse as user-friendly format
                identifier = parse_user_friendly_identifier(raw_identifier)
        except Exception:
            # Fallback to user-friendly parsing
            identifier = parse_user_friendly_identifier(raw_identifier)

        return ParsedURI(
            scheme=parsed.scheme,
            namespace=namespace,
            identifier=identifier,
            raw_uri=uri
        )
        
    except Exception as e:
        raise URIParseError(f"Failed to parse URI '{uri}': {e}") from e


def construct_resource_uri(scheme: str, namespace: str, identifier: str, user_friendly: bool = True) -> str:
    """
    Construct a resource URI from components.

    Args:
        scheme: Provider scheme (e.g., 'msgraph', 'local')
        namespace: Resource namespace (e.g., 'calendars', 'contacts')
        identifier: Resource identifier
        user_friendly: If True, use user-friendly format; if False, use URL encoding

    Returns:
        Constructed URI string
    """
    if not all([scheme, namespace, identifier]):
        raise ValueError("All components (scheme, namespace, identifier) are required")

    if user_friendly:
        # Use user-friendly formatting (quotes for spaces, etc.)
        formatted_identifier = format_user_friendly_identifier(identifier)
    else:
        # Use URL encoding for backward compatibility
        formatted_identifier = urllib.parse.quote(identifier, safe='')

    return f"{scheme}://{namespace}/{formatted_identifier}"


def construct_resource_uri_encoded(scheme: str, namespace: str, identifier: str) -> str:
    """
    Construct a resource URI with URL encoding (for internal storage).

    Args:
        scheme: Provider scheme (e.g., 'msgraph', 'local')
        namespace: Resource namespace (e.g., 'calendars', 'contacts')
        identifier: Resource identifier (will be URL-encoded)

    Returns:
        Constructed URI string with URL encoding
    """
    return construct_resource_uri(scheme, namespace, identifier, user_friendly=False)


def normalize_calendar_name_for_lookup(name: str) -> str:
    """
    Normalize a calendar name for lookup purposes.
    
    This creates a normalized version for fuzzy matching while preserving
    the original name in the URI.
    
    Args:
        name: Original calendar name
        
    Returns:
        Normalized name for lookup
    """
    if not name:
        return ""
    
    # Convert to lowercase and normalize whitespace
    normalized = name.lower().strip()
    normalized = re.sub(r'\s+', ' ', normalized)  # Multiple spaces to single space
    
    # Remove common punctuation that might vary
    normalized = re.sub(r'[^\w\s]', '', normalized)
    
    return normalized


def create_legacy_compatible_lookup_key(name: str) -> str:
    """
    Create a lookup key compatible with the legacy URI format.
    
    This is used for backward compatibility when resolving legacy URIs.
    
    Args:
        name: Calendar name
        
    Returns:
        Legacy-compatible lookup key
    """
    if not name:
        return ""
    
    # Apply the same transformation as the legacy code
    key = name.lower().strip()
    key = re.sub(r"\s+", "-", key)
    key = re.sub(r"[^a-z0-9\-_]", "", key)
    return key


def migrate_legacy_uri(legacy_uri: str) -> str:
    """
    Migrate a legacy URI to the new format.
    
    Args:
        legacy_uri: Legacy URI (e.g., 'msgraph://activity-archive')
        
    Returns:
        New format URI (e.g., 'msgraph://calendars/activity-archive')
    """
    if not legacy_uri:
        return ""
    
    # Handle special cases
    if legacy_uri in ('', 'calendar', 'primary'):
        return 'msgraph://calendars/primary'
    
    # Parse legacy format
    if legacy_uri.startswith('msgraph://'):
        identifier = legacy_uri[len('msgraph://'):]
        if identifier == 'calendar':
            return 'msgraph://calendars/primary'
        return f'msgraph://calendars/{identifier}'
    
    if legacy_uri.startswith('local://'):
        identifier = legacy_uri[len('local://'):]
        return f'local://calendars/{identifier}'
    
    # If it doesn't match known patterns, assume it's already in new format
    return legacy_uri


# Supported schemes and namespaces
SUPPORTED_SCHEMES = {
    'msgraph': 'Microsoft Graph',
    'local': 'Local Database',
    'google': 'Google Workspace',
    'exchange': 'Exchange Server'
}

SUPPORTED_NAMESPACES = {
    'calendars': 'Calendar resources',
    'contacts': 'Contact resources', 
    'emails': 'Email resources',
    'tasks': 'Task resources',
    'files': 'File resources'
}


def validate_uri_components(scheme: str, namespace: str) -> bool:
    """
    Validate that scheme and namespace are supported.
    
    Args:
        scheme: URI scheme
        namespace: URI namespace
        
    Returns:
        True if valid, False otherwise
    """
    return scheme in SUPPORTED_SCHEMES and namespace in SUPPORTED_NAMESPACES


def get_primary_calendar_uri(scheme: str = 'msgraph') -> str:
    """
    Get the URI for the primary calendar of a given scheme.

    Args:
        scheme: Provider scheme

    Returns:
        Primary calendar URI
    """
    return f"{scheme}://calendars/primary"


def convert_uri_to_user_friendly(uri: str) -> str:
    """
    Convert a URI to user-friendly format.

    Args:
        uri: URI to convert (may be URL-encoded or already user-friendly)

    Returns:
        User-friendly formatted URI
    """
    try:
        parsed = parse_resource_uri(uri)
        return construct_resource_uri(parsed.scheme, parsed.namespace, parsed.identifier, user_friendly=True)
    except Exception:
        return uri


def convert_uri_to_encoded(uri: str) -> str:
    """
    Convert a URI to URL-encoded format (for internal storage).

    Args:
        uri: URI to convert (may be user-friendly or already encoded)

    Returns:
        URL-encoded formatted URI
    """
    try:
        parsed = parse_resource_uri(uri)
        return construct_resource_uri(parsed.scheme, parsed.namespace, parsed.identifier, user_friendly=False)
    except Exception:
        return uri
