import requests
import re
import threading
import random
import csv
import os

import tkinter as tk
from tkinter import scrolledtext, ttk, simpledialog
import tkinter.font as tkfont
from PIL import ImageTk, Image
import pygame
import pyttsx3

from narrator import Narrator
from image_generator import ImageGenerator
from narration import process_narration
from prompts import build_system_prompt
from prompts import build_summary_prompt
from keywords import action_contains, MOVEMENT_WORDS, COMBAT_WORDS, GORE_WORDS, DEATH_WORDS, LEAVING_WORDS, SOLO_WORDS, CONVERSATION_WORDS

CHARACTERS_CSV_PATH = "/home/glen/Documents/puca_fantasy_tale/Game/Game_linux/characters.csv"

def extract_destination(action):
    action_lower = action.lower()
    # If they say they are leaving, force a generic "outside" location
    if any(word in action_lower for word in ["leave", "exit", "walk outside", "head out", "be off"]):
        return "Outside the previous location" 
    patterns = [
        r"(?:go|walk|run|head|travel|leave|exit|enter)\s+(?:to|into|towards?|for)\s+(.+)",
        r"(?:i am|i'm)\s+(?:in|at)\s+(.+)",
    ]
    for p in patterns:
        m = re.search(p, action, re.IGNORECASE)
        if m:
            return m.group(1).strip().rstrip(".")
    return None

class Game:
    def __init__(self, player_name, player_location):

        print("Welcome to the game!")

        self.image_generator = ImageGenerator(
            lora_folder="/home/glen/Documents/puca_fantasy_tale/Game/Game_linux/loras/glen_lora_v2/")
        self.narrator = Narrator()
        self.player_name = player_name
        self.player_location = player_location
        self.system_prompt = build_system_prompt(player_name)
        self.player_action = ""
        self.story_so_far = ""       # Short-term memory (last 3 turns)
        self.memory_summary = ""     # Long-term memory (summarized past)
        self.turn_count = 0
        self.current_characters = [] # Who is in the room right now
        self.gore_turns = 0  
        self.in_combat = False
        self.in_conversation = False   # turns of gore visibility remaining
        self.character_db = {}

        # Check if the file exists so it doesn't crash on the very first run
        if os.path.exists(CHARACTERS_CSV_PATH):
            with open(CHARACTERS_CSV_PATH, "r", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.character_db[row["name"]] = {
                        "race": row.get("race", ""),
                        "gender": row.get("gender", "unknown"),
                        "appearance": row.get("appearance", ""),
                        "current_outfit": row.get("current_outfit", "unknown"),
                        "outfit_state": row.get("outfit_state", "worn"),
                        "personality": row.get("personality", "Unknown"),
                        "trust_level": row.get("trust_level", 50),
                        "desire_level": row.get("desire_level", 50),
                        "fear_level": row.get("fear_level", 10),
                        "current_location": row.get("current_location", "Unknown"),
                        "last_seen_turn": row.get("last_seen_turn", 0),
                    }
        
        # The pool of options the game will randomly pick from
        # Context-aware option pools
        self.option_pools = {
            "combat": [
                "Attack.", "Defend yourself.", "Aim for a weak spot.", 
                "Disarm them.", "Push them back.", "Cast a defensive spell.",
                "Drink a potion.", "Surrender.", "Execute the enemy.", 
                "Throw something.", "Kick them.", "Block the attack.",
                "Flee the fight."
            ],
            "conversation": [
                "Demand answers.", "Try to seduce them.", "Offer a bribe.",
                "Threaten them.", "Reassure them.", "Tell a lie.",
                "Reveal the truth.", "Insult them.", "Apologize.",
                "Ask about their past.", "Pull them closer.",
                "Ask for help.", "Offer to help."
            ],
            "exploration": [
                "Search the area.", "Listen closely.", "Light a torch.",
                "Rest for a moment.", "Check your inventory.",
                "Look around.", "Pick the lock.", "Hide.", "Pray to the god-family.",
            ],
            "general": [
                "Wait and listen.", "Look closer.", "Leave the area.",
                "Prepare for combat.", "Prepare to use magic.", "Close your eyes.",
                "Call for help.", "Draw your weapon.", "Take a deep breath.",
                "Step forward.", "Back away slowly.", "Use your senses.",
                "Run away."
            ]
        }

    def get_action_options(self, is_combat=False, is_conversation=False):
        """Returns 3 context-appropriate options."""
        if is_combat:
            pool = self.option_pools["combat"]
        elif is_conversation:
            # Mix conversation with a few general options so the player can escape
            pool = self.option_pools["conversation"] + ["Leave the area.", "Look closer.", "Draw your weapon."]
        else:
            # Default to general + exploration
            pool = self.option_pools["general"] + self.option_pools["exploration"]
            
        return random.sample(pool, 3)

    def start_arrival(self, progress_callback=None):
                # --- ENRICH THE DB WITH RELATIONSHIP STATES ---
        enriched_db = {}
        for name, data in self.character_db.items():
            enriched_db[name] = data.copy()
            if name in self.current_characters:
                enriched_db[name]["relationship"] = self.get_relationship_description(name)
            else:
                enriched_db[name]["relationship"] = ""
        first_action = f"I am currently {self.player_location}. Describe the environment and what I see."
        narration, status, _, _ = self.narrator.ask(
            self.system_prompt,
            first_action,
            self.story_so_far, 
            self.player_location,
            memory_summary=self.memory_summary, 
            current_characters=self.current_characters,
            character_db=enriched_db, 
            max_tokens=250
        )
        if status == "success":
            print("\n" + "-"*40)

            image_prompt, clean_narration, new_location, new_chars, new_char_data, _, _ = process_narration(narration, self.player_name)
            
            # Simple arrival save
            if new_char_data:
                char_name = new_char_data["name"].strip().lower()
                invalid_names = ["name", "<name>", "[name]", "npc", "character", "charactername", "unknown", "example"]
                if char_name not in invalid_names and char_name != self.player_name.lower():
                    name = new_char_data["name"]
                    self.character_db[name] = {
                        "race": new_char_data.get("race", ""),
                        "gender": new_char_data.get("gender", "unknown"),
                        "appearance": new_char_data.get("appearance", ""),
                        "current_outfit": new_char_data.get("current_outfit", "unknown"),
                        "outfit_state": new_char_data.get("outfit_state", "worn"),
                        "personality": new_char_data.get("personality", "Unknown"),
                        "trust_level": 50, "desire_level": 50, "fear_level": 10,
                        "current_location": self.player_location,
                        "last_seen_turn": self.turn_count
                    }
                    self.current_characters = [name]
                    self.save_all_characters_to_csv()
                    print(f"🌟 Arrival Character Saved: {name}")
                else:
                    new_char_data = None

            # ── BLOCK PLACEHOLDERS AND PLAYER AS NPCs ──
            if new_char_data:
                char_name = new_char_data["name"].strip().lower()
                invalid_names = ["name", "<name>",  "[name]", "npc", "character", "charactername", "unknown", "example"]
                
                if char_name in invalid_names:
                    print(f"🚫 Blocked placeholder NPC name: {new_char_data['name']}")
                    new_char_data = None
                elif char_name == self.player_name.lower():
                    print(f"🚫 Blocked LLM from making the player an NPC: {self.player_name}")
                    new_char_data = None
            # ── END BLOCK ──

            # ── ENFORCE DATABASE CLOTHING ──
            if image_prompt and self.current_characters:
                # 1. Strip out clothing words to prevent conflicting descriptions
                clothing_words = [
                    "dress", "armor", "robe", "gown", "tunic", "clothing", "clothes", 
                    "undress", "shirt", "pants", "skirt", "leathers", "mail", "cloak",
                    "naked", "nude", "bare", "nudity", "clad", "wearing", "outfit"
                ]
                for word in clothing_words:
                    image_prompt = re.sub(rf'\b{word}\w*\b', '', image_prompt, flags=re.IGNORECASE)
                
                # 2. Strip the character's name so the generator doesn't skip appending the descriptor
                for char_name in self.current_characters:
                    image_prompt = re.sub(rf'\b{re.escape(char_name)}\b', '', image_prompt, flags=re.IGNORECASE)

                # 3. Clean up leftover spaces and double commas
                image_prompt = re.sub(r'\s+', ' ', image_prompt).strip(', . ')
                
                print(f"🧹 Enforced database outfit. Stripped LLM clothing descriptions.")
            # ── END CLOTHING ENFORCEMENT ──

            # Fallback if the LLM only outputs tags and no actual story
            if not clean_narration.strip():
                print("⚠️ Empty narration from AI during arrival — using fallback")
                clean_narration = f"The world fades into view. You are exactly where you intended to be: {self.player_location}."
            
            # Sanitize image_prompt in arrival
            if image_prompt:
                for known_name in list(self.character_db.keys()):
                    if known_name not in self.current_characters:
                        pattern = rf'\b{re.escape(known_name)}\b'
                        if re.search(pattern, image_prompt, re.IGNORECASE):
                            image_prompt = re.sub(pattern, '', image_prompt, flags=re.IGNORECASE)
                            print(f"🧹 Removed absent character from arrival prompt: {known_name}")
                image_prompt = re.sub(r'\s+', ' ', image_prompt).strip(', .')

            print(clean_narration)

            # Generate 3 context-appropriate options
            options = self.get_action_options(is_combat=self.in_combat, is_conversation=self.in_conversation)

            arrival_prompt = f"establishing shot of {self.player_location}, atmospheric, dark fantasy"

            filename_source = arrival_prompt if arrival_prompt else image_prompt
            safe_filename = re.sub(r'[^a-zA-Z0-9]', '_', filename_source)[:25] + f"_{random.randint(1000,9999)}.png"

            # Build the present NPCs list for the image generator
            present_npcs_data = [] if not self.current_characters else [
                {**self.character_db[n], "name": n}
                for n in self.current_characters
                if n in self.character_db
            ]

            full_path = self.image_generator.generate(
                narration_text=clean_narration,
                filename=safe_filename,
                custom_prompt=image_prompt if image_prompt else arrival_prompt,
                progress_callback=progress_callback,
                allow_gore=False,
                present_npcs=present_npcs_data
            )

            self.story_so_far += f" {clean_narration}"
            
            # This return statement is CRUCIAL for the GUI to work
            return clean_narration, full_path, options, False
            
        return "Error connecting to narrator.", None, [], False
    
    def play_turn(self, action, progress_callback=None):
        # ── DETERMINISTIC MOVEMENT PARSER ──
        dest = extract_destination(action)
        deterministic_move = False
        if dest and dest.lower() != self.player_location.lower():
            old_location = self.player_location
            left_chars = list(self.current_characters)
            self.player_location = dest
            self.current_characters = []
            self.story_so_far = ""
            self.memory_summary += f" Previously left: {old_location}. NPCs left behind: {', '.join(left_chars) if left_chars else 'none'}."
            self.save_all_characters_to_csv()
            print(f"📍 Deterministic move to: {dest}")
            deterministic_move = True
        # ── END MOVEMENT PARSER ──
        blocked_name = None   # ← add this line
        # --- ENRICH THE DB WITH RELATIONSHIP STATES ---
        enriched_db = {}
        for name, data in self.character_db.items():
            enriched_db[name] = data.copy()
            if name in self.current_characters:
                enriched_db[name]["relationship"] = self.get_relationship_description(name)
            else:
                enriched_db[name]["relationship"] = ""
        
        mentioned_char_info = ""
        for char_name, data in self.character_db.items():
            if re.search(rf'\b{re.escape(char_name.lower())}\b', action.lower()):
                loc = data.get("current_location", "Unknown")
                # If they aren't here, tell the AI where they are
                if char_name not in self.current_characters:
                    mentioned_char_info += f"\n[INFO: The player mentioned {char_name}. {char_name} is currently located at: {loc}]"

        # ── FORCE MULTIPLE NPCS FALLBACK ──
        # If the player says "two of you", "both", "three", etc., and we only have 1 NPC
        if any(w in action.lower() for w in ["you two", "two of you", "both of you", "three of you", "two friends", "three women", "pair"]):
            if len(self.current_characters) == 1:
                mentioned_char_info += "\n[SYSTEM: The player expects a second companion. You MUST invent a second character and output a tag formatted EXACTLY like this: [new_character: Lysara | Elf | Female, 25, pale, auburn hair, slender | gossamer silk robes | stern and calculating]]"
                print("🎲 Injected system prompt to force a second NPC.")
        # ──────────────────────────────────

        # Add mentioned_char_info to the player action before sending it
        enhanced_action = action + mentioned_char_info

        # Now pass enriched_db to the narrator instead of self.character_db
        narration, status, _, _ = self.narrator.ask(
            self.system_prompt,
            enhanced_action,
            self.story_so_far,
            self.player_location,
            memory_summary=self.memory_summary,
            current_characters=self.current_characters,
            character_db=enriched_db,
            max_tokens=250
        )

        if status == "success":
            # 1. Unpack
            image_prompt, clean_narration, new_location, new_chars, new_char_data, player_dead, npc_updates = process_narration(narration, self.player_name)

            # ── REPETITION GUARD ──
            def word_overlap(a, b):
                wa = set(a.lower().split())
                wb = set(b.lower().split())
                return len(wa & wb) / max(len(wb), 1)

            if self.story_so_far and word_overlap(clean_narration, self.story_so_far[-300:]) > 0.6:
                print("🔁 Repetition detected — regenerating turn")
                retry_action = enhanced_action + "\n[SYSTEM: The previous response repeated itself. Say something completely different. Do not mention eyes, gaze, or suspicion again.]"
                narration_retry, status_retry, _, _ = self.narrator.ask(
                    self.system_prompt,
                    retry_action,
                    self.story_so_far,
                    self.player_location,
                    memory_summary=self.memory_summary,
                    current_characters=self.current_characters,
                    character_db=enriched_db,
                    max_tokens=250
                )
                if status_retry == "success":
                    image_prompt, clean_narration, new_location, new_chars, new_char_data, player_dead, npc_updates = process_narration(narration_retry, self.player_name)
                    print("🔁 Regenerated turn")
            # ── END REPETITION GUARD ──

            if not clean_narration.strip():
                print("⚠️ Empty narration from AI — using fallback")
                clean_narration = "The moment stretches on in silence. Someone needs to act."

            # Apply NPC outfit/appearance updates from this turn
            for upd in npc_updates:
                upd_name = upd.get("name", "").strip()
                if not upd_name or upd_name.lower() in ["name", "<name>", "npc", "character"]:
                    continue
                
                # If the character doesn't exist yet, create a skeleton so it doesn't crash
                if upd_name not in self.character_db:
                    self.character_db[upd_name] = {
                        "race": "elf", "gender": "female", "appearance": "beautiful", 
                        "current_outfit": "unknown", "outfit_state": "worn",
                        "personality": "unknown", "trust_level": 50, "desire_level": 50, "fear_level": 10,
                        "current_location": self.player_location, "last_seen_turn": self.turn_count
                    }
                    print(f"🌟 Auto-created skeleton character from npc_update: {upd_name}")
                
                if "current_outfit" in upd:
                    # ONLY allow stripping if the player explicitly asked for it
                    if upd["current_outfit"].lower() == "none":
                        if not any(w in action.lower() for w in ["strip", "undress", "naked", "nude", "remove clothes"]):
                            print(f"🚫 Blocked hallucinated stripping for {upd_name}")
                            continue # Skip this update
                    
                    self.character_db[upd_name]["current_outfit"] = upd["current_outfit"]

                if "outfit_state" in upd:
                    self.character_db[upd_name]["outfit_state"] = upd["outfit_state"]

                print(f"👗 NPC updated: {upd_name} → outfit={upd.get('current_outfit','?')}, state={upd.get('outfit_state','?')}")

            # 1 ── FORCE OUTFIT REMOVAL FALLBACK ──
            if any(w in action.lower() for w in ["strip", "undress", "naked", "nude", "remove clothes"]):
                if self.current_characters:
                    for target in self.current_characters:
                        if target in self.character_db:
                            self.character_db[target]["current_outfit"] = "none"
                            self.character_db[target]["outfit_state"] = "removed"
                            print(f"👗 Forced outfit removal for {target} based on player action.")
            # ───────────────────────────────────e
            # ── END VALIDATION ──

            # 2. ⬇️ COMPUTE FLAGS ONCE, HERE ⬇️
            player_moved = action_contains(action, MOVEMENT_WORDS)
            is_combat = action_contains(action, COMBAT_WORDS)
            is_death = action_contains(action, DEATH_WORDS)
            is_leaving = action_contains(action, LEAVING_WORDS)
            action_is_gore = action_contains(action, GORE_WORDS)

            # --- PERSISTENT CONVERSATION STATE ---
            action_has_convo = action_contains(action, CONVERSATION_WORDS) or ('"' in action)
            narration_has_convo = ('"' in clean_narration)
            
            if action_has_convo or narration_has_convo:
                self.in_conversation = True
            elif is_leaving or player_moved or not self.current_characters:
                self.in_conversation = False
            # -------------------------------------

            # 3. Death keyword fallback (uses is_death)
            if is_death and not player_dead:
                print("💀 Death keyword detected — forcing player_dead=True")
                player_dead = True

            # --- RANDOM EVENTS (1 in 20 chance) ---
            if random.randint(1, 10) == 1 and not is_combat and not player_moved:
                print("🎲 RANDOM EVENT TRIGGERED!")
                # Pick a random event
                event_type = random.choice(["ambush", "quest", "omen"])
                
                if event_type == "ambush":
                    enhanced_action += "\n[SYSTEM: A sudden ambush occurs! An enemy attacks the player.]"
                    self.gore_turns = 6
                elif event_type == "quest":
                    enhanced_action += "\n[SYSTEM: A mysterious stranger approaches with a desperate plea for help.]"
                elif event_type == "omen":
                    enhanced_action += "\n[SYSTEM: The environment shifts ominously. A dark omen of severe calamity appears in the sky.]"

            # --- COMBAT / GORE TIMERS ---

            # Combat starts or extends the fight
            if is_combat or is_death:
                self.gore_turns = 6   # 3 turns of fighting + 3 turns of aftermath

            # Seeing gore (looking at a corpse, examining a wound) refreshes gore only
            if action_is_gore:
                self.gore_turns = max(self.gore_turns, 3)

            # AI-described gore also refreshes the window
            if not action_is_gore and action_contains(clean_narration, GORE_WORDS):
                self.gore_turns = max(self.gore_turns, 3)

            # Decrement at the end of turn resolution
            if self.gore_turns > 0:
                self.gore_turns -= 1

            # Compute what the image generator needs
            allow_gore = self.gore_turns > 0

            print(f"🩸 Gore: {self.gore_turns} turns left")

            # 4. Location update (uses player_moved)
            location_changed = False
            
            if not deterministic_move and new_location and player_moved:
                old_location = self.player_location
                self.player_location = new_location
                location_changed = True
                print(f"📍 Location updated to: {self.player_location}")    # 1. Build a quick mini-summary of the scene you are leaving
                # Wipe the short-term dialogue, but KEEP the arrival text
                self.save_all_characters_to_csv()
            elif not deterministic_move and new_location:
                current_words = set(self.player_location.lower().split())
                new_words = set(new_location.lower().split())
                overlap = len(current_words & new_words) / max(len(new_words), 1)
                if overlap < 0.3:
                    self.player_location = new_location
                    print(f"📍 Location updated to: {self.player_location}")

            # ── SPAWN GUARD ──
            action_is_solo = action_contains(action, SOLO_WORDS)
            explicit_ask = any(
                phrase in action.lower()
                for phrase in ["look for", "call out", "who is here", "find someone",
                               "search for a person", "is anyone", "anyone here"]
            )
            # If the name was just mentioned in the story, allow it
            mentioned_in_story = new_char_data and (new_char_data["name"].lower() in self.story_so_far.lower())

            if new_char_data and not explicit_ask and not mentioned_in_story:
                if player_moved or deterministic_move or is_combat or is_leaving or action_is_solo:
                    print(f"🚫 Blocked spawned character during movement/combat/solo: {new_char_data['name']}")
                    blocked_name = new_char_data["name"]
                    new_char_data = None
            # ── END SPAWN GUARD ──

            # 5. Character filter
            # We trust the LLM's [characters:] tag to tell us who is in the room.
            if new_chars is not None:
                valid_chars = []
                for char in new_chars:
                    # If the character is already in our database, or is the new character being introduced
                    if char in self.character_db or (new_char_data and char == new_char_data["name"]):
                        valid_chars.append(char)
                    else:
                        print(f"⚠️ Blocked hallucinated character: {char}")
                
                self.current_characters = valid_chars
                
                # If the LLM introduced a new character, make sure they are added to the list
                if new_char_data and new_char_data["name"] not in self.current_characters:
                    self.current_characters.append(new_char_data["name"])

            elif self.current_characters:
                # If the LLM forgot the [characters:] tag entirely, keep the old ones ONLY if we didn't move
                if location_changed:
                    print(f"🚪 Location changed. Leaving previous NPCs behind.")
                    self.current_characters = []
                else:
                    print(f"⚠️ AI named no valid characters. Keeping previous: {self.current_characters}")
                    # But if the LLM DID introduce a new character in the prose, add them!
                    if new_char_data and new_char_data["name"] not in self.current_characters:
                        self.current_characters.append(new_char_data["name"])
                        print(f"🌟 Added new_character {new_char_data['name']} to current list.")
            else:
                self.current_characters = []

            # Keep these lines right below the filter:
            self.apply_relationship_changes(action, self.current_characters)

            for char_name in list(self.current_characters):
                reject_pattern = rf'\b(?:not|leave)\s+{re.escape(char_name.lower())}\b'
                if re.search(reject_pattern, action.lower()):
                    self.current_characters.remove(char_name)
                    print(f"🚪 Rejected: {char_name}")

            # 6. NPC follow-prevention (uses is_leaving)
            if is_leaving and self.current_characters:
                print(f"🚪 Player left — clearing NPCs: {self.current_characters}")
                self.current_characters = []

            # 7. Save new character
            if new_char_data:
                name = new_char_data["name"]
                if name not in self.character_db:
                    # 1. Add them to the live dictionary
                    self.character_db[name] = {
                        "race": new_char_data.get("race", ""),
                        "gender": new_char_data.get("gender", "unknown"), 
                        "appearance": new_char_data.get("appearance", ""),
                        "current_outfit": new_char_data.get("current_outfit", "unknown"),
                        "outfit_state": new_char_data.get("outfit_state", "worn"),
                        "personality": new_char_data.get("personality", "Unknown"),
                        "trust_level": 50,
                        "desire_level": 50,
                        "fear_level": 10,
                        "current_location": self.player_location,
                        "last_seen_turn": self.turn_count
                    }
                    
                    # 2. Append them to the CSV file
                    with open(CHARACTERS_CSV_PATH, "a", newline="") as f:
                        writer = csv.writer(f)
                        # If the file is empty, we need to write the header first
                        if os.path.getsize(CHARACTERS_CSV_PATH) == 0:
                            writer.writerow([
                                "name", "race", "gender", "appearance", "current_outfit", "outfit_state",
                                "personality", "trust_level", "desire_level", "fear_level",
                                "current_location", "last_seen_turn"
                            ])
                        writer.writerow([
                            name,
                            new_char_data.get("race", ""),
                            new_char_data.get("gender", "unknown"),
                            new_char_data.get("appearance", ""),
                            new_char_data.get("current_outfit", "unknown"),
                            new_char_data.get("outfit_state", "worn"),
                            new_char_data.get("personality", "Unknown"),
                            50, 50, 10,
                            self.player_location,
                            self.turn_count
                        ])
                    print(f"🌟 NEW CHARACTER SAVED TO CSV: {name}")

            # ── SANITIZE IMAGE PROMPT ──
            if image_prompt:
                # Remove any known NPC not currently present
                for known_name in list(self.character_db.keys()):
                    if known_name not in self.current_characters:
                        pattern = rf'\b{re.escape(known_name)}\b'
                        if re.search(pattern, image_prompt, re.IGNORECASE):
                            image_prompt = re.sub(pattern, '', image_prompt, flags=re.IGNORECASE)
                            print(f"🧹 Removed absent character from image prompt: {known_name}")
                # Remove the just-blocked new character, if any
                if blocked_name:
                    image_prompt = re.sub(rf'\b{re.escape(blocked_name)}\b', '', image_prompt, flags=re.IGNORECASE)
                    print(f"🧹 Removed blocked character from image prompt: {blocked_name}")
                image_prompt = re.sub(r'\s+', ' ', image_prompt).strip(', .')

            # 8. Composition override
            force_empty_scene = False
            
            # If there are NO characters, the image prompt must be purely environmental
            if not self.current_characters:
                # Check if the LLM tried to sneak a character into the prompt
                char_words = ["elf", "woman", "man", "warrior", "figure", "person", "character", "she", "he", "her", "him"]
                prompt_lower = image_prompt.lower() if image_prompt else ""
                
                if any(re.search(rf'\b{word}\b', prompt_lower) for word in char_words):
                    print("🎨 Override: AI tried to draw a character in an empty room. Forcing environment shot.")
                    image_prompt = f"wide establishing shot of {self.player_location}, atmospheric, moody lighting, no characters in frame"
                    force_empty_scene = True
                    
            elif image_prompt:
                prompt_lower = image_prompt.lower()
                is_portrait = action_contains(prompt_lower, [
                    "portrait", "close-up", "face", "eyes", "headshot",
                    "sunken", "gaunt", "hair", "lips"
                ])

                if is_portrait and not self.current_characters:
                    image_prompt = f"wide establishing shot of {self.player_location}, atmospheric, moody lighting, no characters in frame"
                    print("🎨 Override: AI drew a person while player is alone. Forcing environment shot.")
                    force_empty_scene = True
                elif is_combat:
                    image_prompt = "close up of an elven warrior swinging a sword, blood splattering, fierce expression, dynamic action pose, motion blur, dark fantasy"
                    print("🎨 Override: combat detected, forcing wide action shot")

            # 9. Force dynamic poses for actions
            action_verbs = ["dance", "run", "jump", "embrace", "kiss", "fight", "swing", "cast a spell", "fly", "swim",
                            "crawl", "climb"]
            if any(re.search(rf'\b{re.escape(word)}\b', action.lower()) for word in action_verbs):
                if image_prompt and not force_empty_scene:
                    # Boost the action weight
                    image_prompt += ", (dynamic pose:1.3), (motion blur:1.2)"
                    print("🎨 Action detected: boosting dynamic pose in image prompt")

            if action_contains(action, ["look at", "examine", "inspect", "coffin"]):
                print("🎨 Override: looking at an object, preventing NPC portraits")
                force_empty_scene = True 
                # If the AI tried to give us an NPC portrait, replace it with the object
                if image_prompt and action_contains(image_prompt, self.current_characters):
                     image_prompt = f"close up of {action}, dark fantasy, atmospheric"

            # --- STRIP GORE IF TIMERS EXPIRED ---
            if self.gore_turns == 0 and image_prompt:
                for word in GORE_WORDS:
                    image_prompt = re.sub(rf'\b{re.escape(word)}\b', '', image_prompt, flags=re.IGNORECASE)
                image_prompt = re.sub(r'\s+', ' ', image_prompt).strip(', .')
                if len(image_prompt) < 15:
                    image_prompt = f"wide establishing shot of {self.player_location}, atmospheric, moody lighting"
                print("🧼 Gore stripped (window expired)")

            if player_dead:
                print("💀 Death image override — forcing gore aftermath")
                image_prompt = f"bloody aftermath of violent death, viscera on ground, {self.player_location}, dark fantasy"
                force_empty_scene = True
                self.gore_turns = 6
                allow_gore = True

            # ── ENFORCE DATABASE CLOTHING ──
            if image_prompt and self.current_characters:
                # 1. Strip out clothing words to prevent conflicting descriptions
                clothing_words = [
                    "dress", "armor", "robe", "gown", "tunic", "clothing", "clothes", 
                    "undress", "shirt", "pants", "skirt", "leathers", "mail", "cloak",
                    "naked", "nude", "bare", "nudity", "clad", "wearing", "outfit"
                ]
                for word in clothing_words:
                    image_prompt = re.sub(rf'\b{word}\w*\b', '', image_prompt, flags=re.IGNORECASE)
                
                # 2. Strip the character's name so the generator doesn't skip appending the descriptor
                for char_name in self.current_characters:
                    image_prompt = re.sub(rf'\b{re.escape(char_name)}\b', '', image_prompt, flags=re.IGNORECASE)

                # 3. Clean up leftover spaces and double commas
                image_prompt = re.sub(r'\s+', ' ', image_prompt).strip(', . ')
                
                print(f"🧹 Enforced database outfit. Stripped LLM clothing descriptions.")
            # ── END CLOTHING ENFORCEMENT ──

            # 10. Filename + image gen (unchanged)
            safe_filename = re.sub(r'[^a-zA-Z0-9]', '_', image_prompt)[:25] + f"_{random.randint(1000,9999)}.png"
            # Generate 3 context-appropriate options
            options = self.get_action_options(is_combat=self.in_combat, is_conversation=self.in_conversation)
            present_npcs_data = [] if force_empty_scene else [
                {**self.character_db[n], "name": n}
                for n in self.current_characters
                if n in self.character_db
            ]
            full_path = self.image_generator.generate(
                narration_text=clean_narration,
                filename=safe_filename,
                custom_prompt=image_prompt or None,
                progress_callback=progress_callback,
                allow_gore=allow_gore,
                present_npcs=present_npcs_data
            )
            threading.Thread(target=self.update_memory, args=(clean_narration,), daemon=True).start()
            return clean_narration, full_path, options, player_dead

        return "Error connecting to narrator.", None, [], False
    
    def save_all_characters_to_csv(self):
        """Overwrites the whole CSV with the current state of the dictionary."""
        with open(CHARACTERS_CSV_PATH, "w", newline="") as f:
            fieldnames = [
                "name", "race", "gender", "appearance", "current_outfit", "outfit_state",
                "personality", "trust_level", "desire_level", "fear_level",
                "current_location", "last_seen_turn"
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for name, data in self.character_db.items():
                writer.writerow({
                    "name": name,
                    "race": data.get("race", ""),
                    "gender": data.get("gender", "unknown"),
                    "appearance": data.get("appearance", "Unknown"),
                    "current_outfit": data.get("current_outfit", "unknown"),
                    "outfit_state": data.get("outfit_state", "worn"),
                    "personality": data.get("personality", "Unknown"),
                    "trust_level": data.get("trust_level", 50),
                    "desire_level": data.get("desire_level", 50),
                    "fear_level": data.get("fear_level", 10),
                    "current_location": data.get("current_location", "Unknown"),
                    "last_seen_turn": data.get("last_seen_turn", 0),
                })

    def apply_relationship_changes(self, action, current_chars):
        """Adjust trust/desire/fear for NPCs present based on player action."""
        action_lower = action.lower()
    
        # Define what counts as what
        hostile = action_contains(action_lower, ["attack", "kill", "stab", "threaten", "insult", "yell at", "punch", "draw my sword"])
        kind = action_contains(action_lower, ["help", "heal", "protect", "save", "comfort", "console", "reassure"])
        gift = action_contains(action_lower, ["give", "offer", "hand over", "gift", "share"])
        intimate = action_contains(action_lower, ["kiss", "caress", "hold hands", "embrace", "flirt"])
    
        for char_name in current_chars:
            if char_name not in self.character_db:
                continue
            c = self.character_db[char_name]
        
            if hostile:
                c["trust_level"] = max(0, c.get("trust_level", 50) - 15)
                c["fear_level"] = min(100, c.get("fear_level", 10) + 20)
                c["desire_level"] = max(0, c.get("desire_level", 50) - 10)
            elif kind:
                c["trust_level"] = min(100, c.get("trust_level", 50) + 10)
                c["fear_level"] = max(0, c.get("fear_level", 10) - 5)
            elif gift:
                c["trust_level"] = min(100, c.get("trust_level", 50) + 15)
                c["desire_level"] = min(100, c.get("desire_level", 50) + 10)
            elif intimate:
                # Only increases desire if trust is already established
                if c.get("trust_level", 50) > 60:
                    c["desire_level"] = min(100, c.get("desire_level", 50) + 15)
                else:
                    c["trust_level"] = max(0, c.get("trust_level", 50) - 10)
                    c["fear_level"] = min(100, c.get("fear_level", 10) + 10)
        
            # Always update where they were last seen
            c["current_location"] = self.player_location
            c["last_seen_turn"] = self.turn_count

    def get_relationship_description(self, char_name):
        """Convert numbers to a phrase the LLM can act on."""
        if char_name not in self.character_db:
            return ""
        c = self.character_db[char_name]
        trust = int(c.get("trust_level", 50))
        desire = int(c.get("desire_level", 50))
        fear = int(c.get("fear_level", 10))
        
        if trust < 20: trust_desc = "openly hostile, refuses to help"
        elif trust < 40: trust_desc = "wary, speaks in short clipped sentences"
        elif trust < 60: trust_desc = "polite but distant"
        elif trust < 80: trust_desc = "friendly, willing to help"
        else: trust_desc = "deeply loyal, would take risks for the player"
        
        if desire < 20: desire_desc = "cold, uninterested"
        elif desire < 40: desire_desc = "curious but reserved"
        elif desire < 60: desire_desc = "warm, drawn to the player"
        elif desire < 80: desire_desc = "visibly attracted, seeks closeness"
        else: desire_desc = "infatuated, possessive"
        
        fear_desc = ""
        if fear > 70: fear_desc = " terrified of the player,"
        elif fear > 40: fear_desc = " visibly uneasy,"
        
        return f"{trust_desc}, {desire_desc}{fear_desc}"

    def update_memory(self, new_narration):
        self.turn_count += 1
        self.story_so_far += f" {new_narration}"
        
        # Cap growth — keep only last ~600 chars
        if len(self.story_so_far) > 600:
            cut = self.story_so_far[-600:]
            space = cut.find(' ')
            if space != -1:
                cut = cut[space+1:] # skip past the broken word
            self.story_so_far = cut
        
        # Every 3 turns, summarize and clear
        if self.turn_count % 3 == 0:
            print("\n" + "*"*60)
            print("--- TRIGGERING MEMORY SUMMARIZATION ---")
            print(f"SHORT-TERM HISTORY BEING SUMMARIZED:\n{self.story_so_far}")
            print("*"*60 + "\n")

            # Build character reference for the summarizer
            chars_reference = ""
            for name in self.current_characters:
                if name in self.character_db:
                    desc = self.character_db[name]
                    chars_reference += f"- {name}: {desc['appearance']}\n"
            if not chars_reference:
                chars_reference = "(no characters present)"

            # Build the summary prompt ◄── HERE
            summary_prompt = build_summary_prompt(
                self.player_name,
                self.player_location,
                chars_reference,
                self.story_so_far
            )
            
            summary, status, _, _ = self.narrator.ask(
                "You are a summarizer.",#
                "Summarize.",
                "",
                "Memory",
                memory_summary="",
                character_db={}, 
                current_characters=[], 
                max_tokens=120, 
                override_prompt=summary_prompt
            )

            if status == "success":
                # Clean the summary to remove LLM conversational filler
                clean_summary = summary.replace("Here is a summary of the RPG events in exactly 3 sentences:", "").strip()
                clean_summary = clean_summary.replace("Summary:", "").strip()
                self.memory_summary += f" {clean_summary}"
                # Keep the summary from getting too long
                self.memory_summary = self.memory_summary[-500:] 
                print(f"NEW LONG-TERM MEMORY: {self.memory_summary}")
            # Clear the short term memory
                self.story_so_far = new_narration
            else:
                # If Ollama fails to summarize, DO NOT wipe the memory, or the game will forget everything.
                print("SUMMARY FAILED. Keeping short-term memory intact.")

            if self.turn_count % 3 == 0:
                self.save_all_characters_to_csv()