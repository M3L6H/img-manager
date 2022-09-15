from typing import Optional, Tuple

import pathlib
import os
from tqdm import tqdm
import xml.etree.ElementTree as ET

import db
import models
import msvcrt
import re
import requests
import utils
import zipfile

HOME = pathlib.Path.home()
DATA_DIR = HOME.joinpath(".img-manager")
SUPPORTED_MEDIA = { ".jpg", ".jpeg", ".png", ".mp4", ".mov" }

def add(my_db: db.DB, to_add: str, with_output: bool=True) -> None:
  to_add = pathlib.Path(to_add)

  if os.path.isdir(to_add):
    total = 0
    registered = 0
    iterator = utils.search_dir(to_add, SUPPORTED_MEDIA)
    if with_output:
      iterator = tqdm(iterator)
    for img in iterator:
      total += 1
      if not models.Image.find_one(my_db, local_path=str(img)):
        registered += 1
        models.Image.create(my_db, local_path=str(img))
    if with_output:
      print(f"Registered {registered}/{total} files in {to_add}")
  elif not models.Image.find_one(my_db, local_path=str(to_add)):
    models.Image.create(my_db, local_path=str(to_add))
    if with_output:
      print(f"Registered {to_add}")

class AuthenticationException(Exception):
  pass

class TemplateException(Exception):
  pass

def download(my_db: db.DB, template: pathlib.Path, location: pathlib.Path, username: str=None, password: str=None, verbose: bool=False, **kwargs) -> None:
  db_copy = db.DB.copy(my_db)
  data_dir = DATA_DIR.joinpath(template.stem)

  if not os.path.isdir(data_dir):
    os.mkdir(data_dir)

  password_file = data_dir.joinpath(".password")
  username_file = data_dir.joinpath(".username")
  tree = ET.parse(template)
  root = tree.getroot()

  if root.tag != "site":
    raise TemplateException(f"Invalid root tag {root.tag}. Should be <site>")

  needs_auth = False

  if "authenticated" in root.attrib:
    needs_auth = root.attrib["authenticated"].lower() == "true"

  if needs_auth:
    if password is None:
      if os.path.isfile(password_file):
        with open(str(password_file), "r") as f:
          password = f.read().strip()
        if verbose:
          print("Using previously saved password")
      else:
        raise AuthenticationException("Template requires authentication, but a password was not supplied")
    else:
      with open(str(password_file), "w") as f:
        f.write(password)

    if username is None:
      if os.path.isfile(username_file):
        with open(str(username_file), "r") as f:
          username = f.read().strip()
        if verbose:
          print("Using previously saved username")
      else:
        raise AuthenticationException("Template requires authentication, but a username was not supplied")
    else:
      with open(str(username_file), "w") as f:
        f.write(username)

  if "root" not in root.attrib:
    raise TemplateException("<site> tag missing required attribute: root")

  for page in root:
    parse_page(page, root.attrib["root"], username=username, password=password, location=location, my_db=db_copy, verbose=verbose, **kwargs)

def parse_action(action: ET.Element, root: str, match: Tuple[str], verbose: bool=False, **kwargs) -> Optional[pathlib.Path]:
  if action.tag == "page":
    parse_page(action, root, match, verbose=verbose, **kwargs)
    return

  if action.tag != "action":
    raise TemplateException(f"Invalid tag {action.tag}. Expected <action>")

  if "type" not in action.attrib:
    raise TemplateException("<action> tag missing required attribute: type")

  action_type = action.attrib["type"]

  if verbose:
    print(f"Performing {action_type}")

  if action_type == "delete":
    if "regex" not in action.attrib:
      raise TemplateException("Delete <action> tag missing required attribute: regex")
    regex = action.attrib["regex"]
    if "action_res" not in kwargs:
      raise RuntimeError("Delete <action> requires an action result. Is an extract action missing?")
    directory: pathlib.Path = kwargs["action_res"]
    if not os.path.isdir(directory):
      print(f"WARN: {directory} is not a valid directory")
      return None
    count = 0
    for _, _, files in os.walk(directory):
      for f in files:
        if re.match(regex, f):
          os.remove(directory.joinpath(f))
          count += 1
    if verbose:
      print(f"Deleted {count} files")
    return directory
  elif action_type == "download":
    if "url" not in action.attrib:
      raise TemplateException("Download <action> tag missing required attribute: url")
    url = utils.substitute(action.attrib["url"], match)
    file = utils.download_file(url, kwargs["location"], verbose=verbose, **kwargs)
    if verbose:
      print(f"Downloaded {file}")
    return file
  elif action_type == "extract":
    if "action_res" not in kwargs:
      raise RuntimeError("Extract <action> requires an action result. Is a download action missing?")
    file: pathlib.Path = kwargs["action_res"]
    target_path = file.resolve().parent.joinpath(file.stem)
    try:
      with zipfile.ZipFile(str(file), "r") as zip_ref:
        zip_ref.extractall(str(target_path))
    except zipfile.BadZipFile as e:
      print(f"\nEncountered error {e} while trying to extract {file}. Continue? (y/N)")
      if msvcrt.getch().lower() != b"y":
        exit(1)
    os.remove(file)
    if verbose:
      print("Extracted file")
    return target_path
  elif action_type == "login":
    method = "POST"

    if "method" in action.attrib:
      method = action.attrib["method"]

    if "form-encoded" in action.attrib:
      parts = action.attrib["form-encoded"].split(" ")
      data = {}
      for part in parts:
        k, v = part.split("=")
        v = v.replace("{username}", kwargs["username"])
        v = v.replace("{password}", kwargs["password"])
        data[k] = utils.substitute(v, match)
    else:
      raise TemplateException("Could not find a valid login body in login <action>")

    utils.my_request(method=method, data=data, verbose=verbose)
    if verbose:
      print("Logged in")
  elif action_type == "register":
    if "action_res" not in kwargs:
      raise RuntimeError("Register <action> requires an action result. Is a download action missing?")
    file: pathlib.Path = kwargs["action_res"]
    add(kwargs["my_db"], str(file), False)
  else:
    print(f"Unrecognized action type {action_type}")

def parse_entry(entry: ET.Element, root: str, res: requests.Response, **kwargs) -> bool:
  if entry.tag != "entry":
    raise TemplateException(f"Invalid entry tag {entry.tag}. Expected <entry>")

  if "regex" not in entry.attrib:
    raise TemplateException("<entry> tag missing required attribute: regex")

  matches = re.findall(entry.attrib["regex"], res.text)

  if len(matches) == 0: return False

  enumeration = range(0, 1)

  if "enumerate" in entry.attrib:
    enumerate_text = entry.attrib["enumerate"]
    if re.match(r"\d+", enumerate_text):
      num = int(enumerate_text)
      enumeration = range(num, num + 1)
    elif re.match(r"\d+-\d+", enumerate_text):
      a, b = enumerate_text.split("-")
      enumeration = range(int(a), int(b) + 1)
    elif enumerate_text.lower() == "all":
      enumeration = range(0, len(matches))

  if len(enumeration) > 1:
    enumeration = tqdm(enumeration)

  for i in enumeration:
    match = matches[i]

    for action in entry:
      action_res = parse_action(action, root, match, **kwargs)
      if action_res is not None:
        kwargs["action_res"] = action_res

  return True

def parse_page(page: ET.Element, root: str, match: Tuple[str]=None, verbose: bool=False, my_db: db.DB=None, **kwargs):
  if page.tag != "page":
    raise TemplateException(f"Invalid page tag {page.tag}. Expected <page>")

  if "url" not in page.attrib:
    raise TemplateException("<page> tag missing required attribute: url")

  url = page.attrib["url"]

  index = None

  if "{index}" in page.attrib["url"]:
    index = 0

    if "start" in page.attrib:
      index = int(page.attrib["start"])

    if "index" in kwargs:
      index = kwargs["index"]

    url = page.attrib["url"].replace("{index}", str(index))

  url = utils.substitute(url, match)

  if url.startswith("/"):
    url = f"{root}{url}"

  save_progress = False

  if "save-progress" in page.attrib:
    save_progress = page.attrib["save-progress"].lower() == "true"

    if save_progress and models.Downloaded.find_one(my_db, url=url) is not None:
      return

  res = utils.my_request(url, verbose=verbose)

  should_continue = False

  for entry in page:
    should_continue = should_continue or parse_entry(entry, root, res, verbose=verbose, my_db=my_db, **kwargs)

  if save_progress:
    models.Downloaded.create(my_db, url=url)

  if should_continue and index is not None:
    parse_page(page, root, match, verbose=verbose, index=index + 1, my_db=my_db, **kwargs)
