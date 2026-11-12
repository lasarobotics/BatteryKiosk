import tkinter as tk
from PIL import Image
import customtkinter as ctk
from app.bfg_can import PWFCanBus



class App(ctk.CTk):
  def __init__(self):
    super().__init__()

    # Window Configuration
    self.title("Purple Haze Battery Kiosk")
    self.geometry("1024x600")
    self.configure(fg_color = "#882fed")
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
        corner_radius=5
    )

    self.toggle_switch.grid(row=0, column=0, padx=20, pady=20)
    # Create Image
    self.first_logo_file = ctk.CTkImage(
        light_image=Image.open("app/Assets/FIRST_Logo.svg.webp"),
        size=(150, 150)
    )
    self.second_logo_file = ctk.CTkImage(
        light_image=Image.open("app/Assets/SecondLogo.png"),
        size=(150, 150)
    )
    # Display image with a transparent background
    self.first_logo_display = ctk.CTkLabel(
        master=self,
        image=self.first_logo_file,
        text="",
        fg_color="transparent"
    )
    self.second_logo_display = ctk.CTkLabel(
        master=self,
        image=self.second_logo_file,
        text=""
    )

    self.first_logo_display.grid(row=1, column=1, padx=0, pady=0)

    # Create battery frames
    self.battery_one_widget = ctk.CTkFrame(
      master=self, width="150", height="200", corner_radius=12
    )
    self.toggle_switch.grid(row=0, column=0, padx=20, pady=20)

    self.battery1 = ctk.CTkFrame(master=self, width=200, height=200, border_width=7, border_color="#80450b", fg_color="#d4700d")
    self.battery2 = ctk.CTkFrame(master=self, width=200, height=300, border_width=7, border_color="#8c7304", fg_color="#e8b50c")
    self.battery3 = ctk.CTkFrame(master=self, width=200, height=250, border_width=7, border_color="#838587", fg_color="#e3e2e1")

    self.battery1.grid(row=2, column = 0, padx=(150, 10), pady=50, stick="s")
    self.battery2.grid(row=2, column = 1, padx=(20, 10), pady=50, stick="s")
    self.battery3.grid(row=2, column = 2, padx=(20, 10), pady=50, stick="s")

  def toggle_mode(self):
    if self.is_match_mode.get():
      self.configure(fg_color = "#882fed")
      self.second_logo_display.grid_remove()
      self.first_logo_display.grid(row=1, column=1, padx=0, pady=0)
    else:
      self.configure(fg_color = "#DE2020")
      self.first_logo_display.grid_remove()
      self.second_logo_display.grid(row=1, column=1, padx=0, pady=0)

  def select_batteries(self):
    self.batteries = self.bus.discovered_bfgs()
    if self.batteries:
      if self.is_match_mode.get():
        self.find_match_batteries(self.batteries)
      else:
        self.find_testing_batteries(self.batteries)
    self.after(1000,self.select_batteries)
  
    
  