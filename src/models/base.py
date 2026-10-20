from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass


class Base(MappedAsDataclass, DeclarativeBase, kw_only=True, eq=False):
    """Base class for all models.

    ``kw_only=True`` forces every generated ``__init__`` to take keyword-only
    arguments. Without it, dataclass field-ordering rules would require every
    field with a default to come after every field without one, which would
    conflict with the column declaration order in each model. ``eq=False``
    keeps SQLAlchemy's identity-based ``__eq__``/``__hash__`` instead of the
    dataclass-generated ``__eq__``: the generated one compares by field values,
    which would make distinct-but-equal rows compare equal and would make
    instances unhashable, breaking ``set``/dict use of mapped objects.
    """
