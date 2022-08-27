from typing import Callable, Dict, List, Optional, Tuple, Union

import contextlib
import enum
from customtkinter import CTkBaseClass, CTkCanvas, CTkFrame, DrawEngine, Settings, ThemeManager
import cv2
from ffpyplayer.player import MediaPlayer
import os
from PIL import Image, ImageTk
import queue
import sys
import tempfile
import threading
import time
import tkinter

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

    self.img = tkinter.Label(
      master=self
    )
    self.img.grid(row=0, column=0, sticky="nswe")
    self.img.bind("<Button-1>", lambda _: self.kill())

    self.player = None
    self.state = PlayerState.STOPPED
    self.t1 = None
    self.t2 = None
    self.t3 = None
    self.t4 = None
    self.verbose = verbose

  def configure(self, require_redraw=False, **kwargs):
    if "file" in kwargs:
      if self.state != PlayerState.STOPPED:
        self.kill()

      file = kwargs.pop("file")
      try:
        im = Image.open(file)
        im.verify()
        if "image" not in kwargs:
          kwargs["image"] = file
      except:
        self.dest = file
        self.cap = cv2.VideoCapture(self.dest)

        self.frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)

        self.play()

    if "image" in kwargs:
      try:
        load = Image.open(kwargs.pop("image"))
        image = ImageTk.PhotoImage(load)
        self.img.configure(image=image)
        self.img.image = image
        load.close()
        require_redraw = True
      except:
        pass

    if "width" in kwargs:
      self.set_dimensions(width=kwargs.pop("width"))

    if "height" in kwargs:
      self.set_dimensions(height=kwargs.pop("height"))

    super().configure(require_redraw=require_redraw, **kwargs)

  def play(self):
    if self.dest is None or self.state == PlayerState.PLAYING:
      return

    self.state = PlayerState.PLAYING
    self.fr_lock = threading.Lock()
    self.frames_read = queue.Queue()
    self.frame_files = queue.Queue() # list of temp files
    self.frame_times = []
    self.kill_threads = False

    self.player = MediaPlayer(self.dest)
    self.player.set_pause(True)

    self.t1 = threading.Thread(target=self.readFrames)
    self.t2 = threading.Thread(target=self.writeFrames)
    self.t3 = threading.Thread(target=self.writeFrames)
    self.t4 = threading.Thread(target=self.playVideo)

    self.t1.start()
    self.t2.start()
    self.t3.start()
    self.t4.start()

  def kill(self):
    if self.verbose:
      print("Joining threads")

    self.kill_threads = True
    if self.t1:
      self.t1.join()

    self.state = PlayerState.STOPPED

  def generateFrameTimes(self):
    newFrames = self.frames

    targetTime = 1/self.fps
    times = 0

    for _ in range(newFrames):
      self.frame_times.append(times)
      times += targetTime

  def readFrames(self):
    self.generateFrameTimes()
    while(self.cap.isOpened()):
      if(self.kill_threads == True):
        self.t2.join()
        self.t3.join()
        if self.verbose:
          print("Read thread terminated")
        return

      if(self.frames_read.qsize() > 10):
        time.sleep(.01)
        continue

      ret, frame = self.cap.read()
      if ret == True:
        self.frames_read.put(frame)
      else:
        break

    if self.verbose:
      print("Read thread terminated")

  # https://stackoverflow.com/questions/13379742/
  # right-way-to-clean-up-a-temporary-folder-in-python-class
  @contextlib.contextmanager
  def make_temp_directory(self):
    temp_dir = tempfile.TemporaryDirectory()
    try:
      yield temp_dir
    finally:
      temp_dir.cleanup()

  def writeFrames(self):
    time.sleep(1)
    with self.make_temp_directory() as temp_dir:
      while True:
        if(self.kill_threads == True):
          self.t4.join()
          try:
            temp_dir.cleanup()
          except:
            pass

          if self.verbose:
            print("Write thread terminated")
          return

        if self.frame_files.qsize() > 20:
          time.sleep(.1)
          continue

        p = tempfile.NamedTemporaryFile('wb', suffix = '.jpg',
                                        dir = temp_dir.name,
                                        delete = False)

        with self.fr_lock:
          if self.frames_read.empty():
            break

          frame = self.frames_read.get()
          self.frame_files.put(p)

        frame = cv2.resize(frame, (self._desired_width,self._desired_height),
                            interpolation = cv2.INTER_AREA)

        cv2.imwrite(p.name,frame)
        p.close()

    if self.verbose:
      print("Write thread terminated")

  def playVideo(self):
    while(self.frame_files.empty()):
      if(self.kill_threads == True):
        if self.verbose:
          print("Play thread terminated")
        return
      time.sleep(0.5)

    fps = self.fps
    print(fps)
    targetTime = 1/fps

    pop = None

    # load up the audio
    self.player.set_pause(False)
    audio_frame, val = self.player.get_frame()
    while audio_frame == None:
      if(self.kill_threads == True):
        if self.verbose:
          self.player.set_pause(True)
          print("Play thread terminated")
        return
      audio_frame, val = self.player.get_frame()

    running_time = time.time()

    while(not self.frame_files.empty()):
      if(self.kill_threads):
        if self.verbose:
          self.player.set_pause(True)
          print("Play thread terminated")
        return

      audio_frame, val = self.player.get_frame()

      if(val == 'eof' or len(self.frame_times) == 0):
        break

      if(audio_frame == None):
        continue

      # for any lag due to cpu, especially for dragging
      # if(self.frame_files.qsize() < 5):
      #   time.sleep(.08)

      t = self.frame_times.pop(0)
      pop: tempfile._TemporaryFileWrapper = self.frame_files.get()

      cur_time = time.time() - running_time
      delay = t - cur_time

      # frame skipping
      if (delay < -targetTime):
        os.remove(pop.name)
        continue

      # diplay image
      self.configure(image=pop.name)
      pop.close()

      os.remove(pop.name)

      cur_time = time.time() - running_time
      delay = t - cur_time

      if (delay > targetTime):
        time.sleep(targetTime)

    # self.kill()
    if self.verbose:
      print("Play thread terminated")
