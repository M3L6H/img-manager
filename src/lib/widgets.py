from typing import Callable, Dict, List, Optional, Tuple, Union

import sys
import tkinter
from customtkinter import CTkBaseClass, CTkCanvas, CTkFrame, DrawEngine, Settings, ThemeManager

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
          activebackground=ThemeManager.single_color(self.active_color, self._appearance_mode)
        ))

      self.labels[value][1].bind("<Button-1>", lambda e: self.clicked(value, e))

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
        pady=(self.apply_widget_scaling(self.border_width), self.apply_widget_scaling(self.border_width) + 1)
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