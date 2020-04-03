import asyncio
import asyncpg
from .fields import *


class DBFilter:
    """Specifies how to filter items in a database query."""

    def __init__(self, **kwargs):
        self.filter_kwargs = kwargs
        self.filter_sql = self._process_filters()

    def _process_filters(self):
        filters = []
        for field_name, value in self.filter_kwargs.items():
            if field_name.endswith("__in"):
                filters.append(f"{field_name[:-4]} IN {tuple(value)!r}")
            elif field_name.endswith("__gt"):
                filters.append(f"{field_name[:-4:]} > {value!r}")
            elif field_name.endswith("__ge"):
                filters.append(f"{field_name[:-4:]} >= {value!r}")
            elif field_name.endswith("__lt"):
                filters.append(f"{field_name[:-4:]} < {value!r}")
            elif field_name.endswith("__le"):
                filters.append(f"{field_name[:-4:]} <= {value!r}")
            elif field_name.endswith("__lt"):
                filters.append(f"{field_name[:-4:]} < {value!r}")
            else:
                filters.append(f"{field_name} = {value!r}")

        return " AND ".join(filters)

    def __str__(self):
        return "WHERE " + self.filter_sql


class DBQuery:
    """Queries a table on the database."""

    def __init__(self, conn, name):
        self.conn = conn
        self.name = name

    async def all(self, limit=None):
        """Get all records in the table."""
        limit_sql = f"LIMIT {limit}" if limit is not None else ""
        records = await self.conn.fetch(f"SELECT * FROM {self.name} {limit_sql};")
        return records

    async def filter(self, where: DBFilter, limit=None):
        """Get records in the table based on a filter."""
        limit_sql = f"LIMIT {limit}" if limit is not None else ""
        records = await self.conn.fetch(f"SELECT * FROM {self.name} {where} {limit_sql};")
        return records

    async def new_record(self, **kwargs):
        """Create a new record in a database."""
        fields_sql = ", ".join(kwargs.keys())
        values_sql = ", ".join(map(repr, kwargs.values()))
        return await self.conn.execute(
            f"INSERT INTO {self.name} ({fields_sql}) VALUES ({values_sql});"
        )

    async def update_records(self, where: DBFilter = None, raw_sql=False, **kwargs):
        """Update records in a database table."""
        if raw_sql:
            updates_sql = ", ".join([f"{field}={value}" for field, value in kwargs.items()])
        else:
            updates_sql = ", ".join([f"{field}={value!r}" for field, value in kwargs.items()])

        if where:
            return await self.conn.execute(
                "UPDATE {self.name} SET {updates_sql} {where};"
            )
        else:
            return await self.conn.execute("UPDATE {self.name} SET {updates_sql};")

    async def delete_records(self, *, where: DBFilter = None):
        """Delete records in a database table."""
        if where:
            return await self.conn.execute("DELETE FROM {self.name} {where};")
        else:
            return await self.conn.execute("DELETE FROM {self.name};")


class Database:
    """Allows you to interact with a postgresql database
    easily and asyncronously."""

    settings_table = "server_settings"

    def __init__(self, url, ssl=False):
        self.url = url + ("?sslmode=require" if ssl else "")

    async def connect(self):
        self.conn = await asyncpg.connect(self.url)
        await self.new_table(
            self.settings_table, (BigInteger("guild_id"), Text("key"), Text("value"),)
        )

    async def get_setting(self, guild, key):
        records = await self.table(self.settings_table).filter(
            where=DBFilter(guild_id=guild.id, key=key)
        )
        if records:
            return records[0]["value"]

    async def set_setting(self, guild, key, value):
        await self.table(self.settings_table).new_record(
            guild_id=guild.id, key=str(key), value=str(value)
        )

    async def new_table(self, name, fields):
        fields = ", ".join([f'"{f.name}" {f.datatype}' for f in fields])
        await self.conn.execute(f"CREATE TABLE IF NOT EXISTS {name} ({fields});")

    def table(self, name):
        return DBQuery(self.conn, name)
