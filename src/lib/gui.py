import tkinter
import customtkinter

customtkinter.set_appearance_mode("dark")
customtkinter.set_default_color_theme("green")

class MainWindow(customtkinter.CTk):
  def __init__(self):
    super().__init__()

    self.title("img-manager")
    self.state("zoomed")
    self.protocol("WM_DELETE_WINDOW", self.on_closing)  # call .on_closing() when app gets closed

    # ===== CREATE FRAMES =====

    # Configure grid layout (2x2)
    self.grid_columnconfigure(1, weight=1)
    self.grid_rowconfigure(1, weight=1)

    self.__frame_left = customtkinter.CTkFrame(master=self, width=320, corner_radius=0)
    self.__frame_left.grid(row=0, column=0, rowspan=2, sticky="nswe")

    self.__frame_right = customtkinter.CTkFrame(master=self)
    self.__frame_right.grid(row=0, column=1, sticky="nswe", padx=40, pady=40)

    self.__frame_bottom = customtkinter.CTkFrame(master=self)
    self.__frame_bottom.grid(row=1, column=1, sticky="nswe")

  def show(self):
    self.mainloop()

  def on_closing(self, event=0):
    self.destroy()
