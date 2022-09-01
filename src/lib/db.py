from typing import Any, Dict, ForwardRef, Generic, List, Optional, Tuple, TypeVar, Union

import datetime
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
  def __init__(self,
    name: str,
    field_type: Type=Type.INTEGER,
    nonnull: bool=False,
    references: str=None,
    index: bool=False,
    unique: Union[bool, List[str]]=False,
    primarykey: bool=False
  ):
    if not re.match(r"[_a-z]+", name):
      raise ValueError(f"Invalid name {name}")

    if references is not None and not re.match(r"[_A-Z]+ \([_a-z]+\)", references):
      raise ValueError(f"Expected references with format 'TABLE (field)', got {references}")

    self.__name = name
    self.__type = field_type
    self.__nonnull = nonnull
    self.__references = references
    self.__index = index
    self.__unique = unique
    self.__primarykey = primarykey

  def get_index(self) -> str:
    '''
    Returns a template string with the command to create an index for this
    Field
    '''
    if self.__index:
      return f"CREATE INDEX {self.__name}_index ON {{}} ({self.__name});"
    return ""

  def get_reference(self) -> str:
    if self.__references is None: return ""

    return f"FOREIGN KEY ({self.__name}) REFERENCES {self.__references}"

  def get_unique(self) -> str:
    '''
    Returns a string with the required command to create a unique constraint on
    this field.
    '''
    if isinstance(self.__unique, list):
      self.__unique.append(self.__name)
      return "UNIQUE({})".format(", ".join(self.__unique))

    if self.__unique:
      return f"UNIQUE({self.__name})"

    return ""

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

  def __repr__(self):
    return self.to_str()

  def __str__(self):
    return self.to_str()

SCHEMA: Dict[str, List[Field]] = {}
T = TypeVar("T")

class ForeignKey(Generic[T]):
  '''
  Wrapper for a foreign key into another table. The inner type should be the
  class name of the model. Should be the innermost wrapper.
  '''
  pass

class Index(Generic[T]):
  '''
  Wrapper to indicate an index should be created on this column.
  '''
  pass

class Unique(Generic[T]):
  '''
  Wrapper to create a unique constraint on a column.
  '''
  pass

TYPE_MAP = {
  "str": Type.TEXT,
  "int": Type.INTEGER,
  "float": Type.FLOAT,
  "bool": Type.BOOLEAN,
  "datetime": Type.TIMESTAMP
}

class DB:
  @staticmethod
  def connect(path: str, verbose=False) -> sqlite3.Connection:
    connection = None
    try:
      connection = sqlite3.connect(path)
      if verbose:
        print(f"Successfully connected to {path}")
    except sqlite3.Error as e:
      print(f"Failed to connect to {path} due to {e}")

    return connection

  @staticmethod
  def copy(db):
    return DB(db.path, db.verbose)

  @staticmethod
  def quote(val: any) -> any:
    if isinstance(val, str):
      val = val.replace("'", "''")
      return f"'{val}'"

    if isinstance(val, datetime.datetime):
      return f"'{str(val)}'"

    return val

  def __init__(self, path: str, verbose: bool = False):
    self.path = path
    self.__connection = DB.connect(path, verbose)
    self.verbose = verbose

  def count(self, table: str) -> int:
    return self.__execute(f"SELECT COUNT(1) FROM {table}", Fetch.ONE)[0]

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
    references = ",\n".join(filter(lambda x: len(x) > 0, [f.get_reference() for f in fields]))
    uniques = ",\n".join([f.get_unique() for f in fields if len(f.get_unique()) > 0])
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
      if len(references) > 0 or len(uniques) > 0 or i < len(fields) - 1:
        query += ","
      query += "\n"
    if len(references) > 0:
      query += references
      if len(uniques) > 0:
        query += ","
      query += "\n"
    if len(uniques) > 0:
      query += uniques + "\n"
    query += ");"
    queries = [query]

    if not pkey:
      if updating:
        self.__rename_table(temp_name, name)
        self.__connection.commit()
      raise ValueError("Table requires one field to be marked as a primary key")

    queries.extend([f.get_index().format(name) for f in fields if len(f.get_index()) > 0])

    self.__execute(queries)

    if updating:
      self.__copy_data(temp_name, name)
      self.__drop_table(temp_name)

    self.__connection.commit()

  def disconnect(self):
    if self.verbose:
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
            entries[i].append(DB.quote(v[i]))
        else:
          for val in v:
            entries.append([DB.quote(val)])
      else:
        if len(entries) > 0:
          entries[0].append(DB.quote(v))
        else:
          entries.append([DB.quote(v)])

    for i in range(len(entries)):
      entries[i] = "(" + ",".join(entries[i]) + ")"

    entries = ",".join(entries)

    self.__execute(f"INSERT INTO {table} ({columns}) VALUES {entries};")
    self.__connection.commit()

  def query_one(self, table: str, id: int = None, **kwargs):
    return self.__query(table, Fetch.ONE, id, **kwargs)

  def query_all(self, table: str, limit: int=50, offset: int=0, **kwargs):
    return self.__query(table, Fetch.ALL, None, limit, offset, **kwargs)

  def update_schema(self):
    # Create tables in schema
    for table in SCHEMA:
      self.create_table(table, SCHEMA[table])

    # Delete tables not in schema
    for table in self.__get_tables():
      if table not in SCHEMA and "sqlite" not in table:
        self.__drop_table(table)

  def __copy_data(self, from_table: str, to_table: str) -> None:
    if self.verbose:
      print(f"Copying data from table {from_table} to {to_table}")
    self.__execute(f"INSERT INTO {to_table} SELECT * FROM {from_table};")

  def __drop_table(self, table: str) -> None:
    if self.verbose:
      print(f"Dropping {table}")
    self.__execute(f"DROP TABLE IF EXISTS {table};")

  def __execute(self, query: Union[str, List[str]], fetch: Fetch=Fetch.NONE, params: Tuple[any]=()) -> any:
    if not self.__connection:
      raise RuntimeError("Not connected to DB")

    cursor = self.__connection.cursor()

    if isinstance(query, str):
      query = [query]

    data = []

    for q in query:
      try:
        if self.verbose:
          print(f"Executing: {q}")
        res = cursor.execute(q, params)

        if fetch == Fetch.ONE:
          data.append(res.fetchone())
        elif fetch == Fetch.ALL:
          data.append(res.fetchall())

      except sqlite3.Error as e:
        print(f"Failed to execute {query} due to {e}")

    cursor.close()
    return data

  def __get_tables(self) -> List[str]:
    res = self.__execute("SELECT name FROM sqlite_master WHERE type='table';", Fetch.ALL)
    return [entry[0] for entry in res]

  def __query(self, table: str, fetch: Fetch, id: int=None, limit: int=None, offset: int=None, **kwargs) -> any:
    table = table.upper()
    if id:
      return self.__execute(f"SELECT * FROM {table} WHERE id=?", fetch, (id,))
    elif kwargs:
      query = f"SELECT * FROM {table} WHERE"
      for k in kwargs:
        if kwargs[k] != "*":
          query += f" {k}=?"
        else:
          query += f" {k} IS NOT NULL AND {k}!=?"
      if limit:
        query += f" LIMIT {limit}"
      if offset:
        query += f" OFFSET {offset}"
      return self.__execute(query, fetch, tuple([k if k != "*" else "" for k in kwargs.values()]))

    return self.__execute(f"SELECT * FROM {table}", fetch)

  def __rename_table(self, old_name: str, new_name: str):
    if self.verbose:
      print(f"Renaming table {old_name} to {new_name}")
    self.__execute(f"ALTER TABLE {old_name} RENAME TO {new_name};")

  def __table_exists(self, table_name: str) -> bool:
    return self.__execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?;", Fetch.ONE, (table_name,)) != None

def unwrap_annotation(annotation: Any) -> Tuple[Type, Dict[str, any]]:
  if "__args__" not in dir(annotation):
    if hasattr(annotation, "__name__") and annotation.__name__ in TYPE_MAP:
      return (TYPE_MAP[annotation.__name__], {})
    else:
      return (None, {})

  if re.match(r"^\w*\.?Index\[.*\]$", str(annotation)):
    t, flags = unwrap_annotation(annotation.__args__[0])
    flags["index"] = True
    return (t, flags)

  if re.match(r"^\w*\.?Unique\[.*\]$", str(annotation)):
    t, flags = unwrap_annotation(annotation.__args__[0])
    flags["unique"] = True
    return (t, flags)

  if re.match(r"^\w*\.?ForeignKey\[.*\]$", str(annotation)):
    _, flags = unwrap_annotation(annotation.__args__[0])
    ref = annotation.__args__[0]
    ref = ref.__forward_arg__ if isinstance(ref, ForwardRef) else ref.__name__
    flags["ref"] = f"{ref.upper()} (id)"
    return (Type.INTEGER, flags)

def model(my_class):
  global SCHEMA
  fields = [Field("id", index=True, primarykey=True)]
  params = inspect.signature(my_class.__init__).parameters
  table: str = my_class.__name__.upper()

  for p in params:
    if p == "self":
      continue
    param = params[p]
    annotation = param.annotation
    field_type, flags = unwrap_annotation(annotation)

    create_index = "index" in flags
    make_unique = "unique" in flags
    ref = None
    if "ref" in flags:
      ref = flags["ref"]

    fields.append(Field(param.name, field_type, param.default == inspect.Parameter.empty, ref, create_index, make_unique))

  SCHEMA[table] = fields

  def all(db: DB) -> List[my_class]:
    res = db.query_all(table)
    return [my_class(*entry[1:]) for entry in res]

  my_class.all = all

  def count(db: DB) -> int:
    res = db.count(table)
    if res:
      return res
    return 0

  my_class.count = count

  param_values = params.values()

  arg_str = ", ".join([p.name for p in param_values if p.name != "self"])
  param_str = ", ".join([p.name if p.default == inspect.Parameter.empty else f"{p.name}={DB.quote(p.default)}" for p in param_values if p.name != "self"])

  create_str = """
def create(my_class, db, {params}):
  new_instance = my_class({args})
  db.insert("{table}", new_instance.__dict__)
  return new_instance
  """.format(args = arg_str, params = param_str, table = table)
  exec(create_str)
  my_class.create = classwrapper(my_class, locals()["create"])

  def find_one(db: DB, **kwargs) -> List[my_class]:
    res = db.query_one(table, **kwargs)
    if res:
      return my_class(*res[1:])

  my_class.find_one = find_one

  def find_all(db: DB, **kwargs) -> List[my_class]:
    res = db.query_all(table, **kwargs)
    return [my_class(*entry[1:]) for entry in res]

  my_class.find_all = find_all

  def find_by_id(db: DB, id: int) -> Optional[my_class]:
    res = db.query_one(table, id)
    if res:
      return my_class(*res[1:])

  my_class.find_by_id = find_by_id

  return my_class

def classwrapper(my_class, myfn):
  def wrapper(*args, **kwargs):
    return myfn(my_class, *args, **kwargs)
  return wrapper
