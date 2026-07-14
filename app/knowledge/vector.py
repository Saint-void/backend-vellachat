"""SQLAlchemy type for pgvector columns."""

from sqlalchemy.types import UserDefinedType


class Vector(UserDefinedType):
    cache_ok = True

    def __init__(self, dimensions: int):
        self.dimensions = dimensions

    def get_col_spec(self, **kw) -> str:
        return f"vector({self.dimensions})"

    def bind_processor(self, dialect):
        def process(value: list[float] | None) -> str | None:
            if value is None:
                return None
            return "[" + ",".join(f"{v:.8f}" for v in value) + "]"

        return process

    def result_processor(self, dialect, coltype):
        def process(value: str | list[float] | None) -> list[float] | None:
            if value is None:
                return None
            if isinstance(value, str):
                return [float(v) for v in value.strip("[]").split(",") if v]
            return list(value)

        return process