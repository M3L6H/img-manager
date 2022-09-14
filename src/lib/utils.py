from typing import Dict, List, Set, Tuple

import os
import posixpath
try:
    from urlparse import urlsplit
    from urllib import unquote
except ImportError: # Python 3
    from urllib.parse import urlsplit, unquote

import pathlib
import random
import re
import requests
import string
import time

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.82 Safari/537.36"

session = requests.Session()
last_url = ""

def download_file(url: str, target: pathlib.Path, attempts=3) -> pathlib.Path:
  """
  Downloads a URL content into a file (with large file support by streaming)

  :param url: URL to download
  :param file_path: Local file name to contain the data downloaded
  :param attempts: Number of attempts
  :return: New file path. Empty string if the download failed
  """
  local_filename = target.joinpath(url2filename(url))
  timeout = 2
  for attempt in range(0, attempts):
    if attempt > 0:
      time.sleep(timeout * (2 ** attempt))

    try:
      with my_request(url, stream=True) as r:
        r.raise_for_status()
        with open(str(local_filename), 'wb') as f:
          for chunk in r.iter_content(chunk_size=1024*1024):
            f.write(chunk)
      return local_filename
    except Exception as e:
      print(f"Attempt #{attempt + 1} failed with error: {e}")
  return None

def my_request(url: str=None, method: str="GET", headers: Dict[str, str]={}, verbose: bool=False, **kwargs) -> requests.Response:
  '''
  Wrapper arround requests to make a session-backed request with some default
  headers.
  '''
  global last_url

  if url is None:
    url = last_url
  else:
    last_url = url

  match = re.match(r"^(https?://)?(?P<host>[^/]+).*$", url, re.IGNORECASE)
  host = match.group("host")

  default_headers = {
    "Accept": "*/*",
    "Accept-Encoding": "identity;q=1, *;q=0",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "Host": host,
    "User-Agent": USER_AGENT
  }

  if verbose:
    print(f"Making {method} request to {url} with {kwargs}...")

  r = session.request(
    method,
    url,
    headers={
      **default_headers,
      **headers
    },
    **kwargs
  )

  if r.status_code < 200 or r.status_code >= 300:
    print(f"Error while trying to access '{url}'")

  return r

def search_dir(dir: pathlib.Path, suffixes: Set[str]) -> List[pathlib.Path]:
  return [p.resolve() for p in dir.glob("**/*") if p.suffix.lower() in suffixes]

def substitute(template: str, match: Tuple[str]) -> str:
  '''
  Substitutes {0} patterns in the template string with the corresponding entry
  in the match tuple.
  '''
  pattern = re.compile("\{(\d+)\}")
  substituted = template

  for m in pattern.finditer(template):
    group = int(m.group(1))
    start, end = m.span()
    substituted = substituted[:start] + match[group] + substituted[end:]

  return substituted

def unsafe_random_str(k: int=8, options: str=string.ascii_lowercase+string.digits) -> str:
  '''
  Generates a cryptographically insecure string of length k by choosing
  randomly from the characters in options.
  '''
  return "".join(random.choices(options, k=k))

def url2filename(url):
    """
    Return basename corresponding to url.
    >>> print(url2filename('http://example.com/path/to/file%C3%80?opt=1'))
    fileÀ
    >>> print(url2filename('http://example.com/slash%2fname')) # '/' in name
    Traceback (most recent call last):
    ...
    ValueError
    """
    urlpath = urlsplit(url).path
    basename = posixpath.basename(unquote(urlpath))
    if (os.path.basename(basename) != basename or
      unquote(posixpath.basename(urlpath)) != basename):
      raise ValueError  # reject '%2f' or 'dir%5Cbasename.ext' on Windows
    return basename
