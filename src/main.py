#!/usr/bin/env python
from typing import List

import argparse
import os
import pathlib
import sys

HOME = pathlib.PosixPath("/cygdrive/c/cygwin64/home/Michael")
DATA_DIR = HOME.joinpath(".img-manager")
LAST_DB = DATA_DIR.joinpath(".last-db")
LIB_DIR = DATA_DIR.joinpath("lib")
LOCAL_DIR = pathlib.PosixPath.cwd()
DEFAULT_DB = LOCAL_DIR.joinpath("db.sqlite")

sys.path.append(os.path.abspath(str(LIB_DIR)))

import db

verbose = False

@db.model
class Image:
  def __init__(self, local_path: str = "", thumbnail_path: str = "", cloud_url: str = ""):
    self.__local_path = local_path
    self.__thumbnail_path = thumbnail_path
    self.__cloud_url = cloud_url

  def __repr__(self):
    return f"<local_path: '{self.__local_path}'; thumbnail_path: '{self.__thumbnail_path}'; cloud_url: '{self.__cloud_url}'>"

  def __str__(self):
    return f"local_path: '{self.__local_path}'; thumbnail_path: '{self.__thumbnail_path}'; cloud_url: '{self.__cloud_url}'"

def parse_arguments(parser: argparse.ArgumentParser, args: List[str]) -> argparse.Namespace:
  parser.add_argument(
    "--db",
    help="Specify path to db"
  )
  parser.add_argument(
    "--verbose",
    action="store_true",
    help="Enable verbose logging"
  )
  return parser.parse_args(args)

def validate_input(ns: argparse.Namespace) -> None:
  error = False

  if not ns.db:
    if os.path.isfile(LAST_DB):
      with open(str(LAST_DB), "r") as f:
        ns.db = f.read().strip()
    else:
      ns.db = DEFAULT_DB
  else:
    with open(str(LAST_DB), "w") as f:
      f.write(ns.db)

  if error:
    exit(1)

def main(args: List[str]) -> None:
  global verbose

  parser = argparse.ArgumentParser(
    description="A complete media management suite"
  )

  ns = parse_arguments(parser, args)
  validate_input(ns)

  verbose = ns.verbose

  my_db = db.DB(ns.db, verbose)

  # image: Image = Image.create(my_db, local_path = "/test")
  # print(image)
  print(Image.find_by_id(my_db, 1))
  print(Image.find_all(my_db))

  my_db.disconnect()

if __name__ == "__main__":
  main(sys.argv[1:])
