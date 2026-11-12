import tkinter as tk
from PIL import Image
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
      command=self.toggle_mode,
      variable=self.is_match_mode,
      onvalue="on",
      offvalue="off",
    )
    # Create Image
    self.first_logo_file = ctk.CTkImage(light_image=Image.open("app/Assets/FirstLogo.jpeg"), size=(150, 150))
   
    # display image with a CTkLabel
    self.first_logo_display = ctk.CTkLabel(self, image=self.first_logo_file, text="") 
    self.first_logo_display.grid(row=2,column=2,padx=0,pady=0)

    # Create battery frames
    self.battery_one_widget = ctk.CTkFrame(
      master=self, width="150", height="200", corner_radius=12
    )
    self.toggle_switch.grid(row=0, column=0, padx=20, pady=20)

    self.battery1 = ctk.CTkFrame(master=self, width=200, height=200, border_width=7, border_color="#80450b", fg_color="")
    self.battery2 = ctk.CTkFrame(master=self, width=200, height=300, border_width=7, border_color="#838587")
    self.battery3 = ctk.CTkFrame(master=self, width=200, height=250, border_width=7, border_color="#8c7304")

    self.battery1.grid(row=1, column = 1, padx=25, pady=50, stick="s")
    self.battery2.grid(row=1, column = 2, padx=25, pady=50, stick="s")
    self.battery3.grid(row=1, column = 3, padx=25, pady=50, stick="s")

  def toggle_mode(self):
    if self.is_match_mode:
      ...
    else:
      ...

  def load_match_mode(self): ...

  def load_test_mode(self): ...

  def select_battery(self): ...
