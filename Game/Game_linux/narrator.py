import requests

class Narrator:
    def __init__(self, model="hf.co/richardyoung/Qwen2.5-7B-Instruct-abliterated-GGUF:latest"):
        self.url = "http://127.0.0.1:11434/api/generate"
        self.model = model
        self.default_max_tokens = 250

    def ask(self, system_prompt, player_action, story_so_far, player_location, memory_summary, current_characters, character_db, max_tokens=None, override_prompt=None):
        tokens = max_tokens if max_tokens is not None else self.default_max_tokens
        
        if override_prompt:
            full_prompt = override_prompt
        else:
            # Build the Character Sheets dynamically
            char_sheets = ""
            for name in current_characters:
                if name in character_db:
                    desc = character_db[name]
                    rel_desc = desc.get("relationship", "")
                    if rel_desc:
                        char_sheets += f"- {name}: {desc['appearance']}. Personality: {desc['personality']}. CURRENT BEHAVIOR: {rel_desc}\n"
                    else:
                        char_sheets += f"- {name}: {desc['appearance']}. Personality: {desc['personality']}\n"
            
            if not char_sheets:
                char_sheets = "None (Player is alone)"

            full_prompt = f"""{system_prompt}

    CHARACTER SHEETS (Use these exact descriptions):
    {char_sheets}

    MEMORY OF PAST EVENTS: {memory_summary}

    RECENT STORY: {story_so_far}

    PLAYER ACTION: {player_action}

    PLAYER LOCATION: {player_location}

    NARRATOR:"""
            
        print("\n" + "="*60)
        print("PROMPT BEING SENT TO OLLAMA:")
        print("="*60)
        print(full_prompt)
        print("="*60 + "\n")

        data = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
            "keep_alive": "30m",
            "options": {
                "num_predict": tokens,
                "temperature": 0.6,
                "num_gpu": 0,
                "num_thread": 14,
                "num_batch": 2048,
                "num_ctx": 2048,  
                "stop": [
                    "PLAYER ACTION:", 
                    "PLAYER LOCATION:", 
                    "STORY SO FAR:", 
                    "NARRATOR:",
                    ],
            },
        }
        try:
            resp = requests.post(self.url, json=data, timeout=300)
            if resp.status_code == 200:
                text = resp.json()['response'].strip()              
                print("\n" + "=" * 60)
                print("🔍 RAW OLLAMA OUTPUT (before any parsing or filtering):")
                print("=" * 60)
                print(repr(text))
                print("=" * 60 + "\n")
                return text, "success", "", ""
            else:
                # --- ADD THIS ELSE BLOCK ---
                print(f"OLLAMA HTTP ERROR {resp.status_code}: {resp.text}")
                return f"[Ollama Error: {resp.status_code}]", "error", "", ""
        except Exception as e:
            print(f"REQUEST FAILED: {e}")
            return f"[Connection Error: {e}]", "error", "", ""
        print(text)