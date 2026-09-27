"""Custom exceptions used across the domain, timetable, and game modules."""


class InvalidTimeError(Exception):
    """Raised when a time slot or time string is invalid."""


class DuplicateIdentifierError(Exception):
    """Raised when a record with a duplicate identifier is loaded."""


class InvalidRecordError(Exception):
    """Raised when a raw record dictionary is missing or has bad fields."""


class InvalidActionError(Exception):
    """Raised when a game action, travel, repair, or resource value is invalid."""