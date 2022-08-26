from typing import Dict, Generic, List, Optional, Tuple, TypeVar

import enum
import inspect
import re
import sqlite3

class Fetch(enum.Enum):
  NONE = 0
  ONE = 1
  ALL = 2

class Type(enum.Enum):
  TEXT = 0
  INTEGER = 1
  FLOAT = 2
  BOOLEAN = 3
  TIMESTAMP = 4

class Field:
  def __init__(self, name: str, field_type: Type = Type.INTEGER, nonnull: bool = False, references: str = "", primarykey: bool = False):
    if not re.match(r"[_a-z]+", name):
      raise ValueError(f"Invalid name {name}")

    if len(references) > 0 and not re.match(r"[_a-z]+ \([_a-z]+\)", str):
      raise ValueError(f"Expected references with format 'table (field)', got {references}")

    self.__name = name
    self.__type = field_type
    self.__nonnull = nonnull
    self.__primarykey = primarykey
    self.__references = references

  def get_reference(self) -> str:
    if len(self.__references) == 0: return ""

    return f"FOREIGN KEY ({self.__name}) REFERENCES {self.__references}"

  def is_primary(self) -> bool:
    return self.__primarykey

  def to_str(self) -> str:
    fields = []
    fields.append(self.__name)
    if self.__primarykey:
      fields.append("INTEGER PRIMARY KEY AUTOINCREMENT")
    else:
      fields.append(self.__type.name)
      if self.__nonnull:
        fields.append("NOT NULL")

    return " ".join(fields)

SCHEMA: Dict[str, List[Field]] = {}
T = TypeVar("T")

class ForeignKey(Generic[T]):
  pass

TYPE_MAP = {
  "str": Type.TEXT,
  "int": Type.INTEGER,
  "float": Type.FLOAT,
  "bool": Type.BOOLEAN,
  "date": Type.TIMESTAMP
}

class DB:
  @staticmethod
  def connect(path: str) -> sqlite3.Connection:
    connection = None
    try:
      connection = sqlite3.connect(path)
      print(f"Successfully connected to {path}")
    except sqlite3.Error as e:
      print(f"Failed to connect to {path} due to {e}")

    return connection

  def __init__(self, path: str, verbose: bool = False):
    self.__connection = DB.connect(path)
    self.__verbose = verbose

    for table in SCHEMA:
      self.create_table(table, SCHEMA[table])

  def create_table(self, name: str, fields: List[Field]):
    name = name.upper()
    if not re.match(r"[_A-Z]+", name):
      raise ValueError(f"Invalid name {name}")

    temp_name = f"__{name}_temp"
    updating = False

    if self.__table_exists(name):
      updating = True
      self.__rename_table(name, temp_name)
      self.__connection.commit()

    query = f"CREATE TABLE {name} (\n"
    pkey = False
    references = " ".join(filter(lambda x: len(x) > 0, [f.get_reference() for f in fields]))
    for i in range(len(fields)):
      field = fields[i]

      if field.is_primary():
        if pkey:
          if updating:
            self.__rename_table(temp_name, name)
            self.__connection.commit()
          raise ValueError("Fields contains more than one primary key")
        pkey = True

      query += field.to_str()
      if len(references) > 0 or i < len(fields) - 1:
        query += ","
      query += "\n"
    if len(references) > 0:
      query += references + "\n"
    query += ");"

    if not pkey:
      if updating:
        self.__rename_table(temp_name, name)
        self.__connection.commit()
      raise ValueError("Table requires one field to be marked as a primary key")

    self.__execute(query)

    if updating:
      self.__copy_data(temp_name, name)
      self.__drop_table(temp_name)

    self.__connection.commit()

  def disconnect(self):
    if self.__verbose:
      print("Disconnecting from db")
    self.__connection.close()

  def insert(self, table: str, data: Dict[str, any]) -> None:
    table = table.upper()
    columns = ",".join(data.keys())
    entries = []
    for _,v in data.items():
      if isinstance(v, list):
        if len(entries) > 0:
          for i in range(len(v)):
            entries[i].append(self.__quote(v[i]))
        else:
          for val in v:
            entries.append([self.__quote(val)])
      else:
        if len(entries) > 0:
          entries[0].append(self.__quote(v))
        else:
          entries.append([self.__quote(v)])

    for i in range(len(entries)):
      entries[i] = "(" + ",".join(entries[i]) + ")"

    entries = ",".join(entries)

    self.__execute(f"INSERT INTO {table} ({columns}) VALUES {entries};")
    self.__connection.commit()

  def query_one(self, table: str, id: int = None):
    return self.__query(table, Fetch.ONE, id)

  def query_all(self, table: str, id: int = None):
    return self.__query(table, Fetch.ALL, id)

  def __copy_data(self, from_table: str, to_table: str) -> None:
    if self.__verbose:
      print(f"Copying data from table {from_table} to {to_table}")
    self.__execute(f"INSERT INTO {to_table} SELECT * FROM {from_table};")

  def __drop_table(self, table: str) -> None:
    if self.__verbose:
      print(f"Dropping {table}")
    self.__execute(f"DROP TABLE IF EXISTS {table};")

  def __execute(self, query: str, fetch: Fetch=Fetch.NONE, params: Tuple[any]=()) -> any:
    if not self.__connection:
      raise RuntimeError("Not connected to DB")

    cursor = self.__connection.cursor()

    try:
      res = cursor.execute(query, params)
      if self.__verbose:
        print(f"Executing: {query}")
      if fetch == Fetch.ONE:
        return res.fetchone()
      elif fetch == Fetch.ALL:
        return res.fetchall()
    except sqlite3.Error as e:
      print(f"Failed to execute {query} due to {e}")

  def __query(self, table: str, fetch: Fetch, id: int = None) -> any:
    table = table.upper()
    if not id:
      return self.__execute(f"SELECT * FROM {table}", fetch)
    else:
      return self.__execute(f"SELECT * FROM {table} WHERE id=?", fetch, (id,))

  def __quote(self, val: any) -> any:
    if isinstance(val, str):
      return f"'{val}'"

    return val

  def __rename_table(self, old_name: str, new_name: str):
    if self.__verbose:
      print(f"Renaming table {old_name} to {new_name}")
    self.__execute(f"ALTER TABLE {old_name} RENAME TO {new_name};")

  def __table_exists(self, table_name: str) -> bool:
    return self.__execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?;", Fetch.ONE, (table_name,)) != None

def model(my_class):
  global SCHEMA
  fields = [Field("id", primarykey=True)]
  params = inspect.signature(my_class.__init__).parameters
  table = my_class.__name__

  for p in params:
    if p == "self":
      continue
    param = params[p]
    annotation = param.annotation
    field_type = Type.INTEGER if re.match(r"__main__\.ForeignKey\[.*\]", str(annotation)) else TYPE_MAP[annotation.__name__]
    ref = annotation.__args__[0].__name__ if re.match(r"__main__\.ForeignKey\[.*\]", str(annotation)) else ""
    fields.append(Field(param.name, field_type, param.default == inspect.Parameter.empty, ref))

  SCHEMA[table] = fields

  param_values = params.values()

  arg_str = ", ".join([p.name for p in param_values if p.name != "self"])
  data_str = "{" + ",".join([f"\"{p.name}\": {p.name}" for p in param_values if p.name != "self"]) + "}"
  param_str = ", ".join([str(p) for p in param_values if p.name != "self"])

  create_str = """
def create(my_class, db, {params}):
  db.insert("{table}", {data})
  return my_class({args})
  """.format(args = arg_str, data = data_str, params = param_str, table = table)
  exec(create_str)
  my_class.create = classwrapper(my_class, locals()["create"])

  def find_by_id(db: DB, id: int) -> Optional[my_class]:
    res = db.query_one(table, id)
    if res:
      return my_class(*res[1:])

  my_class.find_by_id = find_by_id

  def find_all(db: DB) -> List[my_class]:
    res = db.query_all(table)
    return [my_class(*entry[1:]) for entry in res]

  my_class.find_all = find_all

  return my_class

def classwrapper(my_class, myfn):
  def wrapper(*args, **kwargs):
    return myfn(my_class, *args, **kwargs)
  return wrapper
