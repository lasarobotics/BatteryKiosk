import signal
import sys
import threading
import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk
from os import path

from app.bfg_can import PWFCanBus

# Absolute path to app/Assets, so images load no matter which folder the
# kiosk is started from (e.g. a systemd service or autostart entry).
ASSETS_DIR = path.join(path.dirname(path.abspath(__file__)), "Assets")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window Configuration
        self.title("Purple Haze Battery Kiosk")
        self.geometry("1280x684")  # Panel size 1280x720, top bar height 36: 720-36 = 684
        self.configure(fg_color="#663399")
        self.resizable(False, False)  # width, height
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self._closing = False
        self._update_job = None
        self._quit_job = None
        self._quit_requested = threading.Event()
        self.setup_quit_handlers()
        png_path = path.join(ASSETS_DIR, "LasaRoboticsLogo.png")
        # The logo is 2048x2048. On X11 (e.g. the Pi), Tk sends the window icon to
        # the X server in one request, and an image that big is too large for it
        # (it fails with "BadLength"). Window icons are only shown small anyway.
        icon = Image.open(png_path)
        icon.thumbnail((64, 64), Image.Resampling.LANCZOS)
        self.icon_image = ImageTk.PhotoImage(icon)
        self.wm_iconphoto(True, self.icon_image)

        # Variables
        self.is_match_mode = tk.BooleanVar(value=True)
        self.bus = PWFCanBus()
        text = "LASA"
        self.wake_text = text.encode("ascii")
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
            border_color="#dddddd",
            font=("Arial", 24),
            command=self.toggle_mode,
            variable=self.is_match_mode,
            onvalue=False,
            offvalue=True,
            checkbox_width=24,
            checkbox_height=24,
            corner_radius=5,
            text_color="#dddddd",
        )
        self.toggle_switch.grid(row=0, column=0, padx=20, pady=(15, 10))

        # Create Image
        self.first_logo_file = ctk.CTkImage(
            light_image=Image.open(path.join(ASSETS_DIR, "First_Logo_White.png")),
            size=(150, 150),
        )
        self.second_logo_file = ctk.CTkImage(
            light_image=Image.open(path.join(ASSETS_DIR, "SecondLogo.png")),
            size=(150, 150),
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
            anchor="s",  # south
            text_color="#dddddd",
        )
        self.text2nd.grid(row=1, column=0, padx=(30, 0), pady=(0, 8), sticky="s")

        self.text3rd = ctk.CTkLabel(
            master=self,
            text="3rd",
            fg_color="transparent",
            bg_color="transparent",
            font=("Arial", 48),
            anchor="s",  # south
            text_color="#dddddd",
        )
        self.text3rd.grid(row=1, column=2, padx=(10, 42), pady=(0, 8), sticky="s")

        self.test_yell = ctk.CTkLabel(
            master=self,
            text="BATTERIES FOR TESTING!\nDO NOT USE FOR MATCH!!",
            text_color="#dddddd",
            text_color_disabled="#663399",
            fg_color="transparent",
            bg_color="transparent",
            font=("Arial", 30),
            # anchor="s", # south
        )
        self.test_yell.configure(state="disabled")
        self.test_yell.grid(row=0, column=1, columnspan=2, pady=(5, 0))

        # Create battery frames
        self.battery2 = ctk.CTkFrame(
            master=self,
            width=300,
            height=200,
            border_width=7,
            border_color="#838587",
            fg_color="#e3e2e1",
        )
        self.battery1 = ctk.CTkFrame(
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
        self.battery2.grid(row=2, column=0, padx=(42, 10), pady=(0, 100), sticky="s")
        self.battery1.grid(row=2, column=1, padx=10, pady=(0, 100), sticky="s")
        self.battery3.grid(row=2, column=2, padx=(10, 42), pady=(0, 100), sticky="s")

        self.battery_frames = [self.battery1, self.battery2, self.battery3]
        self.battery_labels = ["", "", ""]
        for i in range(3):
            font_size = 20 if i == 0 else 17 if i == 1 else 14
            self.battery_labels[i] = ctk.CTkLabel(
                self.battery_frames[i],
                text="Battery: ----\n\nVoltage: ----\n\n# Cycles: ----\n\nCharging for: ----\n",
                font=("Arial", font_size),
                fg_color="transparent",
            )
            self.battery_frames[i].grid_columnconfigure(0, weight=1)
            self.battery_labels[i].grid(row=0, column=0, padx=0, pady=(20, 10))

    def toggle_mode(self):
        if self.is_match_mode.get():
            self.configure(fg_color="#663399")
            self.second_logo_display.grid_remove()
            self.first_logo_display.grid(row=1, column=1, padx=0, pady=30)
            self.test_yell.configure(state="disabled")
        else:
            self.configure(fg_color="#AB1919")
            self.first_logo_display.grid_remove()
            self.second_logo_display.grid(row=1, column=1, padx=0, pady=30)
            self.test_yell.configure(state="normal")

    # Excludes batteries drawing or discharging more than 600 mA
    def select_batteries(self):
        self.batteries = []
        self.discovered_batteries = self.bus.discovered_bfgs()

        self.batteries = [
            self.bus.get_bfg(battery.id).update()
            for battery in self.discovered_batteries
        ]
        good_batteries = [
            battery for battery in self.batteries if abs(battery.get_current()) < 0.6
        ]
        if self.is_match_mode.get():
            return self.find_match_batteries(good_batteries)
        else:
            return self.find_testing_batteries(good_batteries)

    # Returns 3 batteries (in descending order of voltage)
    def find_match_batteries(self, batteries):
        highest_voltage_batteries = (
            sorted(batteries, key=lambda battery: battery.get_voltage(), reverse=True)
            + [None] * 3
        )[:3]
        return highest_voltage_batteries

    # Returns 3 batteries (in ascending number of cycles)
    # If less than 3 batteries, list is filled with null
    def find_testing_batteries(self, batteries):
        highest_voltage_batteries = self.find_match_batteries(batteries)
        batteries_excluding_highest_voltages = [
            battery for battery in batteries if battery not in highest_voltage_batteries
        ]
        lowest_cycled_batteries = (
            sorted(
                batteries_excluding_highest_voltages,
                key=lambda battery: battery.get_num_cycles(),
                reverse=False,
            )
            + [None] * 3
        )[:3]
        return lowest_cycled_batteries

    # Converts seconds to hours and minutes
    def seconds_converter(self, seconds):
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        str_minutes = " Minutes" if minutes > 1 else " Minute"
        if hours > 0:
            str_hours = " Hours, " if hours > 1 else " Hour, "
            return str(hours) + str_hours + str(minutes) + str_minutes
        return str(minutes) + str_minutes

    # Displays the information
    def display_batteries(self):
        self.wake_can()
        selected_batteries = self.select_batteries()
        for i in range(3):
            if selected_batteries[i] is not None:
                self.battery_labels[i].configure(
                    text="Battery: "
                    + str(selected_batteries[i].sensor_id)
                    + "\n\nVoltage: "
                    + str(selected_batteries[i].get_voltage())
                    + "\n\n# Cycles: "
                    + str(selected_batteries[i].get_num_cycles())
                    + "\n\nCharging for: "
                    + self.seconds_converter(
                        selected_batteries[i].get_cycle_charge_time()
                    )
                    + "\n",
                    font=("Arial", 18),
                    fg_color="transparent",
                )
                if selected_batteries[i].get_voltage() < 12:
                    self.battery_frames[i].configure(
                        border_color="#FF3D3D", fg_color="#ff9d00"
                    )
                else:
                    self.battery_frames[i].configure(
                        border_color="#838587", fg_color="#e3e2e1"
                    )
            else:
                self.battery_labels[i].configure(
                    text="Battery: ----\n\nVoltage: ----\n\n# Cycles: ----\n\nCharging for: ----\n"
                )
                self.battery_frames[i].configure(
                    border_color="#FF3D3D", fg_color="#ff9d00"
                )
        self._update_job = self.after(1000, self.display_batteries)

    def setup_quit_handlers(self):
        # Ctrl+C / Ctrl+D pressed while the kiosk window has focus.
        for seq in ("<Control-c>", "<Control-C>", "<Control-d>", "<Control-D>"):
            self.bind_all(seq, lambda event: self.on_closing())

        # Ctrl+C in the terminal (SIGINT) and `kill` / systemd stop (SIGTERM).
        # Signal handlers can run in the middle of any Python code, so just set
        # a flag here and let the Tk loop do the actual shutdown.
        def handle_signal(signum, frame):
            self._quit_requested.set()

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

        # Ctrl+D in the terminal sends EOF on stdin. Only watch for it when we
        # were started from a real terminal; under systemd/autostart stdin is
        # usually /dev/null, which would hit EOF right away and quit immediately.
        if sys.stdin is not None and sys.stdin.isatty():

            def watch_stdin():
                try:
                    while sys.stdin.readline():
                        pass
                except (OSError, ValueError):
                    return
                self._quit_requested.set()

            threading.Thread(target=watch_stdin, name="stdin-eof", daemon=True).start()

        self._poll_quit()

    def _poll_quit(self):
        # Tk's mainloop sits in C code, so Python only notices signals when it
        # runs some Python code. This wakes it up regularly to check the flag.
        if self._closing:
            return
        if self._quit_requested.is_set():
            self.on_closing()
            return
        self._quit_job = self.after(100, self._poll_quit)

    def on_closing(self):
        if self._closing:
            return
        self._closing = True
        for job in (self._update_job, self._quit_job):
            if job is not None:
                try:
                    self.after_cancel(job)
                except tk.TclError:
                    pass
        try:
            self.bus.close()
        finally:
            self.quit()
            self.destroy()

    def wake_can(self):
      self.bus.send(self.wake_text)
