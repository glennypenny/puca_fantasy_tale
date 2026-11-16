import re

def process_narration(narration, player_name):
    # 1. Extract location from narration
    new_location = None
    loc_match = re.search(r'\[location:\s*(.+?)\]', narration, re.IGNORECASE)
    if loc_match:
        new_location = loc_match.group(1).strip()
        # Remove the location tag from the text
        narration = narration.replace(loc_match.group(0), "").strip()

    # 2. Extract CURRENT Characters (Plural)
    new_characters = None

    # Fallback: catch bare-name lists at the end of the narration
    if new_characters is None:
        lines = narration.rstrip().split("\n")
        last_line = lines[-1].strip().strip(",.")
        # Looks like name/s without []
        if "," in last_line and len(last_line) < 100:
            potential = [n.strip() for n in last_line.split(",") if n.strip()]
            # Every token starts with uppercase letter (loose name check)
            if potential and all(re.match(r'^[A-Z]', n) for n in potential):
                # Drop "None" if mixed in
                new_characters = [n for n in potential if n.lower() != "none"]
                narration = narration.replace(last_line, "").strip()
                print(f"⚠️ Recovered bare character list: {new_characters}")

    char_match = re.search(r'\[?characters:\s*(.+?)(?:\]|\n|$)', narration, re.IGNORECASE)
    if char_match:
        char_string = char_match.group(1).strip()
        if char_string.lower() != "none":
            new_characters = [c.strip() for c in char_string.split(",") if c.strip().lower() != "none"]
        narration = narration.replace(char_match.group(0), "").strip()    
    narration = re.sub(r'characters:.*?(?:\n|$)', '', narration, flags=re.IGNORECASE).strip()
    # 3. Extract NEW Character (if one was just introduced)
    new_char_data = None
    new_char_match = re.search(r'\[?new_character:\s*(.+?)(?:\]|\n|$)', narration, re.IGNORECASE)
    if new_char_match:
        raw_text = new_char_match.group(1).strip()
        
        if "|" in raw_text:
            parts = [p.strip() for p in raw_text.split('|')]
        else:
            parts = [p.strip() for p in raw_text.split(',')]

        # Extract gender automatically from the text
        gender = "unknown"
        if "female" in raw_text.lower():
            gender = "female"
        elif "male" in raw_text.lower():
            gender = "male"

        if len(parts) >= 5:
            # New format: Name | RACE | appearance | OUTFIT | personality
            new_char_data = {
                "name": parts[0],
                "race": parts[1],
                "gender": gender,
                "appearance": parts[2],
                "current_outfit": parts[3],
                "outfit_state": "worn",
                "personality": parts[4],
            }
        elif len(parts) >= 3:
            # Legacy: Name | appearance | personality
            new_char_data = {
                "name": parts[0],
                "race": "",
                "gender": gender,
                "appearance": parts[1],
                "current_outfit": "unknown",
                "outfit_state": "worn",
                "personality": parts[2],
            }
        elif len(parts) >= 2:
            new_char_data = {
                "name": parts[0],
                "race": "",
                "gender": gender,
                "appearance": parts[1],
                "current_outfit": "unknown",
                "outfit_state": "worn",
                "personality": "Unknown",
            }
        if new_char_data is not None:
            # Safety check: Ensure the character data is valid
            if new_characters is None:
                new_characters = []
        # Add the character to the list of new characters if it's not already there
            if new_char_data["name"] not in new_characters:
                new_characters.append(new_char_data["name"])

        # Remove the tag from the text so the player doesn't see it
        narration = narration.replace(new_char_match.group(0), "").strip()

    narration = re.sub(r'SYSTEM:.*?(?:\n|$)', '', narration, flags=re.IGNORECASE).strip()

    # 4. Check for death
    player_dead = False
    if re.search(r'\[player_death\]', narration, re.IGNORECASE):
        player_dead = True
        narration = re.sub(r'\[player_death\]', '', narration, flags=re.IGNORECASE).strip()

    # 5. Extract NPC outfit updates (must run BEFORE image_prompt patterns)
    npc_updates = []
    for match in re.finditer(r'\[npc_update:\s*(.+?)\]', narration, re.IGNORECASE):
        raw = match.group(1).strip()
        if "|" in raw:
            parts = [p.strip() for p in raw.split("|")]
            if len(parts) >= 2:
                update = {"name": parts[0]}
                for part in parts[1:]:
                    if ":" in part:
                        k, v = part.split(":", 1)
                        update[k.strip()] = v.strip()
                npc_updates.append(update)
        narration = narration.replace(match.group(0), "").strip()

    patterns = [
        # Pattern 1: Catch missing closing bracket (only for image_prompt)
        r'\[image[\s_]?prompt:\s*(.+?)(?:\]|$)',
        # Pattern 2: Normal with bracket
        r'\[image[\s_]?prompt:\s*(.+?)\]',
        # Pattern 3: Capitalized with bracket
        r'\[Image[\s_]?Prompt:\s*(.+?)\]',
        # Pattern 4: Fallback for any bracketed text
        r'\[(.+?)\]',
    ]

    for p in patterns:
        match = re.search(p, narration, re.IGNORECASE)
        if match:
            # Extract the prompt and strip out accidental double-tags
            clean_prompt = match.group(1).strip(". ")
            clean_prompt = re.sub(r'^image[\s_]?prompt:\s*', '', clean_prompt, flags=re.IGNORECASE)
            # Remove the matched tag from the narration text
            clean_narration = narration.replace(match.group(0), "").strip()
            # Extra safety: remove any dangling brackets left behind
            clean_narration = clean_narration.replace("[", "").replace("]", "").strip()
            # Strip the player's name from the image prompt
            # Strip the player's name from the image prompt safely
            if player_name:
                clean_prompt = re.sub(r'\b' + re.escape(player_name) + r'\b', '', clean_prompt, flags=re.IGNORECASE)
                clean_prompt = clean_prompt.strip(", ") # Clean up leftover commas and spaces
            return clean_prompt, clean_narration, new_location, new_characters, new_char_data, player_dead, npc_updates

    # No bracketed prompt found — use first two sentences as fallback
    sentences = narration.replace("\n", " ").split(". ")
    return ". ".join(sentences[:2])[:180], narration, new_location, new_characters, new_char_data, player_dead, npc_updates
