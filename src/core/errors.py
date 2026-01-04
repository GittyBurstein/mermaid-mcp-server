from __future__ import annotations


class MCPDiagramError(Exception):
    """Base error for the diagram server."""


class ValidationError(MCPDiagramError):
    """Raised when user input is invalid."""


class AccessDeniedError(MCPDiagramError):
    """Raised when an operation tries to access data outside allowed scope."""


class ExternalServiceError(MCPDiagramError):
    """Raised when an external service (GitHub/Kroki) fails."""


class NotFoundError(MCPDiagramError):
    """Raised when a requested resource is not found."""
