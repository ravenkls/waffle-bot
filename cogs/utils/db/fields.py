

class Field:
    """Represents a field in a database table"""

    _datatype = None

    def __init__(self, field_name, *, default=None):
        self.name = field_name
        self.default = default
        self.datatype_options = {}

    @property
    def datatype(self):
        dt = self._datatype.format(**self.datatype_options)
        if self.default:
            dt += f" DEFAULT {self.default}"
        return dt


class SerialIdentifier(Field):
    def __init__(self):
        super().__init__("id")

    _datatype = "SERIAL PRIMARY KEY"


class Boolean(Field):
    _datatype = "BOOLEAN"


class Char(Field):
    _datatype = "CHAR({n})"

    def __init__(self, field_name, length, **kwargs):
        super().__init__(field_name, **kwargs)
        self.datatype_options = {"n": length}
    

class Varchar(Field):
    _datatype = "VARCHAR({n})"

    def __init__(self, field_name, length, **kwargs):
        super().__init__(field_name, **kwargs)
        self.datatype_options = {"n": length}


class Text(Field):
    _datatype = "TEXT"


class SmallInteger(Field):
    _datatype = "SMALLINT"


class Integer(Field):
    _datatype = "INT"


class BigInteger(Field):
    _datatype = "BIGINT"


class Real(Field):
    _datatype = "REAL"


class Date(Field):
    _datatype = "DATE"


class Time(Field):
    _datatype = "TIME"


class Timestamp(Field):
    _datatype = "TIMESTAMP"


class Json(Field):
    _datatype = "JSON"