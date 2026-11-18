import tkinter as tk

import customtkinter as ctk
from PIL import Image
from os import path

from app.bfg_can import PWFCanBus


class App(ctk.CTk):
  def __init__(self):
    super().__init__()

    # Window Configuration
    self.title("Purple Haze Battery Kiosk")
    self.geometry("1024x600")
    self.configure(fg_color="#663399")
    self.resizable(False, False) # width, height

    png_path = path.join(path.dirname(path.abspath(__file__)), "Assets/LasaRoboticsLogo.png")
    self.icon_image = tk.PhotoImage(file=png_path)
    self.wm_iconphoto(True, self.icon_image)

    # Variables
    self.is_match_mode = tk.BooleanVar(value=True)
    self.bus = PWFCanBus()

    # Open CanBus TODO error handling
    self.bus.open()
    # Initialize Widgets
    self.create_widgets()

    # Start update loop
    self.display_batteries()

  def create_widgets(self):

    # Configure row weights so Row 0 stays compact and Rows 1-2 share remaining height
    self.grid_rowconfigure(0, weight=0)
    self.grid_rowconfigure(1, weight=1)
    self.grid_rowconfigure(2, weight=1)

    # Create match and test battery switch

    self.toggle_switch = ctk.CTkCheckBox(
      master=self,
      text="Testing Mode",
      bg_color="transparent",
      border_color="black",
      font=("Arial", 24),
      command=self.toggle_mode,
      variable=self.is_match_mode,
      onvalue=False,
      offvalue=True,
      checkbox_width=24,
      checkbox_height=24,
      corner_radius=5,
    )
    self.toggle_switch.grid(row=0, column=0, padx=20, pady=(15, 10))

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

    self.first_logo_display.grid(row=1, column=1, padx=0, pady=30)

    self.text2nd = ctk.CTkLabel(
      master=self,
      text="2nd",
      fg_color="transparent",
      bg_color="transparent",
      font=("Arial", 48),
      anchor="s", # south
    )
    self.text2nd.grid(row=1, column=0, padx=(30, 0), pady=(0, 8), sticky="s")

    self.text3rd = ctk.CTkLabel(
      master=self,
      text="3rd",
      fg_color="transparent",
      bg_color="transparent",
      font=("Arial", 48),
      anchor="s", # south
    )
    self.text3rd.grid(row=1, column=2, padx=(10, 42), pady=(0, 8), sticky="s")

    self.test_yell = ctk.CTkLabel(
      master=self,
      text="BATTERIES FOR TESTING!\nDO NOT USE FOR MATCH!!",
      text_color="black",
      text_color_disabled="#663399",
      fg_color="transparent",
      bg_color="transparent",
      font=("Arial", 30),
      # anchor="s", # south
    )
    self.test_yell.configure(state="disabled")
    self.test_yell.grid(row=0, column=1, columnspan=2, pady=(5, 0))

    # Create battery frames
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
      border_color="#838587",
      fg_color="#e3e2e1",
    )
    self.battery3 = ctk.CTkFrame(
      master=self,
      width=240,
      height=160,
      border_width=7,
      border_color="#838587",
      fg_color="#e3e2e1",
    )
    self.battery1.grid_propagate(False)
    self.battery2.grid_propagate(False)
    self.battery3.grid_propagate(False)
    self.battery1.grid(row=2, column=0, padx=(42, 10), pady=(0, 100), sticky="s")
    self.battery2.grid(row=2, column=1, padx=10, pady=(0, 100), sticky="s")
    self.battery3.grid(row=2, column=2, padx=(10, 42), pady=(0, 100), sticky="s")

    self.battery_frames = [self.battery1,self.battery2,self.battery3]
    self.battery_labels = [[],[],[]]
    for i in range(3):
      self.battery_labels[i] = [
      ctk.CTkLabel(self.battery_frames[i],text="Battery: ----",font=('Arial',28),fg_color="transparent"),
      ctk.CTkLabel(self.battery_frames[i],text="Voltage: ----",font=('Arial',18),fg_color="transparent"),
      ctk.CTkLabel(self.battery_frames[i],text="# Cycles: ----",font=('Arial',18),fg_color="transparent"),
      ctk.CTkLabel(self.battery_frames[i],text="Charging for: ----",font=('Arial',10),fg_color="transparent")]
      self.battery_frames[i].grid_columnconfigure(0, weight=1)
      for j in range(4): 
        self.battery_frames[i].grid_rowconfigure(j, weight=1)
        self.battery_labels[i][j].grid(row=j,column=0,padx=0,pady=(10,0) if j == 0 else (0, 5))

  def toggle_mode(self):
    if self.is_match_mode.get():
      self.configure(fg_color="#663399")
      self.second_logo_display.grid_remove()
      self.first_logo_display.grid(row=1, column=1, padx=0, pady=30)
      self.test_yell.configure(state="disabled")
    else:
      self.configure(fg_color="#DE2020")
      self.first_logo_display.grid_remove()
      self.second_logo_display.grid(row=1, column=1, padx=0, pady=30)
      self.test_yell.configure(state="normal")

  def select_batteries(self):
    self.batteries = []
    self.discovered_batteries = self.bus.discovered_bfgs()
    
    self.batteries = [
      self.bus.get_bfg(battery.id).update() for battery in self.discovered_batteries
    ]
    if self.is_match_mode.get():
      return self.find_match_batteries(self.batteries)
    else:
      return self.find_testing_batteries(self.batteries)

  # Returns 3 batteries (in descending order of voltage)
  def find_match_batteries(self,batteries):
    highest_voltage_batteries = (sorted(
      batteries, key=lambda battery: battery.get_voltage(), reverse=True
    )+[None] * 3)[:3]
    return highest_voltage_batteries

  # Returns 3 batteries (in ascending number of cycles)
  # If less than 3 batteries, list is filled with null 
  def find_testing_batteries(self, batteries):
    highest_voltage_batteries = self.find_match_batteries(batteries)
    batteries_excluding_highest_voltages = [
      battery for battery in batteries if battery not in highest_voltage_batteries
    ]
    lowest_cycled_batteries = (sorted(
      batteries_exclud3ing_highest_voltages,
      key=lambda battery: battery.get_num_cycles(),
      reverse=False,
    )+[None] * 3)[:3]
    return lowest_cycled_batteries
  
  # Converts seconds to hours and minutes
  def seconds_converter(self,seconds):
    hours = seconds//3600
    minutes = (seconds%3600)//60
    str_minutes = " Minutes" if minutes > 1 else " Minute"
    if hours > 0:
      str_hours = " Hours, " if hours > 1 else " Hour, "
      return str(hours) +str_hours + str(minutes) + str_minutes
    return str(minutes) + str_minutes
  # Displays the information
  def display_batteries(self):
    selected_batteries = self.select_batteries()
    for i in range(3):
      if selected_batteries[i] is not None:
          self.battery_labels[i][0].configure(text="Battery: " + str(selected_batteries[i].sensor_id))
          self.battery_labels[i][1].configure(text="Voltage: " + str(selected_batteries[i].get_voltage()))
          self.battery_labels[i][2].configure(text="# Cycles: " + str(selected_batteries[i].get_num_cycles()))
          self.battery_labels[i][3].configure(text="Charging for: " + self.seconds_converter(selected_batteries[i].get_cycle_charge_time()))
      else:
        self.battery_labels[i][0].configure(text="Battery: ----")
        self.battery_labels[i][1].configure(text="Voltage: ----")
        self.battery_labels[i][2].configure(text="# Cycles: ----")
        self.battery_labels[i][3].configure(text="Charging for: ----")
    self.after(1000, self.display_batteries)

  #TODO close Bus