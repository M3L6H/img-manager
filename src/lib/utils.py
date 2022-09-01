from typing import List, Set

import pathlib
import random
import string

def search_dir(dir: pathlib.Path, suffixes: Set[str]) -> List[pathlib.Path]:
  return [p.resolve() for p in dir.glob("**/*") if p.suffix.lower() in suffixes]

def unsafe_random_str(k: int=8, options: str=string.ascii_lowercase+string.digits) -> str:
  '''
  Generates a cryptographically insecure string of length k by choosing
  randomly from the characters in options.
  '''
  return "".join(random.choices(options, k=k))
