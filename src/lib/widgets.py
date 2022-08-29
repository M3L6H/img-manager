from typing import Callable, Dict, List, Optional, Tuple, Union

import enum
from customtkinter import CTkBaseClass, CTkButton, CTkCanvas, CTkFrame, CTkLabel, CTkScrollbar, DrawEngine, Settings, ThemeManager
import pathlib
from PIL import Image, ImageTk
import sys
import tkinter
import vlc

HOME = pathlib.Path.home()
IMAGE_DIR = HOME.joinpath(".img-manager", "images")
TICK_WIDTH = 1/50

class CTkListbox(CTkBaseClass):
  def __init__(self, *args,
                 bg_color: Union[str, Tuple[str, str], None] = None,
                 fg_color: Union[str, Tuple[str, str], None] = "default_theme",
                 active_color: Union[str, Tuple[str, str], None] = "default_theme",
                 border_color: Union[str, Tuple[str, str]] = "default_theme",
                 text_color: Union[str, Tuple[str, str]] = "default_theme",
                 text_color_disabled: Union[str, Tuple[str, str]] = "default_theme",
                 width: int = 200,
                 height: int = 400,
                 border_width: Union[int, str] = "default_theme",
                 text_font: any = "default_theme",
                 state: str = "normal",
                 selected: int=None,
                 values: List[str]=[],
                 command: Callable[[str], any] = None,
                 **kwargs):
    super().__init__(*args, bg_color=bg_color, width=width, height=height, **kwargs)

    if fg_color == "default_theme":
      if isinstance(self.master, CTkFrame):
        if self.master.fg_color == ThemeManager.theme["color"]["frame_low"]:
          self.fg_color = ThemeManager.theme["color"]["frame_high"]
        else:
          self.fg_color = ThemeManager.theme["color"]["frame_low"]
      else:
        self.fg_color = ThemeManager.theme["color"]["frame_low"]
    else:
      self.fg_color = fg_color

    self.active_color = ThemeManager.theme["color"]["button"] if active_color == "default_theme" else active_color
    self.border_color = ThemeManager.theme["color"]["frame_border"] if border_color == "default_theme" else border_color
    self.text_color = ThemeManager.theme["color"]["text"] if text_color == "default_theme" else text_color
    self.text_color_disabled = ThemeManager.theme["color"]["text_button_disabled"] if text_color_disabled == "default_theme" else text_color_disabled

    self.border_width = ThemeManager.theme["shape"]["frame_border_width"] if border_width == "default_theme" else border_width
    self.text_font = (ThemeManager.theme["text"]["font"], ThemeManager.theme["text"]["size"]) if text_font == "default_theme" else text_font

    self.command = command
    self.selected = selected
    self.labels: Dict[str, Tuple[bool, tkinter.Label]] = {}
    self.values = values
    self.state = state

    # canvas
    self.canvas = CTkCanvas(
      master=self,
      highlightthickness=0,
      width=self.apply_widget_scaling(self._desired_width),
      height=self.apply_widget_scaling(self._desired_height)
    )
    self.draw_engine = DrawEngine(self.canvas)

    # initial draw
    self.configure(cursor=self.get_cursor())
    self.draw()

  def draw(self, no_color_updates=False):
    requires_recoloring = self.draw_engine.draw_rounded_rect_with_border(
      self.apply_widget_scaling(self._current_width),
      self.apply_widget_scaling(self._current_height),
      0,
      self.apply_widget_scaling(self.border_width)
    )

    if no_color_updates is False or requires_recoloring:
      self.canvas.configure(bg=ThemeManager.single_color(self.bg_color, self._appearance_mode))

      # set color for the border parts (outline)
      self.canvas.itemconfig(
        "border_parts",
        outline=ThemeManager.single_color(self.border_color, self._appearance_mode),
        fill=ThemeManager.single_color(self.border_color, self._appearance_mode)
      )

      # set color for selection
      if self.fg_color is None:
        self.canvas.itemconfig(
          "inner_parts",
          outline=ThemeManager.single_color(self.bg_color, self._appearance_mode),
          fill=ThemeManager.single_color(self.bg_color, self._appearance_mode)
        )
      else:
        self.canvas.itemconfig(
          "inner_parts",
          outline=ThemeManager.single_color(self.fg_color, self._appearance_mode),
          fill=ThemeManager.single_color(self.fg_color, self._appearance_mode)
        )

    # Mark all the labels as pending deletion
    for k in self.labels:
      self.labels[k][0] = False

    row = 0

    for value in self.values:
      if value in self.labels:
        self.labels[value][0] = True
        self.labels[value][1].configure(text=value)
      else:
        self.labels[value] = (True, tkinter.Label(
          master=self,
          font=self.apply_font_scaling(self.text_font),
          text=value,
          activebackground=ThemeManager.single_color(self.active_color, self._appearance_mode),
          justify=tkinter.LEFT
        ))

      self.labels[value][1].bind("<Button-1>", lambda e,value=value: self.clicked(value, e))

      if no_color_updates is False:
        self.labels[value][1].configure(fg=ThemeManager.single_color(self.text_color, self._appearance_mode))

        if self.state == tkinter.DISABLED:
          self.labels[value][1].configure(fg=(ThemeManager.single_color(self.text_color_disabled, self._appearance_mode)))
        else:
          self.labels[value][1].configure(fg=ThemeManager.single_color(self.text_color, self._appearance_mode))

        if self.fg_color is None:
          self.labels[value][1].configure(bg=ThemeManager.single_color(self.bg_color, self._appearance_mode))
        else:
          self.labels[value][1].configure(bg=ThemeManager.single_color(self.fg_color, self._appearance_mode))

      self.labels[value][1].grid(
        row=row,
        column=0,
        pady=(self.apply_widget_scaling(self.border_width), self.apply_widget_scaling(self.border_width) + 1),
        sticky="w"
      )

      row += 1

    # Delete the labels of values which are no longer present
    for k in self.labels:
      if not self.labels[k][0]:
        if self.selected == k:
          self.selected = None
        self.labels[k][1].destroy()
        del self.labels[k]

  def configure(self, require_redraw=False, **kwargs):
    if "values" in kwargs:
      self.values = kwargs.pop("values")
      require_redraw = True

    if "state" in kwargs:
      self.state = kwargs.pop("state")
      cursor = self.get_cursor()
      if cursor and "cursor" not in kwargs:
        kwargs["cursor"] = cursor
      require_redraw = True

    if "fg_color" in kwargs:
      self.fg_color = kwargs.pop("fg_color")
      require_redraw = True

    if "border_color" in kwargs:
      self.border_color = kwargs.pop("border_color")
      require_redraw = True

    if "text_color" in kwargs:
      self.text_color = kwargs.pop("text_color")
      require_redraw = True

    if "command" in kwargs:
      self.command = kwargs.pop("command")

    if "width" in kwargs:
      self.set_dimensions(width=kwargs.pop("width"))

    if "height" in kwargs:
      self.set_dimensions(height=kwargs.pop("height"))

    super().configure(require_redraw=require_redraw, **kwargs)

  def get_cursor(self) -> Optional[str]:
    if Settings.cursor_manipulation_enabled:
      if self.state == tkinter.DISABLED:
        if sys.platform == "darwin" and self.command is not None and Settings.cursor_manipulation_enabled:
          return "arrow"
        elif sys.platform.startswith("win") and self.command is not None and Settings.cursor_manipulation_enabled:
          return "arrow"

      elif self.state == tkinter.NORMAL:
        if sys.platform == "darwin" and self.command is not None and Settings.cursor_manipulation_enabled:
          return "pointinghand"
        elif sys.platform.startswith("win") and self.command is not None and Settings.cursor_manipulation_enabled:
          return "hand2"


  def clicked(self, value: str, event=None):
    if self.command:
      if self.state != tkinter.DISABLED and self.selected != value:
        label = self.labels[value][1]
        label.configure(state=tkinter.ACTIVE)

        if self.selected:
          self.labels[self.selected][1].configure(state=tkinter.NORMAL)

        self.selected = value
        self.command(value)

class PlayerState(enum.Enum):
  STOPPED = 0
  PLAYING = 1
  PAUSED = 2

class VideoPlayer(CTkBaseClass):
  def __init__(self, *args,
    bg_color: Union[str, Tuple[str, str], None]=None,
    width: int=1280,
    height: int=720,
    verbose: bool=False,
    **kwargs
  ):
    super().__init__(*args, bg_color=bg_color, width=width, height=height, **kwargs)

    self.grid_rowconfigure(0, weight=1)
    self.grid_columnconfigure(0, weight=1)

    self.canvas = CTkCanvas(
      master=self,
      highlightthickness=0,
      width=self.apply_widget_scaling(self._desired_width),
      height=self.apply_widget_scaling(self._desired_height)
    )
    self.draw_engine = DrawEngine(self.canvas)

    self.top_frame = CTkFrame(master=self)
    self.top_frame.grid(row=0, column=0, sticky="nswe")

    self.img = tkinter.Label(
      master=self.top_frame,
      bg=ThemeManager.single_color(ThemeManager.theme["color"]["frame_low"], self._appearance_mode)
    )
    self.img.pack(fill=tkinter.BOTH, expand=True)

    self.bottom_frame = CTkFrame(master=self)
    self.bottom_frame.grid(row=1, column=0, stick="nswe")
    self.bottom_frame.grid_columnconfigure(1, weight=1)

    self.play_pimage = tkinter.PhotoImage(file=IMAGE_DIR.joinpath("play-icon.png"))
    self.pause_pimage = tkinter.PhotoImage(file=IMAGE_DIR.joinpath("pause-icon.png"))
    self.play_button = CTkButton(
      master=self.bottom_frame,
      command=self.toggle_play,
      cursor="hand2",
      image=self.play_pimage,
      text="",
      width=28
    )
    self.play_button.grid(row=0, column=0, sticky="nswe")

    self.seeker_bg = CTkFrame(
      master=self.bottom_frame,
      height=28
    )
    self.seeker_bg.grid(row=0, column=1, sticky="nswe", padx=10)

    self.tick = CTkScrollbar(
      master=self.seeker_bg,
      orientation="horizontal",
      command=self.seek
    )
    self.tick.pack(fill=tkinter.BOTH, expand=True)
    self.tick.canvas.bind("<MouseWheel>", None)

    self.timestamp = CTkLabel(
      master=self.bottom_frame,
      text="00:00"
    )
    self.timestamp.grid(row=0, column=2, sticky="nswe")

    self.player_instance = vlc.Instance()
    self.player: vlc.MediaPlayer = self.player_instance.media_player_new()
    self.player.set_hwnd(self.top_frame.winfo_id())
    e_manager: vlc.EventManager = self.player.event_manager()
    e_manager.event_attach(vlc.EventType.MediaPlayerTimeChanged, lambda _: self.video_time_changed())
    e_manager.event_attach(vlc.EventType.MediaPlayerEndReached, lambda _: self.video_end())

    self.dest = None
    self.state = PlayerState.STOPPED
    self.verbose = verbose

  def configure(self, require_redraw=False, **kwargs):
    if "file" in kwargs:
      if self.state != PlayerState.STOPPED:
        self.stop()

      file = kwargs.pop("file")
      try:
        self.dest = None
        im = Image.open(file)
        im.verify()
        load = Image.open(file)
        image = ImageTk.PhotoImage(load)
        self.img.configure(image=image)
        self.img.image = image
        load.close()
        require_redraw = True
      except:
        self.dest = file
        self.play()

    if "width" in kwargs:
      self.set_dimensions(width=kwargs.pop("width"))

    if "height" in kwargs:
      self.set_dimensions(height=kwargs.pop("height"))

    super().configure(require_redraw=require_redraw, **kwargs)

  def play(self):
    if self.dest is None or self.state == PlayerState.PLAYING:
      return

    self.state = PlayerState.PLAYING

    if self.state != PlayerState.PAUSED:
      self.player.set_media(self.player_instance.media_new(self.dest))

    self.player.play()
    self.play_button.configure(image=self.pause_pimage)
    self.tick.set(0, TICK_WIDTH)

  def pause(self):
    if self.state == PlayerState.PLAYING:
      self.state = PlayerState.PAUSED
      self.player.pause()
      self.play_button.configure(image=self.play_pimage)

  def seek(self, _, pos):
    self.pause()
    place = pos / (1 - TICK_WIDTH)
    self.player.set_position(place)
    self.update_timestamp(place)

  def stop(self):
    if self.state != PlayerState.PLAYING:
      return

    self.player.stop()
    self.video_end()

  def toggle_play(self):
    if self.state == PlayerState.PAUSED:
      self.state = PlayerState.PLAYING
      self.player.pause()
      self.play_button.configure(image=self.pause_pimage)
    elif self.state == PlayerState.PLAYING:
      self.pause()
    elif self.state == PlayerState.STOPPED:
      self.play()

  def update_timestamp(self, pos: float):
    video_length = self.player.get_length() / 1000
    seconds = int(pos * video_length)
    minutes = seconds // 60
    hours = minutes // 60
    seconds %= 60

    text = f"{minutes:02d}:{seconds:02d}"

    if video_length // 3600 > 0:
      text = f"{hours:02d}:{text}"

    self.timestamp.configure(text=text)

  def video_end(self):
    self.play_button.configure(image=self.play_pimage)
    self.state = PlayerState.STOPPED
    self.tick.set(0, 1)

  def video_time_changed(self):
    scale = 1 - TICK_WIDTH
    pos = self.player.get_position()
    scaled_pos = pos * scale
    self.tick.set(scaled_pos, scaled_pos + TICK_WIDTH)

    self.update_timestamp(pos)
