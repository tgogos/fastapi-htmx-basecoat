"""Custom auth exceptions."""


class LoginRequired(Exception):
    """Raised when an HTML route requires a logged-in user."""
    pass


class ForbiddenPage(Exception):
    """Raised when a signed-in person opens an HTML page their role does not allow."""
    pass
