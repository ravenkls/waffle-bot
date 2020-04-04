import asyncio
import asyncpg
from .fields import *


class DBFilter:
    """Specifies how to filter items in a database query."""

    def __init__(self, **kwargs):
        self.filter_kwargs = kwargs

    def sql(self, placeholders_from=1):
        filters = []
        values = list(self.filter_kwargs.values())
        removes = []

        for num, field_name in enumerate(self.filter_kwargs.keys(), start=placeholders_from):
            n = num - len(removes)
            i = num - placeholders_from
            if field_name.endswith("__in"):
                filters.append(f"{field_name[:-4]} IN ${n}")
            elif field_name.endswith("__gt"):
                filters.append(f"{field_name[:-4:]} > ${n}")
            elif field_name.endswith("__ge"):
                filters.append(f"{field_name[:-4:]} >= ${n}")
            elif field_name.endswith("__lt"):
                filters.append(f"{field_name[:-4:]} < ${n}")
            elif field_name.endswith("__le"):
                filters.append(f"{field_name[:-4:]} <= ${n}")
            elif field_name.endswith("__lt"):
                filters.append(f"{field_name[:-4:]} < ${n}")
            elif field_name.endswith("__ne"):
                if values[i] is None:
                    filters.append(f"{field_name[:-4:]} IS NOT NULL")
                    removes.append(i)
                else:
                    filters.append(f"{field_name[:-4:]} != ${n}")
            else:
                if values[i] is None:
                    filters.append(f"{field_name} IS NULL")
                    removes.append(i)
                else:
                    filters.append(f"{field_name} = ${n}")

        values = [v for n, v in enumerate(values) if n not in removes]

        return "WHERE " + " AND ".join(filters), values


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
        where_sql, where_values = where.sql()
        records = await self.conn.fetch(f"SELECT * FROM {self.name} {where_sql} {limit_sql};", *where_values)
        return records

    async def new_record(self, **kwargs):
        """Create a new record in a database."""
        fields_sql = ", ".join(kwargs.keys())
        values_sql = ", ".join([f"${n}" for n, _ in enumerate(kwargs, start=1)])
        return await self.conn.execute(
            f"INSERT INTO {self.name} ({fields_sql}) VALUES ({values_sql});", *kwargs.values()
        )
    
    async def new_record_with_id(self, **kwargs):
        """Create a new record in a database and return the 'id' value.
        Note: this only works on tables with a SerialIdentifier field."""
        fields_sql = ", ".join(kwargs.keys())
        values_sql = ", ".join([f"${n}" for n, _ in enumerate(kwargs, start=1)])
        return await self.conn.fetchval(
            f"INSERT INTO {self.name} ({fields_sql}) VALUES ({values_sql}) RETURNING id;", *kwargs.values()
        )

    async def update_records(self, where: DBFilter = None, **kwargs):
        """Update records in a database table."""
        updates_sql = ", ".join([f"{field}=${n}" for n, field in enumerate(kwargs.keys(), start=1)])

        if where:
            where_sql, where_values = where.sql(placeholders_from=len(kwargs)+1)
            return await self.conn.execute(
                f"UPDATE {self.name} SET {updates_sql} {where_sql};", *kwargs.values(), *where_values
            )
        else:
            return await self.conn.execute(f"UPDATE {self.name} SET {updates_sql};", *kwargs.values())

    async def delete_records(self, *, where: DBFilter = None):
        """Delete records in a database table."""
        if where:
            where_sql, where_values = where.sql()
            return await self.conn.execute(f"DELETE FROM {self.name} {where_sql};", *where_values)
        else:
            return await self.conn.execute(f"DELETE FROM {self.name};")


class Database:
    """Allows you to interact with a postgresql database
    easily and asyncronously."""

    settings_table = "server_setting"

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
        return self.table(name)

    def table(self, name):
        return DBQuery(self.conn, name)
