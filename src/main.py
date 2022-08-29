#!/usr/bin/env python
from typing import List

import argparse
import customtkinter
import os
import pathlib
import sys

HOME = pathlib.Path.home()
DATA_DIR = HOME.joinpath(".img-manager")
LAST_DB = DATA_DIR.joinpath(".last-db")
LIB_DIR = DATA_DIR.joinpath("lib")
THEME = DATA_DIR.joinpath("theme.json")
LOCAL_DIR = pathlib.Path.cwd()
DEFAULT_DB = LOCAL_DIR.joinpath("db.sqlite")

sys.path.append(os.path.abspath(str(LIB_DIR)))

import db
import gui
import utils

customtkinter.set_default_color_theme(str(THEME))
verbose = False

def parse_arguments(parser: argparse.ArgumentParser, args: List[str]) -> argparse.Namespace:
  parser.add_argument(
    "-a", "--add",
    help="Add media to be managed by img-manager. Can be a single file or directory"
  )
  parser.add_argument(
    "--db",
    help="Specify path to db"
  )
  parser.add_argument(
    "--gui",
    action="store_true",
    help="Launch the GUI"
  )
  parser.add_argument(
    "--verbose",
    action="store_true",
    help="Enable verbose logging"
  )
  return parser.parse_args(args)

def validate_input(ns: argparse.Namespace) -> None:
  error = False

  if ns.add:
    if not (os.path.isfile(ns.add) or os.path.isdir(ns.add)):
      print(f"{ns.add} is not a file or directory!")
      error = True

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

  # Connect to db
  my_db = db.DB(ns.db, verbose)

  # Run operation
  if ns.add:
    utils.add(my_db, ns.add)
  elif ns.gui:
    mw = gui.MainWindow(my_db, verbose=verbose)
    mw.show()

  my_db.disconnect()

if __name__ == "__main__":
  main(sys.argv[1:])
