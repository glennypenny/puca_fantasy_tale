# Puca — A Dark Fantasy Interactive Story

An AI-driven interactive dark fantasy adventure. Each version is a locally run prototype: a local LLM narrates the story, and a local Stable Diffusion model draws each scene.

> **Content warning.** The v2 prototype is adult-oriented and uses unrestricted models: an abliterated LLM and a Stable Diffusion pipeline with the safety checker disabled. It can generate graphic violence, gore, nudity, and sexual content. I did not create those models; use them with extreme caution. See the v2 README for the full warning.

## Versions

| Version | Branch | Status | Platform | Notes |
| --- | --- | --- | --- | --- |
| **v1** | [`v1`](https://github.com/glennypenny/puca_fantasy_tale/tree/v1) | Legacy — frozen | Windows 11 | Single-file prototype. Buggy installer; see the branch README and `KNOWN_ISSUES.md`. |
| **v2** | [`v2`](https://github.com/glennypenny/puca_fantasy_tale/tree/v2) | Experimental prototype — archived | Pop!_OS 24.04 (Linux) | Modular rewrite: 7B Qwen, DreamShaper-8 + LoRA, session-scoped character state, guardrails. Not production-ready. |
| **v3** | *coming soon* | Planned | TBD | Fresh build with a fine-tuned model, `AIBouncer`, SFW filtering, and in-memory state. |

`main` is the landing page. The code and detailed setup instructions live on each version’s branch.

## Which version should I look at?

- **[v1](https://github.com/glennypenny/puca_fantasy_tale/tree/v1)** — the original proof of concept. Windows-only, single Python script, fragile installer. Setup and known issues are in that branch.
- **[v2](https://github.com/glennypenny/puca_fantasy_tale/tree/v2)** — the modular rewrite. More interesting technically, but an experimental adult prototype with no hosted demo. Start with the branch README.
- **v3** — not started yet. The plan is a fresh build with a fine-tuned model, an `AIBouncer` class from day one, SFW content filtering, and in-memory session state.

## Credits

Game design, lore, code, and music by **Glen Salmon**.

v2’s pixel-art LoRA was trained by Glen Salmon on a private dataset of images generated with Midjourney. Models used: DreamShaper-8 by Lykon, Qwen2.5-7B-Instruct-abliterated by Richard Young, and Stable Diffusion 1.5 by RunwayML, plus Ollama, Hugging Face Diffusers, PEFT, PyTorch, Tkinter, pyttsx3, and pygame.

All rights reserved for the game code, lore, music, and LoRA. The model weights remain under their respective licences. Midjourney-generated training images remain subject to Midjourney’s terms.
