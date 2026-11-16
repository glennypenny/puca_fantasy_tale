import os
import random
import threading
import tkinter as tk
from tkinter import scrolledtext, ttk, simpledialog
import tkinter.font as tkfont
from PIL import ImageTk, Image
import pygame
import pyttsx3
from game import Game

SAVED_IMAGES_DIR = "/home/glen/Documents/puca_fantasy_tale/Game/Game_linux/saved_images"

LOADING_MESSAGES = [
    "The mists of Puca swirl around {name}...",
    "{name} pauses as fate is woven...",
    "Shadows shift in the dark...",
    "The ancient tomes record {name}'s choices...",
    "Your actions echo through...",
    "The Moons watch {name} in silence...",
    "Breathing life into the world of {name}...",
    "The threads of destiny tighten around {name}..."
]

SUMMONING_MESSAGES = [
    "Bringing the story of {name} to life... ",
    "Weaving reality from starlight... ",
    "The Nemorensis awakens for {name}... ",
    "Drawing the map of {name}'s journey... ",
    "The epic of {name} begins...",
    "The ancient magic stirs... "
    "The stars align for {name}... ",
    "The fabric of reality comes to life with {name}'s presence... "
]

class KawaGUI:
    def __init__(self, master):
        self.master = master
        master.title("Puca – A Dark Fantasy Tale")
        master.geometry("2560x1440")
        master.configure(bg="#121212")
        self.is_closing = False
        self.dot_count = 0
        self.dot_cycle = None
        self.loading_base = ""

        # --- OVERRIDE DEFAULT POPUP FONT ---
        default_font = tkfont.nametofont("TkDefaultFont")
        default_font.configure(size=20, family="Arial")
        # -----------------------------------

        # ----- Game Setup -----
        self.game = None # Will hold your Game instance

        # ----- Music Setup -----
        pygame.mixer.init()
        # UPDATE THIS PATH to point to your music file!
        self.music_file = "newsynthwave.wav"

        # ---- - Text-to-Speech Setup -----
        self.speaker = pyttsx3.init()
        self.speaker.setProperty('rate', 170)

        # ----- UI Layout -----
        self.play_btn = tk.Button(master, text="▶ Play", font=("Arial", 20), bg="#333333", fg="white", activebackground="#555555", activeforeground="white",  command=self.start_game)
        self.play_btn.pack(expand=True)

        self.game_frame = tk.Frame(master, bg="#121212")
        
        # Configure the main game frame for a 2-column split
        self.game_frame.grid_columnconfigure(0, weight=1) # Left side (Text)
        self.game_frame.grid_columnconfigure(1, weight=1) # Right side (Image)
        self.game_frame.grid_rowconfigure(0, weight=1)

        # ── LEFT SIDE (Text, Options, Entry) ──
        self.left_frame = tk.Frame(self.game_frame, bg="#121212")
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.left_frame.grid_rowconfigure(0, weight=1) # Text box expands
        self.left_frame.grid_columnconfigure(0, weight=1)

        self.text_box = scrolledtext.ScrolledText(self.left_frame, wrap=tk.WORD, width=50, height=15, font=("Georgia", 20),
                                                  bg="#1e1e1e", fg="#e0e0e0", insertbackground="white")
        self.text_box.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        self.text_box.config(state=tk.DISABLED)

        # --- OPTIONS FRAME ---
        self.options_frame = tk.Frame(self.left_frame, bg="#121212")
        self.options_frame.grid(row=1, column=0, sticky="ew", pady=10)
        
        self.option_btns = []
        for i in range(3):
            btn = tk.Button(self.options_frame, text="", font=("Arial", 16), state=tk.DISABLED, 
                            bg="#333333", fg="white", activebackground="#555555", activeforeground="white",
                            command=lambda idx=i: self.choose_option(idx))
            btn.pack(side=tk.TOP, fill=tk.X, pady=2) # Stacked vertically for easier reading
            self.option_btns.append(btn)

        # --- ENTRY FRAME ---
        entry_frame = tk.Frame(self.left_frame, bg="#121212")
        entry_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        entry_frame.grid_columnconfigure(1, weight=1)
        
        tk.Label(entry_frame, text="Action:", font=("Arial", 18), bg="#121212", fg="white").grid(row=0, column=0, padx=(0, 5))
        
        self.action_entry = tk.Entry(entry_frame, font=("Arial", 18), bg="#2a2a2a", fg="white", insertbackground="white")
        self.action_entry.grid(row=0, column=1, sticky="ew")
        self.action_entry.bind("<Return>", self.process_action)
        
        self.submit_btn = tk.Button(entry_frame, text="Submit", command=self.process_action, font=("Arial", 14), bg="#333333", fg="white", activebackground="#555555", activeforeground="white")
        self.submit_btn.grid(row=0, column=2, padx=(10, 0))

        # ── RIGHT SIDE (Image & Progress) ──
        self.right_frame = tk.Frame(self.game_frame, bg="#121212")
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.right_frame.grid_rowconfigure(0, weight=1) # Image expands
        self.right_frame.grid_columnconfigure(0, weight=1)

        self.img_label = tk.Label(self.right_frame, bg="#121212")
        self.img_label.grid(row=0, column=0, sticky="nsew")

        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TProgressbar", background="#4CAF50", troughcolor="#1e1e1e", bordercolor="#121212")
        
        self.progress = ttk.Progressbar(self.right_frame, mode='determinate', length=500, maximum=25)
        self.progress.grid(row=1, column=0, pady=(10, 0), sticky="ew")

    def start_game(self):
        # Show the game first
        self.play_btn.destroy()
        self.game_frame.pack(fill=tk.BOTH, expand=True)

        # Start Music
        try:
            pygame.mixer.music.load(self.music_file)
            pygame.mixer.music.set_volume(0.3)
            pygame.mixer.music.play(-1)
            self.master.after(1000, lambda: pygame.mixer.music.play(-1))
        except Exception as e:
            print(f"Music failed to load: {e}")

        #Wait 2 seconds. This gives the audio driver time to fully wake up.
        self.master.after(2000, self.run_intro)

    def run_intro(self):
        self.update_text("Welcome to Puca, a dark fantasy tale.")
        # Now the audio is warm, the voice will be perfect
        self.speak_async(" Welcome to Puca, a dark fantasy tale.")
        
        # 4. Wait 1.5 seconds after the voice finishes, then open the popup
        self.master.after(1500, self.ask_name_popup)

    def ask_name_popup(self):
        self.speak_async(" What is your name?")
        name = simpledialog.askstring("Welcome", "What is your name?", parent=self.master)

        # Wait 1 seconds, then call the ask_location_popup method, passing the name
        self.master.after(1000, self.ask_location_popup, name)

    def ask_location_popup(self, name):
        self.update_text(f"Hello, {name}.")
        self.speak_async(f" Hello, {name}. Where does your journey begin?")
        location = simpledialog.askstring("Welcome", "Where does your journey begin?", parent=self.master)

        if not name or not location:
            self.master.destroy() # User clicked cancel
            return

        # Initialize YOUR Game class
        self.game = Game(name, location)
        
        summon_text = random.choice(SUMMONING_MESSAGES).format(name=name,)
        display_text = f"{summon_text}\n\n{location}"
        self.start_loading_animation(f"{display_text}\n\nSummoning the world...")
        self.speak_async(summon_text)

        self.submit_btn.config(state=tk.DISABLED)

        # Run arrival in a thread
        threading.Thread(target=self.run_arrival, daemon=True).start()


    def update_progress_bar(self, step):
        if not self.is_closing:
            # Add +1 so the final step hits 25/25 instead of 24/25
            self.master.after(0, lambda: self.progress.configure(value=step + 1))

    def speak_async(self, text):
        def run():
            try:
                self.speaker.stop()
                self.speaker.say(text)
                self.speaker.runAndWait()
            except Exception as e:
                print(f"Voice error: {e}")
        threading.Thread(target=run, daemon=True).start()

    def start_loading_animation(self, base_text):
        """Starts an animated dots loop at the end of the text box."""
        self.stop_loading_animation()  # Cancel any existing loop
        self.is_loading = True
        self.dot_count = 0
        self.loading_base = base_text
        self._animate_dots()

    def _animate_dots(self):
        if not self.is_loading:
            return
        dots = "." * (self.dot_count % 4)  # cycles "", ".", "..", "..."
        self.text_box.config(state=tk.NORMAL)
        self.text_box.delete(1.0, tk.END)
        self.text_box.insert(tk.END, f"{self.loading_base}{dots}")
        self.text_box.config(state=tk.DISABLED)
        self.dot_count += 1
        self.dot_cycle = self.master.after(400, self._animate_dots)

    def stop_loading_animation(self):
        self.is_loading = False
        if self.dot_cycle:
            self.master.after_cancel(self.dot_cycle)
            self.dot_cycle = None

    def run_arrival(self):
        narration, filename, options, _ = self.game.start_arrival(progress_callback=self.update_progress_bar)
        self.master.after(0, self.stop_loading_animation)  
        self.master.after(0, self.update_ui, narration, filename, options, False)
        self.master.after(0, lambda: self.progress.configure(value=0))

        # READ ALOUD
        self.speak_async(narration)
        # Wait 3 seconds, then ask "What do you do?"
        self.master.after(5000, lambda: self.speak_async("What do you do?"))

        if not self.is_closing:
            self.master.after(0, lambda: self.submit_btn.config(state=tk.NORMAL))

    def process_action(self, event=None):
        action = self.action_entry.get().strip()
        if not action or not self.game:
            return
        
        self.action_entry.delete(0, tk.END)
        if action.lower() in ("quit", "exit"):
            self.on_close()
            return

        action_display = f"> {action}"

        # Pick a loading message and format it with game data
        loading_msg = random.choice(LOADING_MESSAGES).format(
            name=self.game.player_name,
        )

        current_loc = self.game.player_location
        
        self.submit_btn.config(state=tk.DISABLED)
        self.start_loading_animation(f"{loading_msg}\n\nLocation:{current_loc}\n\nThe narrator is thinking...")
        self.speak_async(loading_msg)
        
        # Run turn in a thread
        threading.Thread(target=self.run_turn, args=(action,), daemon=True).start()

    def run_turn(self, action):
        narration, filename, options, player_dead = self.game.play_turn(action, progress_callback=self.update_progress_bar)
        self.master.after(0, self.stop_loading_animation)          
        self.master.after(0, self.update_ui, narration, filename, options, player_dead)
        self.master.after(0, lambda: self.progress.configure(value=0)) 

        if not self.is_closing:
            self.master.after(0, lambda: self.submit_btn.config(state=tk.NORMAL))

        # READ ALOUD
        self.speak_async(narration)
    
        if player_dead:
            # Game Over!
            self.master.after(0, lambda: self.update_text(f"{narration}\n\n🏁 YOU HAVE DIED. GAME OVER."))
            self.speak_async("Game over. You have died.")
            self.master.after(0, lambda: self.submit_btn.config(state=tk.DISABLED))
            for btn in self.option_btns:
                self.master.after(0, lambda b=btn: b.config(state=tk.DISABLED))
        else:
            # Normal turn
            self.master.after(0, lambda: self.submit_btn.config(state=tk.NORMAL))
            self.master.after(3000, lambda: self.speak_async("What do you do?"))

    def update_text(self, text):
        self.text_box.config(state=tk.NORMAL)
        self.text_box.delete(1.0, tk.END)
        self.text_box.insert(tk.END, text)
        self.text_box.config(state=tk.DISABLED)

    def update_ui(self, narration, image_filename, options, player_dead=False):
        # 1. Build the display text based on whether the player is dead
        if player_dead:
            display_text = f"{narration}\n\n🏁 YOU HAVE DIED. GAME OVER."
        else:
            display_text = f"{narration}\n\n What do you do?"
            
        # 2. Update the text box with the correct text
        self.update_text(display_text)

        # Update the buttons
        for i in range(3):
            if i < len(options) and not player_dead:
                self.option_btns[i].config(text=options[i], state=tk.NORMAL)
            else:
                self.option_btns[i].config(text="", state=tk.DISABLED)

        # Update the image
        if image_filename:
            try:
                img = Image.open(image_filename)
                img = img.resize((900, 900), Image.NEAREST)
                photo = ImageTk.PhotoImage(img)
                self.img_label.config(image=photo)
                self.img_label.image = photo
            except Exception as e:
                print(f"Image display error: {e}")

        self.master.update_idletasks()

    def choose_option(self, index):
        # Get the text from the button that was clicked
        action = self.option_btns[index].cget("text")
        if action:
            # Put it in the entry box and trigger the standard action process
            self.action_entry.delete(0, tk.END)
            self.action_entry.insert(0, action)
            self.process_action()

    def on_close(self):
        if self.game:
            self.game.save_all_characters_to_csv()
        self.is_closing = True
        try:
            pygame.mixer.music.stop()
            pygame.mixer.quit()
        except:
            pass

        # ── DELETE THE CSV ON CLOSE ──
        # Make sure you have "import os" at the top of this file!
        from game import CHARACTERS_CSV_PATH # Or whatever your import path is
        if os.path.exists(CHARACTERS_CSV_PATH):
            try:
                os.remove(CHARACTERS_CSV_PATH)
                print("🗑️ characters.csv deleted on exit.")
            except Exception as e:
                print(f"⚠️ Could not delete CSV: {e}")
        # ─────────────────────────────

        try:
            self.speaker.stop()
        except:
            pass

        self.master.quit()
        self.master.destroy()