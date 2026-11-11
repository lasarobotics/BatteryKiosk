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

    # Create battery frames
    self.battery_one_widget = ctk.CTkFrame(
      master=self, width="150", height="200", corner_radius=12
    )
     self.toggle_switch.grid(row=0, column=0, pax=20, paxy=20)

    self.battery1 = ctk.CTkFrame(master=self, width=50, height=50)
    self.battery2 = ctk.CTkFrame(master=self, width=50, height=50)
    self.battery3 = ctk.CTkFrame(master=self,width=50, height=50)

    
    self.battery_one_widget.bind("<Button-1>", self.select_battery())
    # Display First logo
    self.first_logo_file = ctk.CTkImage(light_image=Image.open("app/Assets/FirstLogo.jpeg"),
                                  size=(30, 30))
    self.first_logo_label = ctk.CTkLabel(self, image=self.first_logo_file, text="")

    # Position all widgets
    self.battery_one_widget.grid(row=50, column=100, padx=20, pady=20)
    self.toggle_switch.grid(row=0, column=0, padx=100, pady=60)
    self.first_logo_label.grid(row=50,column=50,padx=20,pady=20)
    self.battery1.grid(row=1, column = 1)
    self.battery2.grid(row=2, column = 1)
    self.battery3.grid(row=3, column = 1)

  def toggle_mode(self):
    if self.is_match_mode:
      ...
    else:
      ...

  def load_match_mode(self): ...

  def load_test_mode(self): ...

  def select_battery(self): ...
