from typing import Callable, Dict, List, Tuple, Union

from canvas_image import CanvasImage
import copy
import enum
from customtkinter import CTkBaseClass, CTkButton, CTkEntry, CTkFrame, CTkLabel, CTkScrollbar, DrawEngine, ThemeManager
import pathlib
from PIL import Image, UnidentifiedImageError
import re
import tkinter
import vlc

Image.MAX_IMAGE_PIXELS = None

HOME = pathlib.Path.home()
IMAGE_DIR = HOME.joinpath(".img-manager", "images")
TICK_WIDTH = 1/50

class CTkAutocompleteEntry(CTkEntry):
  def __init__(self, *args,
    tree: Dict[str, Dict]={},
    **kwargs
  ):
    super().__init__(*args, **kwargs)

    self.__autofilled = False
    self.__tree = tree

    self.entry.bind("<Key>", self.__key_down)
    self.entry.bind("<KeyRelease>", self.__key_press)
    self.entry.bind("<Tab>", self.__tab)

  def configure(self, require_redraw=False, **kwargs):
    if "tree" in kwargs:
      self.__tree = kwargs.pop("tree")

    super().configure(require_redraw=require_redraw, **kwargs)

  def __key_down(self, _):
    if self.__autofilled:
      self.entry.delete(self.entry.index(tkinter.INSERT), tkinter.END)

  def __key_press(self, e):
    if len(e.keysym) == 1 or e.keysym in ["BackSpace", "colon"]:
      parts = self.textvariable.get().split(":")
      tree = self.__tree

      for part in parts[:-1]:
        if part in tree:
          tree = tree[part]
        else:
          return

      matches = [k for k in tree if re.match(f"{parts[-1]}.+", k)]

      if len(matches) > 0:
        parts[-1] = matches[0]
        self.textvariable.set(":".join(parts))
        self.after_idle(lambda: self.entry.configure(validate=tkinter.ALL))
        self.__autofilled = True
      else:
        self.__autofilled = False

  def __tab(self, e):
    old_value = self.textvariable.get()

    if not self.__autofilled and old_value[-1] != ":":
      self.textvariable.set(old_value + ":")
      self.entry.icursor(len(old_value) + 1)
      e.keysym = "colon"
      self.__key_press(e)
      self.after_idle(lambda: self.entry.configure(validate=tkinter.ALL))
    else:
      self.__autofilled = False
      self.entry.icursor(len(self.textvariable.get()))

    return "break"

class CTkAutoScrollbar(CTkScrollbar):
  def __init__(self, *args,
    side: str=tkinter.RIGHT,
    **kwargs
  ):
    super().__init__(*args, **kwargs)

    self.__grid = False
    self.side = side

  def grid(self, **kwargs):
    self.__grid = True
    super().grid(**kwargs)

  def set(self, lo: int, hi: int):
    if float(lo) <= 0.0 and float(hi) >= 1.0:
      if self.__grid:
        self.grid_remove()
      else:
        self.pack_forget()
    else:
      if self.__grid:
        self.grid()
      else:
        self.pack(side=self.side, fill="y")
      super().set(lo, hi)

class CTkLabelButton(CTkLabel):
  def __init__(self, *args,
    command: Callable[[tkinter.Event], any]=None,
    state: str=tkinter.NORMAL,
    **kwargs
  ):
    if "bg_color" in kwargs:
      bg_color = kwargs.pop("bg_color")
    else:
      bg_color = ThemeManager.theme["color"]["button"]

    if "cursor" in kwargs:
      cursor = kwargs.pop("cursor")
    else:
      cursor = "arrow" if state == tkinter.DISABLED else "hand2"

    if "text" in kwargs:
      kwargs.pop("text")

    if "width" in kwargs:
      kwargs.pop("width")

    super().__init__(*args, bg_color=bg_color, cursor=cursor, text=None, width=28, **kwargs)

    self.__command = command
    self.state = state

    self.text_label.bind("<Button-1>", self.__command)
    self.bind("<Enter>", lambda _: self.__hover())
    self.bind("<Leave>", lambda _: self.__unhover())

  def configure(self, **kwargs):
    if "state" in kwargs:
      self.state = kwargs.pop("state")
      if self.state == tkinter.DISABLED or self.__command is None:
        kwargs["cursor"] = "arrow"
      else:
        kwargs["cursor"] = "hand2"

    super().configure(**kwargs)

  def __hover(self):
    if self.state == tkinter.DISABLED or self.__command is None: return
    self.configure(bg_color=ThemeManager.theme["color"]["button_hover"])

  def __unhover(self):
    self.configure(bg_color=ThemeManager.theme["color"]["button"])

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
                 state: str = tkinter.NORMAL,
                 selected: int=None,
                 values: List[Tuple[int, str]]=[],
                 command: Callable[[str], any]=None,
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
    self.labels: List[tkinter.Label] = []
    self.values = values
    self.state = state

    # configure
    self.grid_rowconfigure(0, weight=1)
    self.grid_columnconfigure(0, weight=1)

    # canvas
    self.canvas = tkinter.Canvas(
      master=self,
      highlightthickness=0,
      width=self.apply_widget_scaling(self._desired_width),
      height=self.apply_widget_scaling(self._desired_height)
    )
    self.canvas.grid(row=0, column=0, sticky="nswe")
    self.draw_engine = DrawEngine(self.canvas)

    # inner frame
    self.__container = tkinter.Frame(
      master=self.canvas
    )
    self.__container.bind("<Configure>", lambda _: self.update_canvas())
    self.__scrollbar = CTkAutoScrollbar(
      master=self,
      command=self.canvas.yview
    )
    self.__scrollbar.grid(row=0, column=1, sticky="ns")
    self.canvas.configure(yscrollcommand=self.__scrollbar.set)

    self.canvas.create_window((0, 0), window=self.__container, anchor="nw")

    # initial draw
    self.configure(cursor="arrow")
    self.draw()

  def draw(self, no_color_updates=False):
    self.__container.grid_columnconfigure(0, minsize=self.canvas.winfo_width(), weight=1)

    if no_color_updates is False:
      self.canvas.configure(bg=ThemeManager.single_color(self.bg_color, self._appearance_mode))

    for i, (_, value) in enumerate(self.values):
      if i < len(self.labels):
        self.labels[i].configure(text=value, state=tkinter.NORMAL)
      else:
        self.labels.append(tkinter.Label(
          master=self.__container,
          font=self.apply_font_scaling(self.text_font),
          text=value,
          activebackground=ThemeManager.single_color(self.active_color, self._appearance_mode),
          justify=tkinter.RIGHT,
          anchor="e",
          cursor="hand2"
        ))

      self.labels[i].bind("<Button-1>", lambda _,i=i: self.clicked(i))
      self.labels[i].bind("<Enter>", lambda _,i=i: self.__highlight(i))
      self.labels[i].bind("<Leave>", lambda _,i=i: self.__unhighlight(i))

      if no_color_updates is False:
        self.labels[i].configure(fg=ThemeManager.single_color(self.text_color, self._appearance_mode))

        if self.state == tkinter.DISABLED:
          self.labels[i].configure(fg=ThemeManager.single_color(self.text_color_disabled, self._appearance_mode))
        else:
          self.labels[i].configure(fg=ThemeManager.single_color(self.text_color, self._appearance_mode))

        if i % 2 == 0 and self.selected != i:
          self.labels[i].configure(bg=ThemeManager.single_color(self.bg_color, self._appearance_mode))
        else:
          self.labels[i].configure(bg=ThemeManager.single_color(self.fg_color, self._appearance_mode))

      self.labels[i].grid(row=i, column=0, sticky="we")

    # Hide unused labels
    for i in range(len(self.labels)):
      if i >= len(self.values):
        self.labels[i].grid_remove()

    self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    self.canvas.update()
    self.canvas.xview_moveto(1.0)

  def configure(self, require_redraw=False, **kwargs):
    if "values" in kwargs:
      self.values = kwargs.pop("values")
      self.selected = None
      require_redraw = True

    if "state" in kwargs:
      self.state = kwargs.pop("state")
      cursor = self.get_cursor()
      if cursor and "cursor" not in kwargs:
        kwargs["cursor"] = cursor

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

  def clicked(self, i: int):
    id, _ = self.values[i]
    if self.command:
      if self.state != tkinter.DISABLED and self.selected != i:
        label = self.labels[i]
        label.configure(state=tkinter.ACTIVE, cursor="arrow")

        if self.selected is not None:
          self.labels[self.selected].configure(state=tkinter.NORMAL, cursor="hand2")

        self.selected = i
        self.command(id)

  def get_cursor(self):
    return "hand2" if self.state == tkinter.NORMAL else "arrow"

  def __highlight(self, i: int):
    if self.state != tkinter.DISABLED:
      self.labels[i].configure(bg=ThemeManager.single_color(self.active_color, self._appearance_mode))

  def __unhighlight(self, i: int):
    if i % 2 == 0:
      self.labels[i].configure(bg=ThemeManager.single_color(self.bg_color, self._appearance_mode))
    else:
      self.labels[i].configure(bg=ThemeManager.single_color(self.fg_color, self._appearance_mode))

  def update_canvas(self):
    self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    self.canvas.xview_moveto(1.0)

class CollapsibleState(enum.Enum):
  COLLAPSED = 0
  OPEN = 1

class Collapsible(CTkBaseClass):
  def __init__(self, *args,
    bg_color: Union[str, Tuple[str, str], None]=None,
    fg_color: Union[str, Tuple[str, str], None]="default_theme",
    children: Dict[str, Tuple[str, Dict]]={},
    delete_command: Union[Callable[[str], any], List[Callable[[str], any]]]=[],
    height: int=50,
    id: str="",
    root: bool=False,
    state: CollapsibleState=CollapsibleState.COLLAPSED,
    value: str="",
    width: int=300,
    **kwargs
  ):
    super().__init__(*args, bg_color=bg_color, height=height, width=width, **kwargs)

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

    self.__children = children
    self.__child_collapsibles: List["Collapsible"] = []
    self.__delete_command = delete_command if isinstance(delete_command, list) else [delete_command]
    self.__id = id
    self.__root = root
    self.__state = state

    self.grid_rowconfigure(1, weight=1)
    self.grid_columnconfigure(0, weight=1)

    self.__header = CTkFrame(
      master=self,
      corner_radius=0,
      cursor="hand2" if len(self.__children) > 0 else "arrow",
      fg_color=self.fg_color
    )
    self.__header.grid(row=0, column=0, columnspan=2, sticky="nswe")
    self.__header.grid_rowconfigure(0, weight=1)

    self.__caret_down_pimage = tkinter.PhotoImage(file=IMAGE_DIR.joinpath("caret-down-icon.png"))
    self.__caret_right_pimage = tkinter.PhotoImage(file=IMAGE_DIR.joinpath("caret-right-icon.png"))
    self.__caret = CTkLabelButton(
      master=self.__header,
      command=lambda _: self.toggle_state(),
      image=self.__caret_down_pimage if state == CollapsibleState.OPEN else self.__caret_right_pimage
    )
    self.__caret.grid(row=0, column=0)

    self.__value_var = tkinter.StringVar(value=value)
    self.__label = CTkLabel(
      master=self.__header,
      textvariable=self.__value_var
    )
    self.__label.grid(row=0, column=1, sticky="nswe")

    container_kwargs = {
      "corner_radius": 0,
      "fg_color": self.fg_color
    }

    if self.__root:
      self.canvas = tkinter.Canvas(
        master=self,
        highlightthickness=0,
        width=self.apply_widget_scaling(self._desired_width),
        height=self.apply_widget_scaling(self._desired_height)
      )
      self.canvas.grid(row=1, column=0, sticky="nswe", padx=(10, 0))
      self.canvas.bind("<Enter>", lambda _: self.__enter())
      self.canvas.bind("<Leave>", lambda _: self.__leave())
      self.draw_engine = DrawEngine(self.canvas)

      self.__container = CTkFrame(master=self.canvas, **container_kwargs)
      self.__container.bind("<Configure>", lambda _: self.update_canvas())

      self.__scrollbar = CTkAutoScrollbar(
        master=self,
        command=self.canvas.yview
      )
      self.__scrollbar.grid(row=1, column=1, sticky="ns")
      self.canvas.configure(yscrollcommand=self.__special_set)

      self.canvas.create_window((0, 0), window=self.__container, anchor="nw")
    else:
      self.__container = CTkFrame(master=self, **container_kwargs)

      self.__delete_pimage = tkinter.PhotoImage(file=IMAGE_DIR.joinpath("delete-icon.png"))
      self.__delete_label = tkinter.Label(
        master=self.__header,
        image=self.__delete_pimage,
        text=None,
        cursor="hand2",
        bg=ThemeManager.single_color(ThemeManager.theme["color"]["button"], self._appearance_mode)
      )
      self.__delete_label.grid(row=0, column=2)
      if len(self.__delete_command) > 0:
        self.__delete_label.bind("<Button-1>", lambda _: self.delete())
      self.__container.grid(row=1, column=0, sticky="nswe", padx=(10, 0))

    self.__container.grid_columnconfigure(0, weight=1)

    if len(self.__children) == 0:
      self.__caret.grid_remove()
      self.__hide()
    else:
      self.__header.canvas.bind("<Button-1>", lambda _: self.toggle_state())

    if self.__state == CollapsibleState.COLLAPSED:
      self.__hide()

    # Initial draw
    self.draw()

  def configure(self, require_redraw=False, **kwargs):
    if "delete_command" in kwargs:
      delete_command = kwargs.pop("delete_command")

      if delete_command is None:
        self.__delete_command = []
        self.__delete_label.grid_remove()
      else:
        self.__delete_command = delete_command if isinstance(delete_command, list) else [delete_command]
        self.__delete_label.grid()

    if "id" in kwargs:
      self.__id = kwargs.pop("id")

    if "state" in kwargs:
      self.__state = kwargs.pop("state")

      if self.__state == CollapsibleState.OPEN:
        self.__show()
        self.__caret.configure(image=self.__caret_down_pimage)
      else:
        self.__hide()
        self.__caret.configure(image=self.__caret_right_pimage)

      require_redraw = True

    if "children" in kwargs:
      children = kwargs.pop("children")

      require_redraw = require_redraw or children != self.__children

      self.__children: Dict[str, Tuple[str, Dict]] = children

      if self.__children is None:
        self.__children = []

      if len(self.__children) == 0:
        self.__caret.grid_remove()
        self.__hide()
        self.__header.canvas.bind("<Button-1>", None)
        self.__header.configure(cursor="arrow")
      else:
        self.__caret.grid()
        self.__header.canvas.bind("<Button-1>", lambda _: self.toggle_state())
        self.__header.configure(cursor="hand2")

        if self.__state == CollapsibleState.OPEN:
          self.__show()
        else:
          self.__hide()

    if "value" in kwargs:
      self.__value_var.set(kwargs.pop("value"))
      require_redraw = True

    super().configure(require_redraw=require_redraw, **kwargs)

  def delete(self):
    queue = [self.__children]
    to_delete = [self.__id]
    for d in queue:
      for id in d:
        to_delete.append(id)
        queue.append(d[id][1])
    for i in range(len(self.__delete_command) - 1):
      cmd = self.__delete_command[i]
      cmd(self.__id)
    for id in to_delete:
      self.__delete_command[-1](id)

  def delete_command_prefix(self, id: str):
    del self.__children[id]
    self.configure(require_redraw=True, children=self.__children)

  def destroy(self):
    for child in self.__child_collapsibles:
      child.destroy()
    super().destroy()

  def draw(self, no_color_updates=False):
    if no_color_updates is False and self.__root:
      self.canvas.configure(bg=ThemeManager.single_color(self.bg_color, self._appearance_mode))

    i = 0
    alphabetical_list = sorted([(id, *self.__children[id]) for id in self.__children], key=lambda t: t[1])

    for id, value, children in alphabetical_list:
      if i < len(self.__child_collapsibles):
        self.__child_collapsibles[i].configure(
          children=children,
          delete_command=[self.delete_command_prefix, self.__delete_command[-1]],
          id=id,
          value=value
        )
      else:
        self.__child_collapsibles.append(Collapsible(
          master=self.__container,
          children=children,
          delete_command=[self.delete_command_prefix, self.__delete_command[-1]],
          id=id,
          value=value
        ))

      self.__child_collapsibles[i].grid(row=i, column=0, sticky="nswe")
      i += 1

    # Remove unused children
    for i in range(len(self.__child_collapsibles)):
      if i >= len(self.__children):
        self.__child_collapsibles[i].destroy()
    self.__child_collapsibles = self.__child_collapsibles[:len(self.__children)]

  def __enter(self):
    self.__mousewheel_bind()

  def get_dict(self) -> Dict[str, Tuple[str, Dict]]:
    return copy.deepcopy(self.__children)

  def get_header(self) -> CTkFrame:
    return self.__header

  def __hide(self):
    if self.__root:
      self.canvas.grid_remove()
      self.after_idle(self.update_canvas)
    else:
      self.__container.grid_remove()

  def insert(self, child: Dict[str, Tuple[str, Dict]]):
    self.__insert(child, self.__children)

  def __insert(self, child: Dict[str, Tuple[str, Dict]], tree: Dict[str, Tuple[str, Dict]]):
    for k in child:
      if k in tree:
        self.__insert(child[k][1], tree[k])
      else:
        tree[k] = child[k]

  def __leave(self):
    self.__mousewheel_unbind()

  def __mousewheel(self, e):
    self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

  def __mousewheel_bind(self):
    self.canvas.bind_all("<MouseWheel>", self.__mousewheel)

  def __mousewheel_unbind(self):
    self.canvas.unbind_all("<MouseWheel>")

  def __show(self):
    if self.__root:
      self.canvas.grid()
    else:
      self.__container.grid()

  def __special_set(self, *args):
    if self.__state == CollapsibleState.OPEN:
      self.__scrollbar.set(*args)

  def toggle_state(self):
    if self.__state == CollapsibleState.COLLAPSED:
      self.configure(state=CollapsibleState.OPEN)
    else:
      self.configure(state=CollapsibleState.COLLAPSED)

  def update_canvas(self):
    if self.__state == CollapsibleState.COLLAPSED:
      self.__scrollbar.set(0, 1)
    else:
      self.canvas.configure(scrollregion=self.canvas.bbox("all"))

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

    self.top_frame = CTkFrame(master=self)
    self.top_frame.grid_rowconfigure(0, weight=1)
    self.top_frame.grid_columnconfigure(0, weight=1)
    self.top_frame.grid(row=0, column=0, sticky="nswe")

    self.img = CanvasImage(
      master=self.top_frame,
      bg=ThemeManager.single_color(ThemeManager.theme["color"]["frame_low"], self._appearance_mode)
    )
    self.img.grid(row=0, column=0)

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

    self.bottom_frame.grid_remove()
    self.dest = None
    self.state = PlayerState.STOPPED
    self.verbose = verbose

  def configure(self, require_redraw=False, **kwargs):
    if "file" in kwargs:
      if self.state != PlayerState.STOPPED:
        self.stop()

      file = kwargs.pop("file")
      try:
        self.bottom_frame.grid_remove()
        self.dest = None
        im = Image.open(file)
        im.verify()
        self.img.configure(image=file)
        require_redraw = True
      except UnidentifiedImageError:
        self.bottom_frame.grid()
        self.dest = file
        self.img.configure(image=None)
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
    self.timestamp.configure(text="00:00")

  def video_time_changed(self):
    scale = 1 - TICK_WIDTH
    pos = self.player.get_position()
    scaled_pos = pos * scale
    self.tick.set(scaled_pos, scaled_pos + TICK_WIDTH)

    self.update_timestamp(pos)
