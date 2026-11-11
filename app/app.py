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
      text="Testing Mode",
      bg_color="transparent",
      font=("Arial", 24),
      command=self.toggle_mode(),
      variable=self.is_match_mode,
      onvalue="on",
      offvalue="off",
    )
    self.toggle_switch.grid(padx=50, pady=30)

    self.battery1 = ctk.CTkFrame(master=None, width=50, height=50)
    self.battery2 = ctk.CTkFrame(master=None, width=50, height=50)
    self.battery3 = ctk.CTkFrame(master=None,width=50, height=50)

    self.battery1.grid(padx=250, pady=300)
    self.battery2.grid(padx=500, pady=300)
    self.battery3.grid(padx=750, pady=300)

  def toggle_mode(self):
    if self.is_match_mode:
      ...
    else:
      ...

  def load_match_mode(self): ...

  def load_test_mode(self): ...

  def select_battery(self): ...
