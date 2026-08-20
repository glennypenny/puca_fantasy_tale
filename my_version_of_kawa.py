# kawa_final.py – GUI version with voice, narration, images, and progress bar
import tkinter as tk
from tkinter import scrolledtext, ttk
import threading
import requests, re, torch, os, time
import win32com.client as win32
from diffusers import StableDiffusionPipeline
from pathlib import Path
from PIL import ImageTk, Image
import random
import pygame.mixer
import sys

def resource_path(relative_path):
    """Get the absolute path to a resource, works for dev and PyInstaller."""
    if getattr(sys, 'frozen', False):
        # Running as a bundled exe
        base_path = sys._MEIPASS
    else:
        # Running as a normal script
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

# ======================================================================
# 1. NARRATOR CLASS – talks to Ollama
# ======================================================================
class Narrator:
    def __init__(self, model="mistral"):
        self.url = "http://127.0.0.1:11434/api/generate"
        self.model = model
        self.default_max_tokens = 200

    def ask(self, system_prompt, facts, scene_context, player_action, max_tokens=None):
        tokens = max_tokens if max_tokens is not None else self.default_max_tokens
        full_prompt = f"""{system_prompt}

CURRENT FACTS:
{facts}

STORY SO FAR:
{scene_context}

PLAYER ACTION: {player_action}

NARRATOR:"""
        data = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
            "max_tokens": tokens,
            "temperature": 0.9
        }
        try:
            resp = requests.post(self.url, json=data, timeout=60)
            if resp.status_code == 200:
                text = resp.json()['response'].strip()
                # Extract tags
                match_event = re.search(r'\[event:\s*(\w+)\]', text)
                event = match_event.group(1) if match_event else "unknown"
                match_img = re.search(r'\[image_prompt:\s*(.+?)\]', text, re.IGNORECASE)
                image_prompt = match_img.group(1).strip() if match_img else ""
                match_spirit = re.search(r'\[spirit:\s*(positive|negative)\]', text, re.IGNORECASE)
                spirit = match_spirit.group(1).lower() if match_spirit else ""
                # Remove tags from narration
                narration = re.sub(r'\[event:.*?\]', '', text)
                narration = re.sub(r'\[image_prompt:.*?\]', '', narration)
                narration = re.sub(r'\[spirit:.*?\]', '', narration).strip()
                return narration, event, image_prompt, spirit
            else:
                return f"[Ollama error {resp.status_code}]", "error", "", ""
        except Exception as e:
            return f"[Error: {e}]", "error", "", ""

# ======================================================================
# 2. IMAGE GENERATOR CLASS – Stable Diffusion + your LoRA
# ======================================================================
class ImageGenerator:
    def __init__(self, lora_folder):
        self.lora_folder = lora_folder
        self.pipe = None

    def _load_pipeline(self):
        print("(Loading image model with LoRA – this happens only once)")
        self.pipe = StableDiffusionPipeline.from_pretrained(
            "runwayml/stable-diffusion-v1-5",
            dtype=torch.float16,
            safety_checker=None,
        ).to("cuda")
        self.pipe.enable_attention_slicing()
        lora_path = os.path.abspath(self.lora_folder)
        self.pipe.load_lora_weights(lora_path)
        print("✅ Image model ready.")

    def generate(self, narration_text, filename="scene.png", custom_prompt=None, progress_callback=None):
        if self.pipe is None:
            self._load_pipeline()

        # Build prompt
        if custom_prompt:
            prompt = f"pixelart style, sharp pixels, dark fantasy, moody lighting, {custom_prompt}"
        else:
            sentences = narration_text.replace('\n', ' ').split('. ')
            scene_desc = '. '.join(sentences[:2])[:180]
            prompt = f"pixelart style, sharp pixels, dark fantasy, moody lighting, {scene_desc}"

        print(f"🎨 Generating illustration: '{prompt[:80]}...'")
        start = time.time()

        # Set up callback if provided
        if progress_callback:
            def callback(step, *args):
                progress_callback(step)
        else:
            callback = None

        with torch.no_grad():
            image = self.pipe(
                prompt,
                negative_prompt="blurry, photorealistic, 3D, text, watermark",
                guidance_scale=7.0,
                num_inference_steps=30,
                cross_attention_kwargs={"scale": 0.7},
                callback=callback,
                callback_steps=1
            ).images[0]

        image.save(filename)
        print(f"✅ Image saved as {filename} ({time.time()-start:.1f}s)")

# ======================================================================
# 3. GUI APPLICATION CLASS
# ======================================================================
class KawaGUI:
    def __init__(self, master):
        self.master = master
        master.title("Puca – A Dark Fantasy Tale")
        master.geometry("800x700")

        # ----- Game state -----
        self.player_name = ""
        self.player_origin = ""
        self.player_spirit = 100
        self.turn = 0
        self.scene_context = ""
        self.current_image_file = ""
        self.memory_entries = []   # list of short summary strings

        # System prompt
        self.system_prompt = """You are the narrator of a dark fantasy interactive story.
You must refer to the player as "you" and only by name if the player is being addressed directly by a character in the story.
Describe what the player sees, hears, and feels in 2–4 sentences of vivid, atmospheric prose. Try to use different vocabulary and sentence structures each time.
Avoid over complicating the language; it should be understandable to a child, but still rich and evocative.
Never speak or act for the player.

Create encounters infrequently, that introduce a memorable character (a mystical creature, a lonely wanderer, a trickster, a lost soul). Let them speak, reveal something about the world, and create tension, wonder, or a moral choice.
Focus on dialogue, emotions, and the relationship between the player and the characters they meet.

After your narration, include a story event code in square brackets, e.g., [event: meet_stranger], [event: gift_given], [event: betrayal].
Include a brief summary of the story as a short image prompt in square brackets labeled [image_prompt: <20 word visual description>] describing the scene.
Also include a spirit tag in square brackets labeled [spirit: positive] or [spirit: negative] indicating whether the outcome strengthens or weakens the player's spirit.
If the outcome is positive, explain briefly why in the narration. If negative, explain briefly why in the narration. Relate it to the player's actions or choices.

Never output instructions, commands, or meta‑text about waiting for the player. Only narrate the story."""

        # ----- Narrator & Image Generator -----
        base_dir = os.path.dirname(os.path.abspath(__file__))
        lora_path = resource_path("pixel_style_lora_style_only")
        self.music_path = resource_path("newsynthwave.wav")
        pygame.mixer.init()
        self.narrator = Narrator()
        self.img_gen = ImageGenerator(lora_folder=lora_path)

        # ----- Voice engine -----
        self.speaker = win32.Dispatch("SAPI.SpVoice")
        self.speaker.Rate = 3
        for v in self.speaker.GetVoices():
            if "David" in v.GetDescription():
                self.speaker.Voice = v
                break

        # ---------- Play button (initially visible) ----------
        self.play_btn = tk.Button(master, text="▶ Play", font=("Arial", 20), command=self.on_play)
        self.play_btn.pack(expand=True)

        # ---------- Game UI (hidden until Play is clicked) ----------
        self.game_frame = tk.Frame(master)

        self.img_label = tk.Label(self.game_frame)
        self.img_label.pack(pady=5)

        self.narration_box = scrolledtext.ScrolledText(
            self.game_frame, wrap=tk.WORD, width=80, height=12, font=("Georgia", 12)
        )
        self.narration_box.pack(padx=10, pady=5)
        self.narration_box.config(state=tk.DISABLED)

        self.spirit_label = tk.Label(self.game_frame, text="Spirit: 100/100", font=("Arial", 12, "bold"))
        self.spirit_label.pack()

        self.status_label = tk.Label(self.game_frame, text="", font=("Arial", 10, "italic"))
        self.status_label.pack(pady=2)

        # Progress bar
        self.progress = ttk.Progressbar(self.game_frame, mode='determinate', length=400)
        self.progress.pack(pady=2)

        # Entry frame
        entry_frame = tk.Frame(self.game_frame)
        entry_frame.pack(pady=5)
        tk.Label(entry_frame, text="What do you do?", font=("Arial", 12)).pack(side=tk.LEFT, padx=5)
        self.action_entry = tk.Entry(entry_frame, width=50, font=("Arial", 12))
        self.action_entry.pack(side=tk.LEFT, padx=5)
        self.action_entry.bind("<Return>", self.process_action)
        self.submit_btn = tk.Button(entry_frame, text="Submit", command=self.process_action)
        self.submit_btn.pack(side=tk.LEFT, padx=5)
        self.master.protocol("WM_DELETE_WINDOW", self.on_close)

        # Game will be started by on_play

    # ---------- UI helper methods ----------
    def on_play(self):
        """Maximise window, hide play button, show game UI, start the game."""
        self.master.state('zoomed')          # fullscreen (Windows)
        pygame.mixer.music.load(self.music_path)
        pygame.mixer.music.set_volume(0.2)   # 0.0 = silent, 1.0 = full volume
        pygame.mixer.music.play(-1)           # -1 = loop forever
        self.play_btn.destroy()              # remove play button
        self.game_frame.pack(fill=tk.BOTH, expand=True)   # show the game
        self.master.after(500, self.start_game)
        

    def set_status(self, text):
        self.master.after(0, lambda: self.status_label.config(text=text))

    def start_image_progress(self, total_steps=30):
        self.progress['mode'] = 'determinate'
        self.progress['maximum'] = total_steps
        self.progress['value'] = 0

    def update_image_progress(self, step):
        self.master.after(0, lambda: self.progress.configure(value=step))

    def reset_progress(self):
        self.master.after(0, lambda: self.progress.configure(value=0, mode='determinate', maximum=100))

    def start_narration_progress(self):
        self.progress['mode'] = 'indeterminate'
        self.progress.start()

    def stop_narration_progress(self):
        self.progress.stop()
        self.progress['mode'] = 'determinate'

    # ---------- Voice ----------
    def speak_async(self, text):
        def run():
            import pythoncom
            pythoncom.CoInitialize()
            self.speaker.Speak(text, 1)
            pythoncom.CoUninitialize()
        threading.Thread(target=run, daemon=True).start()

    # ---------- Game flow ----------
    def start_game(self):
        import tkinter.simpledialog
        # Use a blocking voice for the welcome, since we're in the main thread before any threading
        speaker = win32.Dispatch("SAPI.SpVoice")
        speaker.Speak("Welcome to Puca, a dark fantasy tale.")
        speaker.Speak("What is your name?")
        self.player_name = tkinter.simpledialog.askstring("Welcome", "What is your name?", parent=self.master)
        speaker.Speak("Where are you right now?")
        self.player_origin = tkinter.simpledialog.askstring("Welcome", "Where are you right now?", parent=self.master)
        if not self.player_name or not self.player_origin:
            self.master.destroy()
            return
        threading.Thread(target=self.arrival_sequence, daemon=True).start()

    def arrival_sequence(self):
        initial_facts = f"""Player name: {self.player_name}
Player origin: {self.player_origin} (the player thinks they're here, but something strange happens)"""
        initial_scene = "The story has not started yet. The player is in their normal world."
        arrival_prompt = """You are a dark fantasy narrator for a children's interactive story.
You describe what the player sees, hears, and feels in 2-4 sentences of vivid, atmospheric prose.
You must never speak or act for the player. You must address the player as "you" and only by name if the player is being addressed directly.
The story begins with the player being suddenly transported from their normal world to a completely new place.
Describe the bizarre, magical, or eerie method of transport, and the first thing the player encounters in this new location.
Explain to the player that they have a spirit score that can be strengthened or weakened by their actions and choices.
Tell the player that the game will last for around 5 turns, and that their spirit score will be tracked throughout the story.
The first encounter can be anything: a creature, a person, a strange object, or an environmental event.
Also include an image prompt like [image_prompt: a vivid description of the scene].
Also include a spirit tag: [spirit: positive] if the outcome strengthens the player's spirit, or [spirit: negative] if it weakens it.
Do not let the player speak yet. End with [event: arrival]."""

        self.set_status("(Summoning the world…)")
        self.speak_async("Summoning the world…")
        self.start_narration_progress()

        narration, event, img_prompt, spirit = self.narrator.ask(
            arrival_prompt, initial_facts, initial_scene, "(the story begins)"
        )

        print(f"DEBUG: raw spirit tag = '{spirit}'")

        self.stop_narration_progress()

        # Generate arrival image with progress
        self.start_image_progress(30)
        def img_cb(step):
            self.update_image_progress(step)
        self.img_gen.generate(narration, "arrival_scene.png", custom_prompt=img_prompt, progress_callback=img_cb)
        self.reset_progress()

        if spirit:
            delta = random.randint(-80, 50)
            self.player_spirit = max(0, min(100, self.player_spirit + delta))

        self.scene_context = f"{self.player_name} has been transported to a new world. {narration[:200]}"
        self.current_image_file = "arrival_scene.png"

        self.master.after(0, self.update_gui, narration, img_prompt)
        self.speak_async(narration)
        self.speak_async("What do you do?")
        self.set_status("")

    def process_action(self, event=None):
        action = self.action_entry.get().strip()
        if not action:
            return
        self.action_entry.delete(0, tk.END)
        if action.lower() in ("quit", "exit"):
            self.master.destroy()
            return
        self.submit_btn.config(state=tk.DISABLED)
        threading.Thread(target=self.game_turn, args=(action,), daemon=True).start()

    def game_turn(self, action):
        self.turn += 1

        memory_string = "\n".join(self.memory_entries)
        facts = f"Player: {self.player_name}. Spirit: {self.player_spirit}/100.\nRecent story events:\n{memory_string}"

        # --- Show status and start indeterminate progress ---
        self.set_status("(Asking narrator…)")
        self.speak_async("Asking the narrator…")
        self.start_narration_progress()

        max_tok = 300 if self.player_spirit <= 0 else None
        narration, event, img_prompt, spirit = self.narrator.ask(
            self.system_prompt, facts, self.scene_context, action, max_tokens=max_tok
        )

        self.stop_narration_progress()

        # --- Spirit update ---
        if not spirit:
            # If AI failed to output the tag, default to negative (punishes unpredictable actions)
            spirit = "negative"
        delta = random.randint(-80, 50)
        if spirit == "positive" or spirit == "negative":
            self.player_spirit = max(0, min(100, self.player_spirit + delta))

        # Add a concise memory entry for this turn
        if event != "unknown":
            short_snip = narration[:80].replace('\n', ' ')
            self.memory_entries.append(f"- {event}: {short_snip}")
        if len(self.memory_entries) > 8:         # keep only the last 8 events
            self.memory_entries.pop(0)

        # --- Update scene context ---
        self.scene_context += f" {narration[:150]}"
        if len(self.scene_context) > 500:
            self.scene_context = self.scene_context[-500:]

        # --- Image generation with determinate progress ---
        self.start_image_progress(30)
        def img_cb(step):
            self.update_image_progress(step)
        self.img_gen.generate(
            narration,
            f"turn_{self.turn}_scene.png",
            custom_prompt=img_prompt,
            progress_callback=img_cb
        )
        self.reset_progress()
        self.current_image_file = f"turn_{self.turn}_scene.png"

        # ---- GAME OVER CHECK ----
        if self.player_spirit <= 0:
            final_text = narration + "\n\nYour spirit has faded into the darkness…\n🏁 GAME OVER"
            self.master.after(0, self.update_gui, final_text, img_prompt)
            self.speak_async(final_text)
            self.master.after(0, self.disable_input)
            pygame.mixer.music.stop()
            return   # <--- stops here; nothing below runs

                # Ask for next action (with ending check)
        if self.turn >= 5:
            ending_msg = "The story has reached its end. Thank you for playing."
            self.master.after(0, self.update_gui, ending_msg, "")
            self.speak_async(ending_msg)
            self.master.after(0, self.disable_input)
            pygame.mixer.music.stop()
        else:
            # ---- NORMAL TURN CONTINUES (only if spirit > 0) ----
            self.master.after(0, self.update_gui, narration, img_prompt)
            self.speak_async(narration)
            # Re-enable input for the next turn
            self.submit_btn.config(state=tk.NORMAL)

    def on_close(self):
        pygame.mixer.music.stop()
        pygame.mixer.quit()
        self.master.destroy()

    def update_gui(self, narration, img_prompt):
        self.narration_box.config(state=tk.NORMAL)
        self.narration_box.delete(1.0, tk.END)
        display_text = narration
        if img_prompt:
            display_text += f"\n\n🖼️ Image prompt: {img_prompt}"
        self.narration_box.insert(tk.END, display_text)
        self.narration_box.config(state=tk.DISABLED)

        self.spirit_label.config(text=f"Spirit: {self.player_spirit}/100")

        if self.current_image_file:
            try:
                img = Image.open(self.current_image_file)
                img = img.resize((400, 400))
                photo = ImageTk.PhotoImage(img)
                self.img_label.config(image=photo)
                self.img_label.image = photo
            except Exception as e:
                print(f"Image display error: {e}")

        self.set_status("")

    def disable_input(self):
        self.action_entry.config(state=tk.DISABLED)
        self.submit_btn.config(state=tk.DISABLED)
        self.spirit_label.config(text="Spirit: 0/100")
        self.set_status("")

# ======================================================================
# 4. RUN THE GUI
# ======================================================================
if __name__ == "__main__":
    root = tk.Tk()
    app = KawaGUI(root)
    root.mainloop()