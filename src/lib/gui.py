from typing import List

import tkinter
import customtkinter

import db
import models
import widgets

customtkinter.set_appearance_mode("dark")

class MainWindow(customtkinter.CTk):
  def __init__(self, my_db: db.DB):
    super().__init__()

    self.__my_db = my_db

    self.title("img-manager")
    self.state("zoomed")
    self.protocol("WM_DELETE_WINDOW", self.on_closing)  # call .on_closing() when app gets closed

    # ===== CREATE FRAMES =====

    # Configure grid layout (2x2)
    self.grid_columnconfigure(1, weight=1)
    self.grid_rowconfigure(0, weight=1)

    self.__frame_left = customtkinter.CTkFrame(master=self, width=500, corner_radius=0)
    self.__frame_left.grid(row=0, column=0, rowspan=2, sticky="nswe")

    self.__frame_right = customtkinter.CTkFrame(master=self)
    self.__frame_right.grid(row=0, column=1, sticky="nswe", padx=40, pady=40)

    self.__frame_bottom = customtkinter.CTkFrame(master=self, corner_radius=0)
    self.__frame_bottom.grid(row=1, column=1, sticky="nswe")

    # ===== LEFT FRAME =====
    self.__list_widget = widgets.CTkListbox(master=self.__frame_left, command=lambda x: print(x))
    self.__list_widget.grid(row=0, column=0, sticky="nswe")

    # ===== LOAD DATA =====
    self.load_data()

  def load_data(self):
    images: List[models.Image] = models.Image.find_all(self.__my_db, local_path="*")
    self.__list_widget.configure(values=[img.local_path for img in images])

  def on_closing(self, event=0):
    self.destroy()

  def show(self):
    self.mainloop()
