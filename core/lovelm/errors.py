"""Errors carry a stable `code` and structured `data`. The UI owns the (funny) wording."""


class LoveLMError(Exception):
    code = "error"

    def __init__(self, message: str, **data):
        super().__init__(message)
        self.data = data


class BadArchive(LoveLMError):
    code = "bad_archive"


class UnrecognizedFormat(LoveLMError):
    code = "unrecognized_format"


class InconsistentDates(LoveLMError):
    code = "inconsistent_dates"


class DateOrderAmbiguous(LoveLMError):
    """Every date reads validly as day-first and month-first and the evidence ties."""

    code = "date_order_ambiguous"


class NotTwoPeople(LoveLMError):
    code = "not_two_people"


class TooFewMessages(LoveLMError):
    code = "too_few_messages"
