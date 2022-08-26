import db

@db.model
class ImageState:
  def __init__(self, name: str, color: str):
    self.__name = name
    self.__color = color

@db.model
class Image:
  def __init__(self, local_path: str = "", thumbnail_path: str = "", cloud_url: str = ""):
    self.__local_path = local_path
    self.__thumbnail_path = thumbnail_path
    self.__cloud_url = cloud_url

  def __repr__(self):
    return f"<local_path: '{self.__local_path}'; thumbnail_path: '{self.__thumbnail_path}'; cloud_url: '{self.__cloud_url}'>"

  def __str__(self):
    return f"local_path: '{self.__local_path}'; thumbnail_path: '{self.__thumbnail_path}'; cloud_url: '{self.__cloud_url}'"
