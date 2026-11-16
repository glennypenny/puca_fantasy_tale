import os
import tkinter as tk
from gui import KawaGUI
from game import CHARACTERS_CSV_PATH

# initialization #
# ------------------------ #
if __name__ == "__main__":
    root = tk.Tk()
    app = KawaGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close) # Ensures music stops when X is clicked
    try:
        root.mainloop()
    finally:
        # ── FINAL CLEANUP ──
        # This runs NO MATTER WHAT happens to the mainloop (crash, quit, or force close)
        if os.path.exists(CHARACTERS_CSV_PATH):
            try:
                os.remove(CHARACTERS_CSV_PATH)
                print("🗑️ characters.csv deleted on exit (from main.py).")
            except Exception as e:
                print(f"⚠️ Could not delete CSV: {e}")