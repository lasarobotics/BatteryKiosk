import tkinter as tk

import customtkinter as ctk


class App(ctk.CTk):
  def __init__(self):
    super().__init__()

    # Window Configuration
    self.title("Purple Haze Battery Kiosk")
    self.geometry("1024x600")
    self.resizable(False, False)

    # Variables
    self.is_match_mode = tk.BooleanVar(value=True)

    # Initialize Widgets
    self.create_widgets()

  def create_widgets(self):
    # Create match and test battery switch
    self.toggle_switch = ctk.CTkSwitch(
      master=self,
      text="Testing Mode ?",
      bg_color="transparent",
      font=("Arial", 24),
      command=self.toggle_mode(),
      variable=self.is_match_mode,
      onvalue="on",
      offvalue="off",
    )

    # Create battery frames
    self.battery_one_widget = ctk.CTkFrame(
      master=self, width="150", height="200", corner_radius=12
    )

    self.battery_one_widget.bind("<Button-1>", self.select_battery())

    # Position all widgets
    self.battery_one_widget.grid(row=50, column=100, padx=20, pady=20)
    self.toggle_switch.grid(row=0, column=0, padx=100, pady=60)

  def toggle_mode(self):
    if self.is_match_mode:
      ...
    else:
      ...

  def load_match_mode(self): ...

  def load_test_mode(self): ...

  def select_battery(self): ...
