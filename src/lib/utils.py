from typing import Dict, List, Set, Tuple

import certifi
import glob
import os
import pathlib
import posixpath
import pycurl
import random
import re
import requests
import shutil
import string
import time
from urllib.parse import urlsplit, unquote
import urllib.request

DEFAULT_HEADERS = {
  "Accept": "*/*",
  "Accept-Encoding": "identity;q=1, *;q=0",
  "Accept-Language": "en-US,en;q=0.9",
  "Connection": "keep-alive",
  "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.82 Safari/537.36"
}
DEFAULT_HEADERS_LIST = [f"{k}: {DEFAULT_HEADERS[k]}" for k in DEFAULT_HEADERS]

session = requests.Session()
last_url = ""

def download_file(url: str, target: pathlib.Path, attempts: int=3, verbose: bool=False, **kwargs) -> pathlib.Path:
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
      if "libcurl" in kwargs and kwargs["libcurl"]:
        c = pycurl.Curl()
        c.setopt(c.URL, url)
        c.setopt(c.CAINFO, certifi.where())
        cookies = []
        for k, v in session.cookies.iteritems():
          cookies.append(f"{k}={v}")
        cookies = "; ".join(cookies)
        c.setopt(c.HTTPHEADER, [*DEFAULT_HEADERS_LIST, f"Cookie: {cookies}"])
        with open(str(local_filename), "wb") as f:
          c.setopt(c.WRITEDATA, f)
          c.perform()
      elif "urllib" in kwargs and kwargs["urllib"]:
        request = urllib.request.Request(url, headers=DEFAULT_HEADERS)
        session.cookies.add_cookie_header(request)
        res = urllib.request.urlopen(request)
        with open(str(local_filename), "wb") as f:
          f.write(res.read())
      elif "requests" in kwargs and kwargs["requests"]:
        with my_request(url, headers={ "Accept-Encoding": "gzip, deflate, br" }, stream=True, verbose=verbose) as r:
          r.raise_for_status()
          with open(str(local_filename), "wb") as f:
            for chunk in r.iter_content(chunk_size=4096 * 64):
              f.write(chunk)
              f.flush()
              os.fsync(f.fileno())
      else:
        raise RuntimeError(f"No download scheme supplied")
      return local_filename
    except Exception as e:
      print(f"Attempt #{attempt + 1} failed with error: {e}")
    finally:
      if "libcurl" in kwargs and kwargs["libcurl"]:
        c.close()
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

  if verbose:
    print(f"Making {method} request to {url} with {kwargs}...")

  r = session.request(
    method,
    url,
    headers={
      **DEFAULT_HEADERS,
      "Host": host,
      **headers
    },
    **kwargs
  )

  if r.status_code < 200 or r.status_code >= 300:
    print(f"Error while trying to access '{url}'")

  return r

def rolling_backup(path: str, count: int=10):
  backups = glob.glob(path + "-backup*")
  if len(backups) == 0:
    shutil.copyfile(path, path + "-backup")
  elif len(backups) < count:
    shutil.copyfile(path, path + "-backup" + f"-{len(backups)}")
  else:
    backups = sorted(backups, key=lambda t: os.stat(t).st_mtime)
    os.remove(backups[0])
    shutil.copyfile(path, backups[0])

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
