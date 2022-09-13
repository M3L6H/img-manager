from typing import List

import customtkinter
import tkinter

import db
import models
import pathlib
import re
import subprocess
import threading
import widgets

HOME = pathlib.Path.home()
DATA_DIR = HOME.joinpath(".img-manager")
IMAGE_DIR = DATA_DIR.joinpath("images")
VERSION_FILE = DATA_DIR.joinpath("version")

customtkinter.set_appearance_mode("dark")

class MainWindow(customtkinter.CTk):
  def __init__(self, my_db: db.DB, verbose: bool=False):
    super().__init__()

    self.__my_db = my_db

    with open(VERSION_FILE, "r") as f:
      version = f.read().strip()

    self.title(f"img-manager {version}")
    self.state("zoomed")
    self.protocol("WM_DELETE_WINDOW", self.on_closing)  # call .on_closing() when app gets closed

    # ===== INITIALIZE MEMBERS =====
    self.__entries_per_page = 75
    self.__max_page = None
    self.__page = 0
    self.__page_var = tkinter.StringVar()
    self.__tag_var = tkinter.StringVar()
    self.update_page_var()
    self.__verbose = verbose

    # ===== CREATE THREADS =====
    self.t_max_page = threading.Thread(target=self.fetch_max_page)

    # ===== RUN THREADS
    self.t_max_page.start()

    # ===== CREATE FRAMES =====

    # Configure grid layout (2x2)
    self.grid_columnconfigure(0, weight=1)
    self.grid_columnconfigure(1, weight=4)
    self.grid_rowconfigure(0, weight=3)
    self.grid_rowconfigure(1, weight=1)

    self.__frame_left = customtkinter.CTkFrame(master=self, width=500, corner_radius=0)
    self.__frame_left.grid_rowconfigure(0, weight=1)
    self.__frame_left.grid_columnconfigure(0, weight=1)
    self.__frame_left.grid(row=0, column=0, rowspan=2, sticky="nswe")
    self.__frame_left.grid_propagate(False)

    self.__frame_right = customtkinter.CTkFrame(master=self)
    self.__frame_right.grid(row=0, column=1, sticky="nswe", padx=40, pady=40)
    self.__frame_right.grid_propagate(False)

    self.__frame_bottom = customtkinter.CTkFrame(master=self, corner_radius=0)
    self.__frame_bottom.grid(row=1, column=1, sticky="nswe")
    self.__frame_bottom.grid_propagate(False)

    # ===== LEFT FRAME =====
    self.__list_widget = widgets.CTkListbox(master=self.__frame_left, command=lambda x: self.load_media(x))
    self.__list_widget.grid(row=0, column=0, sticky="nswe")

    self.__pagination = customtkinter.CTkFrame(
      master=self.__frame_left,
      corner_radius=0
    )
    self.__pagination.grid(row=1, column=0, sticky="nswe")
    self.__pagination.grid_rowconfigure(0, weight=1)
    self.__pagination.grid_columnconfigure(0, weight=1)
    self.__pagination.grid_columnconfigure(6, weight=1)

    self.__first_page = customtkinter.CTkButton(
      master=self.__pagination,
      text=None,
      image=tkinter.PhotoImage(file=IMAGE_DIR.joinpath("first-page-icon.png")),
      width=28,
      command=lambda : threading.Thread(target=self.first_page).start(),
      state=tkinter.DISABLED
    )
    self.__first_page.grid(row=0, column=1)

    self.__prev_page = customtkinter.CTkButton(
      master=self.__pagination,
      text=None,
      image=tkinter.PhotoImage(file=IMAGE_DIR.joinpath("arrow-back-icon.png")),
      width=28,
      command=lambda : threading.Thread(target=self.prev_page).start(),
      state=tkinter.DISABLED
    )
    self.__prev_page.grid(row=0, column=2)

    self.__page_entry = customtkinter.CTkEntry(
      master=self.__pagination,
      textvariable=self.__page_var,
      justify=tkinter.CENTER,
      validate=tkinter.ALL,
      validatecommand=(self.register(self.validate_page_entry), "%P")
    )
    self.__page_entry.grid(row=0, column=3, padx=10)
    self.__page_entry.bind("<FocusOut>", lambda _: self.update_page_var())
    self.__page_entry.bind("<Return>", lambda _: threading.Thread(target=self.go_to_page).start())

    self.__next_page = customtkinter.CTkButton(
      master=self.__pagination,
      text=None,
      image=tkinter.PhotoImage(file=IMAGE_DIR.joinpath("arrow-forward-icon.png")),
      width=28,
      command=lambda : threading.Thread(target=self.next_page).start()
    )
    self.__next_page.grid(row=0, column=4)

    self.__last_page = customtkinter.CTkButton(
      master=self.__pagination,
      text=None,
      image=tkinter.PhotoImage(file=IMAGE_DIR.joinpath("last-page-icon.png")),
      width=28,
      command=lambda : threading.Thread(target=self.last_page).start()
    )
    self.__last_page.grid(row=0, column=5)

    # ===== RIGHT FRAME =====
    self.__frame_right.grid_columnconfigure(0, weight=1)
    self.__frame_right.grid_rowconfigure(0, weight=1)

    self.__media_widget = widgets.VideoPlayer(master=self.__frame_right, verbose=verbose)
    self.__media_widget.grid(row=0, column=0, sticky="nswe")
    self.bind("<space>", lambda _: self.__media_widget.toggle_play())

    # ===== BOTTOM FRAME =====
    self.__frame_bottom.grid_columnconfigure(0, weight=1)
    self.__frame_bottom.grid_rowconfigure(1, weight=1)

    self.__frame_header = customtkinter.CTkFrame(
      master=self.__frame_bottom,
      corner_radius=0
    )
    self.__frame_header.grid(row=0, column=0, sticky="nswe")
    self.__frame_header.grid_columnconfigure(1, weight=2)
    self.__frame_header.grid_columnconfigure(2, weight=1)

    self.__open_in_explorer_pimage = tkinter.PhotoImage(file=IMAGE_DIR.joinpath("folder-open-icon.png"))
    self.__open_in_explorer = tkinter.Label(
      master=self.__frame_header,
      image=self.__open_in_explorer_pimage,
      text=None,
      cursor="arrow",
      bg=customtkinter.ThemeManager.single_color(customtkinter.ThemeManager.theme["color"]["button"], self.appearance_mode)
    )
    self.__open_in_explorer.grid(row=0, column=0)
    self.__open_in_explorer.bind("<Button-1>", lambda _: self.open_in_explorer())

    self.__file_name_var = tkinter.StringVar()
    self.__file_name = customtkinter.CTkLabel(
      master=self.__frame_header,
      textvariable=self.__file_name_var,
      anchor="w",
      justify=tkinter.LEFT
    )
    self.__file_name.grid(row=0, column=1, padx=10, sticky="nswe")
    self.__file_name.grid_propagate(False)

    self.__tag_entry = customtkinter.CTkEntry(
      master=self.__frame_header,
      textvariable=self.__tag_var,
      state=tkinter.DISABLED,
      cursor="arrow",
      validate=tkinter.ALL,
      validatecommand=(self.register(self.validate_tag_entry), "%P"),
      invalidcommand=(self.register(lambda : print("Invalid called")),)
    )
    self.__tag_entry.bind("<Return>", lambda _: self.add_tag())
    self.__tag_entry.grid(row=0, column=2, sticky="nswe")

    self.__frame_body = customtkinter.CTkFrame(
      master=self.__frame_bottom,
      corner_radius=0
    )
    self.__frame_body.grid(row=1, column=0, sticky="nswe")
    self.__frame_body.grid_rowconfigure(0, weight=1)
    self.__frame_body.grid_columnconfigure(0, weight=1)

    self.__collapsible = widgets.Collapsible(
      master=self.__frame_body,
      delete_command=lambda id: print(id),
      id="0",
      root=True,
      value="Tags"
    )
    self.__collapsible.grid(row=0, column=0, sticky="nswe", pady=10)

    # ===== LOAD DATA =====
    self.load_data()

  def add_tag(self):
    thread = threading.Thread(target=self.__add_tag_task)
    thread.start()
    self.focus()
    self.__tag_entry.configure(state=tkinter.DISABLED, cursor="arrow")

  def __add_tag_task(self):
    db_copy = db.DB.copy(self.__my_db)
    image = models.Image.find_one(db_copy, local_path=self.__file_name_var.get())
    new_children = self.__collapsible.get_dict()
    tag_dict = new_children
    tags = self.__tag_var.get().split(":")
    prev_tag = None

    for i, tag_text in enumerate(tags):
      tag = models.Tag.find_one(db_copy, name=tag_text, parent=None if prev_tag is None else prev_tag.id)

      if tag is None:
        tag = models.Tag.create(db_copy, name=tag_text, parent=None if i == 0 else prev_tag.id)

      prev_tag = tag

      level = tag_dict[tag.id] if tag.id in tag_dict else (tag.name, {})
      tag_dict[tag.id] = level
      tag_dict = level[1]

      models.ImageTag.create(db_copy, image=image.id, tag=tag.id)

    self.__collapsible.configure(children=new_children)
    self.__tag_var.set("")
    self.__tag_entry.configure(state=tkinter.NORMAL, cursor="xterm", validate=tkinter.ALL)
    self.__tag_entry.focus()

  def disable_pagination(self):
    self.__first_page.configure(state=tkinter.DISABLED)
    self.__last_page.configure(state=tkinter.DISABLED)
    self.__next_page.configure(state=tkinter.DISABLED)
    self.__prev_page.configure(state=tkinter.DISABLED)
    self.__page_entry.configure(state=tkinter.DISABLED)

  def enable_pagination(self):
    if self.__page != 0:
      self.__first_page.configure(state=tkinter.NORMAL)
      self.__prev_page.configure(state=tkinter.NORMAL)
    if self.__page != self.max_page():
      self.__last_page.configure(state=tkinter.NORMAL)
      self.__next_page.configure(state=tkinter.NORMAL)
    self.__page_entry.configure(state=tkinter.NORMAL)

  def fetch_max_page(self):
    count: int = models.Image.count(db.DB.copy(self.__my_db))
    if self.__verbose:
      print(f"Loaded {count} files")
    self.__max_page = count // self.__entries_per_page

  def finalize_page_change(self):
    self.update_page_var()
    self.load_data()
    self.enable_pagination()

  def first_page(self):
    self.disable_pagination()
    self.__page = 0
    self.finalize_page_change()

  def go_to_page(self):
    text = self.__page_entry.get()
    if len(text) == 0:
      self.focus()
      self.update_page_var()
      return
    page = max(min(int(text) - 1, self.max_page()), 0)
    if page != self.__page:
      self.disable_pagination()
      self.__page = page
      self.focus()
      self.finalize_page_change()

  def last_page(self):
    self.disable_pagination()
    self.__page = self.max_page()
    self.finalize_page_change()

  def load_data(self):
    images: List[models.Image] = models.Image.find_all(
      db.DB.copy(self.__my_db),
      limit=self.__entries_per_page,
      offset=self.__page * self.__entries_per_page,
      local_path="*"
    )
    self.__list_widget.configure(values=[img.local_path for img in images])

  def load_media(self, local_path: str=None):
    if local_path:
      self.__file_name_var.set(local_path)
      thread = threading.Thread(target=self.__load_media_task)
      thread.start()
      self.__open_in_explorer.configure(cursor="hand2")
      self.__media_widget.configure(file=local_path)
    else:
      self.__open_in_explorer.configure(cursor="arrow")
      self.__tag_entry.configure(state=tkinter.DISABLED, cursor="arrow")

  def __load_media_task(self):
    db_copy = db.DB.copy(self.__my_db)
    query = f"SELECT TAG.id, TAG.name, TAG.parent FROM TAG JOIN IMAGETAG ON IMAGETAG.tag == TAG.id JOIN IMAGE ON IMAGE.id == IMAGETAG.image WHERE IMAGE.local_path == '{self.__file_name_var.get()}';"
    tags: List = db_copy.execute(query, db.Fetch.ALL)
    children = {}
    dict_of_dicts = {}

    i = 0

    while i < len(tags):
      tag = tags[i]
      id, name, parent = tag
      dict_of_dicts[id] = {}

      if parent is None:
        children[id] = (name, dict_of_dicts[id])
      elif parent in dict_of_dicts:
        dict_of_dicts[parent][id] = (name, dict_of_dicts[id])
      else:
        tags.append(tag)

      i += 1

    self.__collapsible.configure(children=children)
    self.__tag_entry.configure(state=tkinter.NORMAL, cursor="xterm")
    self.__tag_entry.focus()


  def max_page(self) -> int:
    if self.__max_page == None:
      self.t_max_page.join()
    return self.__max_page

  def next_page(self):
    self.disable_pagination()
    self.__page = min(self.__page + 1, self.max_page())
    self.finalize_page_change()

  def on_closing(self, event=0):
    self.destroy()

  def open_in_explorer(self):
    filename = self.__file_name_var.get()
    if filename:
      subprocess.Popen(f"explorer /select,\"{pathlib.WindowsPath(filename)}\"")

  def prev_page(self):
    self.disable_pagination()
    self.__page = max(self.__page - 1, 0)
    self.finalize_page_change()

  def show(self):
    self.mainloop()

  def update_page_var(self):
    self.__page_var.set(str(self.__page + 1))

  def validate_page_entry(self, value):
    if re.match(r"^\d*$", value) is None:
      return False
    return True

  def validate_tag_entry(self, value: str):
    if re.match(r"^[-:a-z0-9]*$", value):
      return True

    if re.match(r"^[-:a-z0-9]* $", value):
      self.__tag_var.set(self.__tag_var.get() + "-")
    elif re.match(r"^[-:a-z0-9]*[A-Z]$", value):
      self.__tag_var.set(self.__tag_var.get() + value[-1].lower())
    elif re.match(r"^[-:a-z0-9]*;$", value):
      self.__tag_var.set(self.__tag_var.get() + ":")

    self.__tag_entry.entry.icursor(len(self.__tag_var.get()))
    self.__tag_entry.after_idle(lambda: self.__tag_entry.configure(validate=tkinter.ALL))

    return False
