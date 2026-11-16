import os
import torch
from diffusers import StableDiffusionPipeline, DEISMultistepScheduler
from peft import PeftModel
from keywords import action_contains, COMBAT_WORDS, GORE_WORDS

SAVED_IMAGES_DIR = "/home/glen/Documents/puca_fantasy_tale/Game/Game_linux/saved_images"

def short_descriptor(char):
    """Build a short image-prompt clause from structured character state."""
    race = char.get("race", "") or ""
    appearance = char.get("appearance", "") or ""
    outfit = char.get("current_outfit", "") or ""
    state = char.get("outfit_state", "worn")

    if state == "removed" or not outfit or outfit.lower() in ("none", "unknown", ""):
        outfit_text = "nude"
    elif state == "damaged":
        outfit_text = f"{outfit} (damaged)"
    else:
        outfit_text = outfit

    parts = [p for p in [race, appearance, outfit_text] if p]
    return ", ".join(parts)

class ImageGenerator:
    def __init__(self, lora_folder):
        self.lora_folder = lora_folder
        self.pipe = None
        os.makedirs(SAVED_IMAGES_DIR, exist_ok=True)

    def _load_pipeline(self):
        print("(Loading image model with LoRA – this happens only once)")
        self.pipe = StableDiffusionPipeline.from_pretrained(
        "Lykon/dreamshaper-8",
        torch_dtype=torch.float16,
        safety_checker=None
        ).to("cuda")

        # Add the DreamShaper recommended scheduler
        self.pipe.scheduler = DEISMultistepScheduler.from_config(self.pipe.scheduler.config)

        self.pipe.enable_attention_slicing()
        lora_path = os.path.abspath(self.lora_folder)
        self.pipe.unet = PeftModel.from_pretrained(self.pipe.unet, lora_path)
        print("Image model ready.")
        print("\n" + "-"*40)

    def generate(self, narration_text, filename="scene.png", custom_prompt=None, progress_callback=None, allow_gore=True, present_npcs=None):
        if self.pipe is None:
            self._load_pipeline()

        # Build prompt — trigger must be exactly as trained
        style = ("(pixelart style:1.5), "
        "(sharp pixels:1.4), "
        "dark fantasy, moody lighting, "
        "eye-level view"
        )

        # --- DYNAMIC GORE LOGIC ---
        is_gore = False
        if allow_gore and custom_prompt and action_contains(custom_prompt, GORE_WORDS):
            is_gore = True

        if is_gore:
            print("🩸 Gore detected! Injecting Gore prompts.")
            style += ", (gore:1.4), (blood splatter:1.5), bloody corpses lying on the floor, decapitated bodies, visceral, dark fantasy"

        is_combat = False
        if custom_prompt and action_contains(custom_prompt, COMBAT_WORDS):
            is_combat = True
        
        if is_combat:
            print("⚔️ Combat detected! Injecting Combat prompts.")
            style = style.replace(", eye-level view", "")  # remove the calm camera angle
            style += ", (dynamic action:1.3), (weapons clashing:1.4), (motion blur:1.2)"

        # Build NPC descriptors FIRST so they never get truncated
        npc_desc = ""
        if present_npcs:
            descriptors = []
            for c in present_npcs:
                name = c.get("name", "")
                if not name: continue
                if c.get("outfit_state") == "removed":
                    descriptors.append(f"{name} is nude")
                else:
                    descriptors.append(short_descriptor(c))
            if descriptors:
                npc_desc = ", ".join(descriptors)

        if custom_prompt:
            # 1. Clean the prompt here, right before you use it
            clean_custom = custom_prompt.strip(', ')
            prompt = f"{style}, {npc_desc}, {clean_custom}"
        else:
            sentences = narration_text.replace('\n', ' ').split('. ')
            scene_desc = '. '.join(sentences[:2])[:180]
            prompt = f"{style}, {scene_desc}"

        # Append short descriptors for present NPCs (never full character sheets)
        if present_npcs and custom_prompt:
            descriptors = []
            for c in present_npcs:
                name = c.get("name", "")
                if not name:
                    continue
                # If the LLM already named them, only inject outfit state when it matters
                if name.lower() in prompt.lower():
                    state = c.get("outfit_state", "worn")
                    if state == "removed":
                        descriptors.append(f"{name} is nude")
                    elif state == "damaged":
                        outfit = c.get("current_outfit", "clothing")
                        descriptors.append(f"{name} in damaged {outfit}")
                else:
                    descriptors.append(short_descriptor(c))
            if descriptors:
                prompt = prompt + ", " + ", ".join(descriptors)

        # Truncate prompt to prevent the 75-token error
        if len(prompt) > 320: 
            prompt = prompt[:320].strip()

        print(f"Generating illustration: ({len(prompt)} characters): {prompt}")

        # Modern callback for progress
        if progress_callback:
            def step_end_callback(pipe, step, timestep, callback_kwargs):
                progress_callback(step)
                return callback_kwargs
        else:
            step_end_callback = None

        with torch.no_grad():
            image = self.pipe(
                prompt,
                width=512,
                height=512,
                negative_prompt=(
            "static pose, centered, symmetrical, "
            "T-pose, pillar, blurry, miniature, diorama, "
            "character sheet, smooth shading, 3d render, "
            "photorealistic, text, watermark, signature, logo, "
            "duplicate, multiple views, cloned, "
            "modern, car, vehicle, taxi, tiling, split image, "
            "comic panel, sequence, storyboard, frame, "
            "anime, manga, cartoon, cel shaded, digital painting, "
            "diagram, floor plan, layout, bird's eye view, floor plan, "
            "isometric, (isometric:1.5), top down view, "
            "anime, manga, flat colors, moe, cute, kawaii, "
            "bad hands, missing fingers, extra fingers, poorly drawn hands, mutated hands"
                ),
                guidance_scale=7.5,
                num_inference_steps=25,
                cross_attention_kwargs={"scale": 1.2},
                callback_on_step_end=step_end_callback,
            ).images[0]

        full_path = os.path.join(SAVED_IMAGES_DIR, filename)
        image.save(full_path)
        print(f"✅ Image saved as {filename}")
        return full_path
