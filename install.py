#!/usr/bin/env python

from os import link, makedirs, path, remove
from pathlib import Path, PurePath
from shutil import copy, copytree, which
import subprocess
import sys

APP_NAME = "img-manager"
HOME = Path.home()
DATA_DIR = HOME.joinpath(f".{APP_NAME}")
LIB_DIR = DATA_DIR.joinpath("lib")
DEFAULT_DIR = HOME.joinpath(".local", "bin")
LOCAL_DIR = PurePath(path.realpath(__file__)).parent
LOCAL_DATA = LOCAL_DIR.joinpath("data")
LOCAL_LIB = LOCAL_DIR.joinpath("src", "lib")
LOCAL_FILE = LOCAL_DIR.joinpath("src", "main.py")
ZSHRC = HOME.joinpath(".zshrc")
BASHRC = HOME.joinpath(".bashrc")
BASH_PROFILE = HOME.joinpath(".bash_profile")
PROFILE = HOME.joinpath(".profile")
PROFILES = [
  str(ZSHRC),
  str(BASHRC),
  str(BASH_PROFILE),
  str(PROFILE)
]
PACKAGES = []

def reduce(function, iterable, initializer=None):
  it = iter(iterable)
  if initializer is None:
    value = next(it)
  else:
    value = initializer
  for element in it:
    value = function(value, element)
  return value

def yes_no_question(prompt, default="y"):
  default = default.lower()

  if default == "y":
    key = "(Y/n)"
  else:
    key = "(y/N)"

  ans = input(f"{prompt} {key}? ")

  if ans:
    return ans.lower() == "y" or ans.lower() == "yes"
  else:
    return default == "y"

def main():
  installed = False
  installation_path = which(APP_NAME)
  if installation_path:
    print(f"{APP_NAME} is already installed. Updating...")
    installed = True
    installation_path = PurePath(installation_path).parent
  else:
    installation_path = str(DEFAULT_DIR)

  if not sys.version_info.major == 3 and sys.version_info.minor >= 5:
    print("Python 3.5 or higher is required.")
    print("You are using Python {}.{}.".format(sys.version_info.major, sys.version_info.minor))
    sys.exit(1)

  if not installed:
    print(f"Where would you like to install {APP_NAME}? (Default: {str(DEFAULT_DIR)})")

  while not installed and True:
    val = input()
    if val: installation_path = val
    if yes_no_question(f"{APP_NAME} will be installed at '{installation_path}'. Is this correct"):
      break
    else:
      installation_path = str(DEFAULT_DIR)
    print(f"Where would you like to install {APP_NAME}?")

  if installed:
    print(f"Updating {APP_NAME} at '{installation_path}'...")
  else:
    print(f"Installing {APP_NAME} to '{installation_path}'...")

  if path.exists(installation_path):
    if not path.isdir(installation_path):
      print(f"Path '{installation_path}' exists but is not a directory")
      sys.exit(1)
  else:
    makedirs(installation_path)

  assert path.isfile(LOCAL_FILE)

  target = PurePath(installation_path).joinpath(APP_NAME)

  copy(str(LOCAL_FILE), str(target))
  if sys.platform == "win32":
    exe = PurePath(installation_path).joinpath(f"{APP_NAME}.exe")
    if path.isfile(exe): remove(exe)
    link(target, str(exe))

  assert path.isdir(LOCAL_DATA)

  copytree(LOCAL_DATA, DATA_DIR, dirs_exist_ok=True)

  assert path.isdir(LOCAL_LIB)

  copytree(LOCAL_LIB, LIB_DIR, dirs_exist_ok=True)

  for package in PACKAGES:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", package])

  print("Installation complete")

if __name__ == "__main__":
  main()
