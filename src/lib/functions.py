import pathlib
import os
from tqdm import tqdm

import db
import models
import utils

SUPPORTED_MEDIA = { ".jpg", ".jpeg", ".png", ".mp4", ".mov" }

def add(my_db: db.DB, to_add: str) -> None:
  to_add = pathlib.Path(to_add)

  if os.path.isdir(to_add):
    total = 0
    registered = 0
    for img in tqdm(utils.search_dir(to_add, SUPPORTED_MEDIA)):
      total += 1
      if not models.Image.find_one(my_db, local_path=str(img)):
        registered += 1
        models.Image.create(my_db, local_path=str(img))
    print(f"Registered {registered}/{total} files in {to_add}")
  elif not models.Image.find_one(my_db, local_path=str(to_add)):
    models.Image.create(my_db, local_path=str(to_add))
    print(f"Registered {to_add}")