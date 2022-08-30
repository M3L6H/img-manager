from datetime import datetime
import db

@db.model
class Image:
  def __init__(self, local_path: str="", thumbnail_path: str="", cloud_url: str="", last_seen: datetime=None):
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
class ImageTag:
  def __init__(self, image: db.ForeignKey[Image], tag: db.ForeignKey["Tag"]):
    self.image = image
    self.tag = tag

@db.model
class Tag:
  def __init__(self, name: str, parent: db.ForeignKey["Tag"]=None):
    self.name = name
    self.parent = parent
