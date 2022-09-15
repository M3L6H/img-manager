from datetime import datetime
import db

@db.model
class Downloaded:
  def __init__(self, url: db.Unique[db.Index[str]]):
    self.url = url

@db.model
class Image:
  def __init__(self, local_path: db.Unique[db.Index[str]]="", thumbnail_path: str="", cloud_url: str="", last_seen: datetime=None):
    self.local_path = local_path
    self.thumbnail_path = thumbnail_path
    self.cloud_url = cloud_url

    if last_seen is None:
      self.last_seen = datetime.now()

  def __repr__(self):
    return f"<local_path: '{self.local_path}'; thumbnail_path: '{self.thumbnail_path}'; cloud_url: '{self.cloud_url}'; last_seen: '{self.last_seen}'>"

  def __str__(self):
    return f"local_path: '{self.local_path}'; thumbnail_path: '{self.thumbnail_path}'; cloud_url: '{self.cloud_url}'; last_seen: '{self.last_seen}'"

@db.model
@db.unique("image", "tag")
class ImageTag:
  def __init__(self, image: db.Index[db.ForeignKey[Image]], tag: db.Index[db.ForeignKey["Tag"]]):
    self.image = image
    self.tag = tag

@db.model
@db.unique("name", "parent")
class Tag:
  def __init__(self, name: db.Index[str], parent: db.ForeignKey["Tag"]=None):
    self.name = name
    self.parent = parent
