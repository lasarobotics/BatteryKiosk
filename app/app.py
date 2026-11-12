import tkinter as tk

import customtkinter as ctk
from PIL import Image

from app.bfg_can import PWFCanBus


class App(ctk.CTk):
  def __init__(self):
    super().__init__()

    # Window Configuration
    self.title("Purple Haze Battery Kiosk")
    self.geometry("1024x600")
    self.configure(fg_color="#882fed")
    self.resizable(False, False)

    # Variables
    self.is_match_mode = tk.BooleanVar(value=True)
    self.bus = PWFCanBus()
    # Initialize Widgets
    self.create_widgets()

    # Start update loop
    self.select_batteries()

  def create_widgets(self):

    # Create match and test battery switch

    self.toggle_switch = ctk.CTkCheckBox(
      master=self,
      text="Testing Mode",
      bg_color="transparent",
      font=("Arial", 24),
      command=self.toggle_mode,
      variable=self.is_match_mode,
      onvalue=False,
      offvalue=True,
      checkbox_width=24,
      checkbox_height=24,
      corner_radius=5,
    )

    self.toggle_switch.grid(row=1, column=0, padx=20, pady=20)

    # Create Image
    self.first_logo_file = ctk.CTkImage(
      light_image=Image.open("app/Assets/FIRST_Logo.svg.webp"), size=(150, 150)
    )
    self.second_logo_file = ctk.CTkImage(
      light_image=Image.open("app/Assets/SecondLogo.png"), size=(150, 150)
    )
    # Display image with a transparent background
    self.first_logo_display = ctk.CTkLabel(
      master=self, image=self.first_logo_file, text="", fg_color="transparent"
    )
    self.second_logo_display = ctk.CTkLabel(
      master=self, image=self.second_logo_file, text=""
    )

    self.first_logo_display.grid(row=1, column=1, padx=0, pady=40)

    text1 = ctk.CTkTextbox(
      master=self,
      width=160,
      height=60,
      corner_radius=5,
      font=("Cambria Math", 48, "bold"),
      fg_color="transparent",
      bg_color="transparent",
      text_color="black",
    )
    text1.insert("0.0", "2nd")
    text1.place(x=140, y=225)

    text2 = ctk.CTkTextbox(
      master=self,
      width=160,
      height=60,
      corner_radius=5,
      font=("Cambria Math", 48, "bold"),
      fg_color="transparent",
      bg_color="transparent",
      text_color="black",
    )
    text2.insert("0.0", "3rd")
    text2.place(x=815, y=275)

    # Create battery frames
    self.battery_one_widget = ctk.CTkFrame(
      master=self, width=150, height=200, corner_radius=12
    )
    self.toggle_switch.grid(row=0, column=0, padx=20, pady=20)

    self.battery1 = ctk.CTkFrame(
      master=self,
      width=300,
      height=200,
      border_width=7,
      border_color="#838587",
      fg_color="#e3e2e1",
    )
    self.battery2 = ctk.CTkFrame(
      master=self,
      width=360,
      height=240,
      border_width=7,
      border_color="#8c7304",
      fg_color="#e8b50c",
    )
    self.battery3 = ctk.CTkFrame(
      master=self,
      width=240,
      height=160,
      border_width=7,
      border_color="#80450b",
      fg_color="#d4700d",
    )

    self.battery1.grid(row=2, column=0, padx=(42, 10), pady=(0, 100), stick="s")
    self.battery2.grid(row=2, column=1, padx=10, pady=(0, 100), stick="s")
    self.battery3.grid(row=2, column=2, padx=(10, 42), pady=(0, 100), stick="s")

  def toggle_mode(self):
    if self.is_match_mode.get():
      self.configure(fg_color="#882fed")
      self.second_logo_display.grid_remove()
      self.first_logo_display.grid(row=1, column=1, padx=0, pady=40)
    else:
      self.configure(fg_color="#DE2020")
      self.first_logo_display.grid_remove()
      self.second_logo_display.grid(row=1, column=1, padx=0, pady=40)

  def select_batteries(self):
    self.discovered_batteries = self.bus.discovered_bfgs()
    if self.discovered_batteries:
      self.batteries = [
        self.bus.get_bfg(battery.id) for battery in self.bus.discovered_bfgs()
      ]
      if self.is_match_mode.get():
        self.find_match_batteries(self.batteries)
      else:
        self.find_testing_batteries(self.batteries)
    self.after(1000, self.select_batteries)

  # Returns 3 batteries (in descending order of voltage)
  def find_match_batteries(batteries):
    highest_voltage_batteries = sorted(
      batteries, key=lambda battery: battery.voltage, reverse=True
    )[:3]
    return highest_voltage_batteries

  # Returns 3 batteries (in ascending number of cycles)
  def find_testing_batteries(self, batteries):
    highest_voltage_batteries = self.find_match_batteries()
    batteries_excluding_highest_voltages = [
      battery for battery in batteries if battery not in highest_voltage_batteries
    ]
    lowest_cycled_batteries = sorted(
      batteries_excluding_highest_voltages,
      key=lambda battery: battery.getNumCycles(),
      reverse=False,
    )[:3]
    return lowest_cycled_batteries
