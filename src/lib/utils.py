from typing import List, Set

import pathlib
import os

import db
import models

SUPPORTED_MEDIA = { ".jpg", ".jpeg", ".png", ".mp4", ".mov" }

def add(my_db: db.DB, to_add: str) -> None:
  to_add = pathlib.Path(to_add)

  if os.path.isdir(to_add):
    total = 0
    registered = 0
    for img in search_dir(to_add, SUPPORTED_MEDIA):
      total += 1
      if not models.Image.find_one(my_db, local_path=str(img)):
        registered += 1
        models.Image.create(my_db, local_path=str(img))
    print(f"Registered {registered}/{total} files in {to_add}")
  elif not models.Image.find_one(my_db, local_path=str(to_add)):
    models.Image.create(my_db, local_path=str(to_add))
    print(f"Registered {to_add}")

def search_dir(dir: pathlib.Path, suffixes: Set[str]) -> List[pathlib.Path]:
  return (p.resolve() for p in dir.glob("**/*") if p.suffix.lower() in suffixes)
