# Known issues — Puca v1

v1 was my first substantial programming project. It runs, but it is fragile.
These are the problems I know about, and what to do about each.

## Setup / installation

- **`install.bat` only installs part of what's needed.** It frequently
  half-completes, leaving the game to crash on a missing module.
  *Workaround:* use the Manual setup section of the README. Install PyTorch
  (CUDA build) first, then the remaining packages, then go through the imports
  at the top of `my_version_of_kawa.py` one at a time until nothing is missing.
- **No pinned dependency versions.** v1 was built against whatever was current
  at the time. A fresh install today may pull newer, incompatible versions.
  `requirements.txt` lists the packages; pin them from a working install if you
  need reproducibility.
- **Ollama and the Stable Diffusion model are separate installs.** The batch
  file tries to handle both, but neither is reliable. Install Ollama manually
  and run `ollama pull <model>` yourself.
- **First run needs internet.** The Stable Diffusion weights (~4 GB) are
  downloaded on first launch. Expect a long wait and a large download.
- **Windows only.** The script uses Windows-specific packages (`pywin32`) and
  Windows paths. It will not run on macOS or Linux.
- **Python version sensitivity.** Old/new Python 3 releases may break the
  dependency chain. The version this was developed on is recorded in the README.

## Runtime

- **Slow image generation.** Usually means PyTorch installed without CUDA
  support. Reinstall with:
  `pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124`
- **"Ollama not found".** Ollama isn't installed, or isn't running. Start it with
  `ollama serve` or from the system tray.
- **Out-of-memory when generating an image.** Reduce the image resolution in the
  script, or close other GPU-using applications.
- **No music or narration.** `pygame` and/or `pywin32` missing:
  `pip install pygame pywin32`.
- **Model mismatch.** If you pull a different Mistral size/tag than the script
  expects, output quality or speed will change. Check `ollama list`.

## Code / design

- **One monolithic script.** All logic lives in `my_version_of_kawa.py` — no
  separation of concerns, no tests, limited error handling. This is the main
  thing v2 addresses.
- **Brittle error handling.** Failures (missing model, GPU unavailable) often
  surface as a raw traceback rather than a useful message.
- **Script name.** `my_version_of_kawa.py` is an early internal codename of my
  own project; it is not a fork of another codebase.

## Repository

- **Code lives on the `v1` branch.** The default branch is a landing page
  describing both versions. Use the branch dropdown or
  `git checkout v1` to see the code.