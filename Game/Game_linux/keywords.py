import re

def action_contains(text, word_list):
    text_lower = text.lower()
    for word in word_list:
        # \b ensures it only matches whole words, not sub-strings (e.g., 'blood' won't match 'blood-red')
        if re.search(rf'\b{re.escape(word.lower())}\b', text_lower):
            return True
    return False

MOVEMENT_WORDS = [
    "walk", "run", "enter", "leave", "exit", "climb",
    "travel", "step", "head", "follow", "accompany", "journey",
    "depart", "return", "ride", "away", "out of"
]

COMBAT_WORDS = [
    "attack", "strike", "slash", "stab", "kill", "fight",
    "draw my sword", "draw your weapon", "punch",
    "hit", "shoot", "fire magic"
]

GORE_WORDS = [
    "blood", "gore", "corpse", "wound", "dead", "decapitate", "entrails", "viscera",
    "entrails", "viscera", "guts", "flesh", "limb", "severed", "mutilated", "disembowel"
]

DEATH_WORDS = [
    "suicide", "kill myself", "stab myself", "slit my throat",
    "i die", "i'm dead", "im dead", "end my life", "take my own life",
    "player dead", "player_death"
]

LEAVING_WORDS = [
    "leave", "walk away", "walk out", "depart", "goodbye",
    "ignore him", "ignore her", "turn my back", "walk past",
    "continue past", "walk deeper", "deeper into"
]

SOLO_WORDS = ["swim", "dive", "sleep", "rest", "read",
              "pray", "meditate", "run", "climb", "jump", "explore",
              "sit", "lie down", "wait", "watch", "listen", "breathe"]

CONVERSATION_WORDS = [
                "Demand answers.", "Try to seduce them.", "Offer a bribe.",
                "Threaten them.", "Reassure them.", "Tell a lie.",
                "Reveal the truth.", "Insult them.", "Apologize.",
                "Ask about their past.", "Pull them closer.",
                "Ask for help.", "Offer to help."
]