# Puca — A Dark Fantasy Interactive Story (v1)

> **Legacy / first attempt.** This is version 1 of Puca, kept for reference. It was my first substantial programming project: a single Python script, a fragile installer, and a lot of trial and error. It works, but setup is brittle. See [KNOWN_ISSUES.md](KNOWN_ISSUES.md).
>
> The code lives on this `v1` branch. The default branch is a landing page describing all versions.

> **Content warning.** v1 can generate adult content and graphic violence. It is not suitable for minors.

An AI-driven interactive dark fantasy story. A local LLM (Mistral via Ollama) narrates each beat, and a local Stable Diffusion model draws each scene. This version is a five-turn story with a spirit score.

## System requirements

- Windows 10 or 11 (developed and tested on Windows 11)
- NVIDIA GPU with at least 8 GB of VRAM
- ~10 GB free disk space for the AI models
- Internet connection for first setup only
- Python 3.13 (tested)
- Ollama with `mistral:latest`
- Stable Diffusion weights (downloaded automatically on first run)

## Installation

1. Install Python 3.13 from python.org. Check **Add Python to PATH**.
2. Install [Ollama](https://ollama.com/download).
3. Run `install.bat`, or install manually:

   ```bat
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
   pip install diffusers transformers accelerate peft Pillow requests pywin32 pygame
   ```

4. Pull the model:

   ```bat
   ollama pull mistral
   ```

5. Start Ollama if it is not already running:

   ```bat
   ollama serve
   ```

6. Run the game:

   ```bat
   python my_version_of_kawa.py
   ```

The first run downloads Stable Diffusion 1.5 (~4 GB). Expect a long wait.

## Controls

- Click **Play**.
- Enter your name and starting location in the dialogs.
- Type an action and press **Enter**, or click **Submit**.
- The story runs for about five turns. Your spirit score starts at 100 and changes with your choices; if it reaches 0, the game ends.
- Close the window or stop the script to quit.

## Files

| File | Purpose |
| --- | --- |
| `my_version_of_kawa.py` | The whole game: narrator, image generator, and GUI |
| `newsynthwave.wav` | Background music |
| `pixel_style_lora_style_only/` | Pixel-art LoRA (stored with Git LFS) |
| `install.bat` | Windows installer helper |
| `requirements.txt` | Python packages |
| `KNOWN_ISSUES.md` | Known setup and runtime problems |

## Known issues

See [KNOWN_ISSUES.md](KNOWN_ISSUES.md). The short version: the installer is unreliable, dependency versions are unpinned, and the code is Windows-only.

## Credits

Game design, lore, code, and music by **Glen Salmon**. Models and libraries retain their own licences. See the [main README](https://github.com/glennypenny/puca_fantasy_tale) for the full credits and version list.

## Related branches

- [`main`](https://github.com/glennypenny/puca_fantasy_tale) — landing page.
- [`v1`](https://github.com/glennypenny/puca_fantasy_tale/tree/v1) — this branch.
- [`v2`](https://github.com/glennypenny/puca_fantasy_tale/tree/v2) — modular Linux rewrite.
