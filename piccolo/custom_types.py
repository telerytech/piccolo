from __future__ import annotations

import typing as t

if t.TYPE_CHECKING:  # pragma: no cover
    from piccolo.columns.combination import And, Or, Where, WhereRaw  # noqa


Combinable = t.Union["Where", "WhereRaw", "And", "Or"]
Iterable = t.Iterable[t.Any]


###############################################################################
# For backwards compatibility:

from piccolo.columns.defaults.timestamp import DatetimeDefault  # noqa
