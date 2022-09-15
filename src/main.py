#!/usr/bin/env python
from typing import List

import argparse
import customtkinter
import os
import pathlib
import subprocess
import sys

HOME = pathlib.Path.home()
DATA_DIR = HOME.joinpath(".img-manager")
TEMPLATES_DIR = DATA_DIR.joinpath("templates")
DEFAULT_LOCATION = DATA_DIR.joinpath("files")
LAST_DB = DATA_DIR.joinpath(".last-db")
LAST_LOCATION = DATA_DIR.joinpath(".last-location")
LIB_DIR = DATA_DIR.joinpath("lib")
THEME = DATA_DIR.joinpath("theme.json")
LOCAL_DIR = pathlib.Path.cwd()
DEFAULT_DB = LOCAL_DIR.joinpath("db.sqlite")

sys.path.append(os.path.abspath(str(LIB_DIR)))

import db
import functions
import gui

customtkinter.set_default_color_theme(str(THEME))
verbose = False

def parse_arguments(parser: argparse.ArgumentParser, args: List[str]) -> argparse.Namespace:
  parser.add_argument(
    "-a", "--add",
    help="Add media to be managed by img-manager. Can be a single file or directory"
  )
  parser.add_argument(
    "-d", "--download",
    help="Download media based on a template. Specify the template to follow. Template should be present in the templates folder"
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
    "-l", "--location",
    help="Specify a location to download files to"
  )
  parser.add_argument(
    "--password",
    help="Specify a password for use in authentication"
  )
  parser.add_argument(
    "--templates",
    action="store_true",
    help="Open the templates folder"
  )
  parser.add_argument(
    "--use",
    help="Specify a downloading scheme to use. Accepted values are libcurl and urllib"
  )
  parser.add_argument(
    "--username",
    help="Specify a username for use in authentication"
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
        ns.db = pathlib.Path(f.read().strip())
    else:
      ns.db = DEFAULT_DB
  else:
    with open(str(LAST_DB), "w") as f:
      f.write(ns.db)
    ns.db = pathlib.Path(ns.db)

  if ns.download:
    if not ns.download.endswith(".xml"):
      ns.download += ".xml"

    ns.download = TEMPLATES_DIR.joinpath(ns.download)

    if not os.path.isfile(ns.download):
      print(f"{ns.download} is not present in template directory.")
      error = True

  if not ns.location:
    if os.path.isfile(LAST_LOCATION):
      with open(str(LAST_LOCATION), "r") as f:
        ns.location = pathlib.Path(f.read().strip())
    else:
      ns.location = DEFAULT_LOCATION
  else:
    with open(str(LAST_LOCATION), "w") as f:
      f.write(ns.location)
    ns.location = pathlib.Path(ns.location)

  if ns.use:
    if ns.use not in ["libcurl", "urllib"]:
      print(f"{ns.use} is not a valid downloading scheme. Currently only libcurl and urllib are supported")
      error = True

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

  if ns.templates:
    subprocess.Popen("explorer /select,\"{}\"".format(TEMPLATES_DIR.joinpath("example.xml")))
    exit(0)

  # Connect to db
  my_db = db.DB(ns.db, verbose)
  my_db.update_schema()

  # Run operation
  if ns.add:
    functions.add(my_db, ns.add)
  elif ns.download:
    functions.download(
      my_db,
      ns.download,
      ns.location,
      ns.username,
      ns.password,
      verbose=verbose,
      libcurl=ns.use == "libcurl",
      urllib=ns.use == "urllib"
    )
  elif ns.gui:
    mw = gui.MainWindow(my_db, verbose=verbose)
    mw.show()

  my_db.disconnect()

if __name__ == "__main__":
  main(sys.argv[1:])
