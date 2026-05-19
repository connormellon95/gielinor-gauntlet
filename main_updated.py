import tkinter as tk
from tkinter import messagebox
import json
import random
import os
import winsound
import glob
from PIL import Image, ImageTk

# -------------------------
# GLOBALS
# -------------------------
player_bar = None
player_cards = []   # list of frames per player (for coin popup positioning)
coin_img = None     # PhotoImage cached
current_song_path = None
sfx_resume_job = None
cape_imgs = []        # list of PhotoImages for placements 1..5
game_over_shown = False

# Rune icons cache
rune_icons = {}   # name -> PhotoImage
back_icon = None

# Barrows chest cached images (optional)
chest_closed_img = None
chest_open_img = None
barrows_dharok_img = None
barrows_karil_img = None
# -------------------------
# PATHS
# -------------------------
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
ANIM_DIR   = os.path.join(ASSETS_DIR, "anims")
MUSIC_DIR  = os.path.join(BASE_DIR, "Music")
# Barrows brothers images (PNG)
BARROWS_DHAROK_PATH  = os.path.join(ASSETS_DIR, "dh.png")
BARROWS_KARIL_PATH = os.path.join(ASSETS_DIR, "karil.png")
RUNES_DIR = os.path.join(ASSETS_DIR, "runes")
RUNE_SIZE = (64, 64)
# Cape images for final placements (put these PNGs in /assets)
INFERNAL_CAPE_PATH = os.path.join(ASSETS_DIR, "infernal_cape.png")
FIRE_CAPE_PATH     = os.path.join(ASSETS_DIR, "fire_cape.png")
OBBY_CAPE_PATH     = os.path.join(ASSETS_DIR, "obby_cape.png")
TEAM_CAPE_PATH     = os.path.join(ASSETS_DIR, "team_cape.png")
RED_CAPE_PATH      = os.path.join(ASSETS_DIR, "red_cape.png")

QUESTIONS_PATH   = os.path.join(BASE_DIR, "questions.json")
PUNISHMENTS_PATH = os.path.join(BASE_DIR, "punishments.json")

COINS_PATH = os.path.join(ASSETS_DIR, "coins.png")  # use PNG for transparency

# Optional Barrows chest images
CHEST_CLOSED_PATH = os.path.join(ASSETS_DIR, "barrows_chest_closed.png")
CHEST_OPEN_PATH   = os.path.join(ASSETS_DIR, "barrows_chest_open.png")

# -------------------------
# OSRS THEME
# -------------------------
C_BG        = "#1d1b16"
C_PANEL     = "#2a271f"
C_PARCH     = "#d6c7a1"
C_PARCH2    = "#cdbb8d"
C_BORDER    = "#6f5f3b"
C_GOLD      = "#c9a227"
C_TEXT_DARK = "#1a140b"
C_TEXT_LIGHT= "#efe6d3"
C_RED       = "#b74a3c"
C_GREEN     = "#3da35a"

FONT_UI     = ("Georgia", 11)
FONT_UI_B   = ("Georgia", 11, "bold")
FONT_HEAD   = ("Georgia", 16, "bold")
FONT_TILE   = ("Georgia", 12, "bold")
FONT_SMALL  = ("Georgia", 10)

PAD_X = 6
PAD_Y = 6
VALUES = [100, 200, 300, 400, 500]

#  Toggle these probabilities
BONUS_CHANCE    = 0.15
PUNISH_CHANCE   = 0.19   

#  Every tile click has this chance to trigger a mini-game
MINIGAME_CHANCE = 0.17   

# -------------------------
# LOAD DATA
# -------------------------
with open(QUESTIONS_PATH, "r", encoding="utf-8") as f:
    board = json.load(f)

with open(PUNISHMENTS_PATH, "r", encoding="utf-8") as f:
    PUNISHMENTS = json.load(f)

# -------------------------
# GAME STATE
# -------------------------
players = []
scores = []
clue_buttons = []
selected_clues = []
selected_player = None  # IntVar after window is created

# -------------------------
# HELPERS
# -------------------------
USED_BG = "#9c9c9c"
USED_FG = "#5f5f5f"

def mark_tile_used(cat_idx: int, clue_idx: int):
    w = clue_buttons[cat_idx][clue_idx]
    info = w.grid_info()  # remember its grid position
    w.destroy()

    used = tk.Label(
        board_frame,
        text="—",
        font=FONT_TILE,
        bg=USED_BG,
        fg=USED_FG,
        bd=2,
        relief="ridge"
    )
    used.grid(
        row=info["row"],
        column=info["column"],
        padx=info.get("padx", PAD_X),
        pady=info.get("pady", PAD_Y),
        sticky=info.get("sticky", "nsew")
    )

    clue_buttons[cat_idx][clue_idx] = used


    # Keep placeholder so indexing still works
    clue_buttons[cat_idx][clue_idx] = used

def normalize(s: str) -> str:
    return " ".join(s.strip().lower().split())

def center_window(win, parent):
    win.update_idletasks()
    w = win.winfo_width()
    h = win.winfo_height()
    if w <= 1 or h <= 1:
        w = win.winfo_reqwidth()
        h = win.winfo_reqheight()

    px = parent.winfo_x()
    py = parent.winfo_y()
    pw = parent.winfo_width()
    ph = parent.winfo_height()

    x = px + (pw // 2) - (w // 2)
    y = py + (ph // 2) - (h // 2)
    win.geometry(f"+{x}+{y}")

def all_done() -> bool:
    for col in clue_buttons:
        for w in col:
            if isinstance(w, tk.Button) and w["state"] != "disabled":
                return False
    return True


def load_rune_icons():
    global rune_icons, back_icon
    if rune_icons and back_icon is not None:
        return

    names = ["air", "water", "earth", "fire", "death", "blood", "chaos"]
    for n in names:
        path = os.path.join(RUNES_DIR, f"{n}.png")
        if not os.path.exists(path):
            print("Missing rune icon:", path)
            rune_icons[n] = None
            continue
        img = Image.open(path).convert("RGBA").resize(RUNE_SIZE, Image.LANCZOS)
        rune_icons[n] = ImageTk.PhotoImage(img)

    # optional "back" icon (not required)
    back_path = os.path.join(RUNES_DIR, "back.png")
    if os.path.exists(back_path):
        img = Image.open(back_path).convert("RGBA").resize(RUNE_SIZE, Image.LANCZOS)
        back_icon = ImageTk.PhotoImage(img)
    else:
        back_icon = None
def load_barrows_brothers(size=(190, 270)):
    """Load Dharok + Karil images once and cache them."""
    global barrows_dharok_img, barrows_karil_img

    if barrows_dharok_img is None and os.path.exists(BARROWS_DHAROK_PATH):
        pil = Image.open(BARROWS_DHAROK_PATH).convert("RGBA")
        pil = pil.resize(size, Image.LANCZOS)
        barrows_dharok_img = ImageTk.PhotoImage(pil)

    if barrows_karil_img is None and os.path.exists(BARROWS_KARIL_PATH):
        pil = Image.open(BARROWS_KARIL_PATH).convert("RGBA")
        pil = pil.resize(size, Image.LANCZOS)
        barrows_karil_img = ImageTk.PhotoImage(pil)

def load_barrows_chest_images():
    """Optional Barrows chest images; uses text buttons if missing."""
    global chest_closed_img, chest_open_img

    if chest_closed_img is None and os.path.exists(CHEST_CLOSED_PATH):
        pil = Image.open(CHEST_CLOSED_PATH).convert("RGBA").resize((160, 120), Image.LANCZOS)
        chest_closed_img = ImageTk.PhotoImage(pil)

    if chest_open_img is None and os.path.exists(CHEST_OPEN_PATH):
        pil = Image.open(CHEST_OPEN_PATH).convert("RGBA").resize((160, 120), Image.LANCZOS)
        chest_open_img = ImageTk.PhotoImage(pil)

# -------------------------
# MUSIC (winsound)
# -------------------------
music_muted = False

def play_music_random():
    global current_song_path

    tracks = glob.glob(os.path.join(MUSIC_DIR, "*.wav"))
    if not tracks:
        print("NO MUSIC FILES FOUND IN:", MUSIC_DIR)
        return

    current_song_path = random.choice(tracks)
    print("Playing:", current_song_path)

    winsound.PlaySound(
        current_song_path,
        winsound.SND_FILENAME | winsound.SND_LOOP | winsound.SND_ASYNC | winsound.SND_NODEFAULT
    )

def resume_music():
    # winsound can't truly resume — it restarts the track
    if music_muted:
        return
    play_music_random()
    if not current_song_path or not os.path.exists(current_song_path):
        play_music_random()
        return

    winsound.PlaySound(
        current_song_path,
        winsound.SND_FILENAME | winsound.SND_LOOP | winsound.SND_ASYNC | winsound.SND_NODEFAULT
    )

def stop_music():
    winsound.PlaySound(None, winsound.SND_PURGE)

def toggle_mute():
    global music_muted
    if music_muted:
        music_muted = False
        play_music_random()
        mute_btn.config(text="🔊 Mute")
    else:
        music_muted = True
        stop_music()
        mute_btn.config(text="🔇 Unmute")

# -------------------------
# SFX (winsound)
# -------------------------
# -------------------------
# GAIN SFX
# -------------------------
GAIN_SFX = "money.wav"

def play_sfx(filename, restart_music=True, resume_delay_ms=4200):
    global sfx_resume_job

    if not filename:
        return

    path = os.path.join(MUSIC_DIR, "SFX", filename)
    if not os.path.exists(path):
        print("Missing SFX:", path)
        return

    print("play_sfx():", filename, "restart_music=", restart_music, "delay=", resume_delay_ms)

    winsound.PlaySound(
        path,
        winsound.SND_FILENAME |
        winsound.SND_ASYNC |
        winsound.SND_NODEFAULT
    )

    # Cancel any previously scheduled resume to avoid weird overlaps
    if sfx_resume_job is not None:
        try:
            window.after_cancel(sfx_resume_job)
        except Exception:
            pass
        sfx_resume_job = None

    # Schedule resume
    if restart_music and not music_muted:
        sfx_resume_job = window.after(resume_delay_ms, resume_music)

def play_gain_sfx():
    # money.wav should NOT interrupt background music
    play_sfx(GAIN_SFX, restart_music=True, resume_delay_ms=4000)


# -------------------------
# COIN POPUP (gain/loss)
# -------------------------
def load_coin_image():
    global coin_img
    if coin_img is not None:
        return
    if not os.path.exists(COINS_PATH):
        print("Missing coins.png:", COINS_PATH)
        return

    pil = Image.open(COINS_PATH).convert("RGBA")
    pil = pil.resize((28, 28), Image.LANCZOS)
    coin_img = ImageTk.PhotoImage(pil)

def show_coin_delta(player_idx: int, amount: int, is_gain: bool):
    load_coin_image()
    if coin_img is None:
        return
    if player_idx >= len(player_cards) or player_cards[player_idx] is None:
        return

    card = player_cards[player_idx]
    window.update_idletasks()

    x = card.winfo_rootx() + (card.winfo_width() // 2)
    y = card.winfo_rooty() - 6

    fg = C_GREEN if is_gain else C_RED
    sign = "+" if is_gain else "-"

    tip = tk.Toplevel(window)
    tip.overrideredirect(True)
    tip.attributes("-topmost", True)
    tip.configure(bg=C_BG)

    wrap = tk.Frame(tip, bg=C_BG)
    wrap.pack(padx=2, pady=2)

    tk.Label(wrap, image=coin_img, bg=C_BG).pack(side="left", padx=(0, 6))
    tk.Label(
        wrap,
        text=f"{sign}{abs(amount):,} gp",
        font=FONT_UI_B,
        fg=fg,
        bg=C_BG
    ).pack(side="left")

    tip.update_idletasks()
    tip.geometry(f"+{x - (tip.winfo_width() // 2)}+{y - tip.winfo_height()}")

    steps = 28
    duration_ms = 2000
    dy = 24
    start_y = y - tip.winfo_height()

    def step(i=0):
        if i >= steps:
            tip.destroy()
            return
        new_y = start_y - int(dy * (i / steps))
        tip.geometry(f"+{x - (tip.winfo_width() // 2)}+{new_y}")
        window.after(duration_ms // steps, lambda: step(i + 1))

    step()

# -------------------------
# SCOREBOARD UI
# -------------------------
def rebuild_scoreboard():
    global player_cards

    for w in player_bar.winfo_children():
        w.destroy()

    player_cards = [None] * len(players)

    if not players:
        tk.Label(
            player_bar,
            text="No players yet.   Game → Setup Players",
            font=FONT_UI_B,
            fg=C_TEXT_LIGHT,
            bg=C_PANEL
        ).grid(row=0, column=0, padx=10, pady=6)
        player_bar.grid_columnconfigure(0, weight=1)
        return

    for i, name in enumerate(players):
        is_turn = (i == selected_player.get())

        card = tk.Frame(
            player_bar,
            bg=C_PARCH2 if is_turn else C_PANEL,
            bd=2,
            relief="groove",
            highlightbackground=C_BORDER,
            highlightthickness=2
        )
        card.grid(row=0, column=i, padx=10, pady=4, sticky="n")
        player_cards[i] = card

        tk.Label(
            card,
            text=("▶ " + name) if is_turn else name,
            font=FONT_UI_B,
            fg=C_TEXT_DARK if is_turn else C_TEXT_LIGHT,
            bg=C_PARCH2 if is_turn else C_PANEL
        ).pack(padx=12, pady=(8, 2))

        if scores[i] > 0:
            score_color = C_GREEN
        elif scores[i] < 0:
            score_color = C_RED
        else:
            score_color = C_GOLD

        tk.Label(
            card,
            text=f"{scores[i]:,} gp",
            font=FONT_HEAD,
            fg=score_color,
            bg=C_PARCH2 if is_turn else C_PANEL
        ).pack(padx=12, pady=(0, 8))

        player_bar.grid_columnconfigure(i, weight=1)

def update_scoreboard():
    rebuild_scoreboard()

# -------------------------
# PLAYER SETUP
# -------------------------
def open_player_setup():
    setup = tk.Toplevel(window)
    setup.title("Player Setup")
    setup.geometry("480x560")
    setup.minsize(480, 560)
    setup.configure(bg=C_BG)
    setup.grab_set()
    center_window(setup, window)

    card = tk.Frame(setup, bg=C_PANEL, bd=2, relief="groove",
                    highlightbackground=C_BORDER, highlightthickness=2)
    card.pack(fill="both", expand=True, padx=12, pady=12)

    tk.Label(card, text="Party Setup", font=FONT_HEAD, fg=C_GOLD, bg=C_PANEL).pack(pady=(10, 4))
    tk.Label(card, text="How many players? (1–8)", font=FONT_UI, fg=C_TEXT_LIGHT, bg=C_PANEL).pack(pady=(6, 4))

    num_var = tk.StringVar(value="2")
    num_entry = tk.Entry(
        card, textvariable=num_var, font=FONT_UI_B, justify="center",
        bg=C_PARCH, fg=C_TEXT_DARK, insertbackground=C_TEXT_DARK,
        relief="solid", bd=1
    )
    num_entry.pack()

    names_frame = tk.Frame(card, bg=C_PANEL)
    names_frame.pack(pady=12, fill="both", expand=True)
    name_entries = []

    btn_row = tk.Frame(card, bg=C_PANEL)
    btn_row.pack(pady=(4, 14))

    def render_name_inputs():
        for w in names_frame.winfo_children():
            w.destroy()
        name_entries.clear()

        try:
            n = int(num_var.get())
            if n < 1 or n > 8:
                raise ValueError
        except ValueError:
            tk.Label(names_frame, text="Enter a valid number 1–8.", fg=C_RED, bg=C_PANEL, font=FONT_UI_B).pack(pady=10)
            return

        new_height = 360 + (n * 34)
        setup.geometry(f"480x{new_height}")

        tk.Label(names_frame, text="Enter player names:", font=FONT_UI_B, fg=C_TEXT_LIGHT, bg=C_PANEL).pack(pady=(0, 10))

        for i in range(n):
            row = tk.Frame(names_frame, bg=C_PANEL)
            row.pack(pady=4, padx=10, fill="x")

            tk.Label(
                row,
                text=f"Player {i+1}:",
                width=10,
                anchor="w",
                font=FONT_SMALL,
                fg=C_TEXT_LIGHT,
                bg=C_PANEL
            ).pack(side="left")

            e = tk.Entry(
                row,
                font=FONT_UI,
                bg=C_PARCH,
                fg=C_TEXT_DARK,
                insertbackground=C_TEXT_DARK,
                relief="solid",
                bd=1
            )
            e.pack(side="left", fill="x", expand=True)
            e.insert(0, f"Player{i+1}")
            name_entries.append(e)

    def start_game():
        try:
            n = int(num_var.get())
            if n < 1 or n > 8:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid", "Number of players must be 1–8.")
            return

        new_players = []
        for e in name_entries:
            name = e.get().strip()
            if not name:
                messagebox.showerror("Missing name", "All players must have a name.")
                return
            new_players.append(name)

        players.clear()
        players.extend(new_players)

        scores.clear()
        scores.extend([0] * len(players))

        global game_over_shown
        game_over_shown = False

        selected_player.set(0)
        update_scoreboard()
        setup.destroy()

    def make_btn(parent, text, cmd):
        return tk.Button(
            parent,
            text=text,
            command=cmd,
            font=FONT_UI_B,
            bg=C_PARCH2,
            fg=C_TEXT_DARK,
            activebackground=C_GOLD,
            activeforeground=C_TEXT_DARK,
            relief="raised",
            bd=2,
            padx=14,
            pady=6,
            highlightbackground=C_BORDER,
            highlightthickness=1
        )

    make_btn(btn_row, "Update", render_name_inputs).pack(side="left", padx=8)
    make_btn(btn_row, "Start Game", start_game).pack(side="left", padx=8)

    render_name_inputs()
    setup.bind("<Return>", lambda e: start_game())
    num_entry.focus_set()

# -------------------------
# REWARDS / PUNISHMENTS / POPUPS / ANIMS
# -------------------------
def apply_reward(player_idx: int, value: int) -> str:
    effects = [value, value // 2, 200]
    amt = random.choice(effects)
    scores[player_idx] += amt
    update_scoreboard()
    show_coin_delta(player_idx, amt, True)
    play_gain_sfx()
    return f"Bonus loot! +{amt:,} gp"

class GifPlayer:
    def __init__(self, label: tk.Label):
        self.label = label
        self.frames = []
        self.delay = 60
        self.idx = 0
        self.job = None
        self.clear_job = None

    def stop(self):
        if self.job:
            self.label.after_cancel(self.job)
            self.job = None
        if self.clear_job:
            self.label.after_cancel(self.clear_job)
            self.clear_job = None
        self.frames = []
        self.idx = 0
        self.label.config(image="")
        self.label.image = None

    def play(self, gif_path: str, duration_ms: int = 7000, size=(220, 220)):
        self.stop()

        if not os.path.exists(gif_path):
            print("Missing anim:", gif_path)
            return

        pil = Image.open(gif_path)

        self.frames = []
        try:
            while True:
                frame = pil.copy().convert("RGBA")
                frame = frame.resize(size, Image.LANCZOS)
                self.frames.append(ImageTk.PhotoImage(frame))
                pil.seek(pil.tell() + 1)
        except EOFError:
            pass

        if not self.frames:
            return

        self.delay = max(60, int(pil.info.get("duration", 60)))
        self.idx = 0

        def step():
            self.label.config(image=self.frames[self.idx])
            self.label.image = self.frames[self.idx]
            self.idx = (self.idx + 1) % len(self.frames)
            self.job = self.label.after(self.delay, step)

        step()
        self.clear_job = self.label.after(int(duration_ms), self.stop)

def show_event_popup(title: str, text: str, image_filename=None, auto_close_ms: int = 1600):
    pop = tk.Toplevel(window)
    pop.title(title)
    pop.configure(bg=C_BG)
    pop.resizable(False, False)
    pop.transient(window)
    pop.grab_set()
    pop.lift()
    pop.focus_force()

    card = tk.Frame(pop, bg=C_PARCH, bd=2, relief="groove",
                    highlightbackground=C_BORDER, highlightthickness=3)
    card.pack(padx=14, pady=14, fill="both", expand=True)

    tk.Label(card, text=title, font=FONT_HEAD, fg=C_TEXT_DARK, bg=C_PARCH).pack(pady=(10, 6))
    tk.Label(card, text=text, font=FONT_UI_B, fg=C_TEXT_DARK, bg=C_PARCH,
             wraplength=420, justify="center").pack(padx=14, pady=(0, 10))

    if image_filename:
        path = os.path.join(ASSETS_DIR, image_filename)
        if os.path.exists(path):
            pil = Image.open(path).convert("RGBA").resize((300, 180), Image.LANCZOS)
            img = ImageTk.PhotoImage(pil)
            lbl = tk.Label(card, image=img, bg=C_PARCH)
            lbl.image = img
            lbl.pack(pady=(0, 10))

    center_window(pop, window)
    pop.after(auto_close_ms, pop.destroy)
def load_cape_icons(size=(44, 54)):
    """Load placement cape icons once (1st..5th). Missing files are allowed."""
    global cape_imgs
    if cape_imgs:
        return

    paths = [
        INFERNAL_CAPE_PATH,  # 1st
        FIRE_CAPE_PATH,      # 2nd
        OBBY_CAPE_PATH,      # 3rd
        TEAM_CAPE_PATH,      # 4th
        RED_CAPE_PATH,       # 5th
    ]

    out = []
    for p in paths:
        if os.path.exists(p):
            pil = Image.open(p).convert("RGBA").resize(size, Image.LANCZOS)
            out.append(ImageTk.PhotoImage(pil))
        else:
            out.append(None)

    cape_imgs = out


def show_final_scores_popup():
    """OSRS-styled final standings with cape icons for placements."""
    global game_over_shown
    if game_over_shown:
        return
    game_over_shown = True

    if not players:
        messagebox.showinfo("Game Over", "No players.")
        return

    load_cape_icons()

    # Sort standings: highest gp first. Tie-breaker: name (stable)
    standings = list(zip(players, scores))
    standings.sort(key=lambda x: (x[1], x[0]), reverse=True)

    pop = tk.Toplevel(window)
    pop.title("Game Over")
    pop.configure(bg=C_BG)
    pop.resizable(False, False)
    pop.transient(window)
    pop.grab_set()
    pop.lift()
    pop.focus_force()

    card = tk.Frame(
        pop, bg=C_PARCH, bd=2, relief="groove",
        highlightbackground=C_BORDER, highlightthickness=3
    )
    card.pack(padx=16, pady=16)

    tk.Label(
        card,
        text="GAME OVER",
        font=("Georgia", 18, "bold"),
        fg=C_TEXT_DARK,
        bg=C_PARCH
    ).pack(pady=(10, 2))

    tk.Label(
        card,
        text="Final Standings",
        font=FONT_UI_B,
        fg=C_TEXT_DARK,
        bg=C_PARCH
    ).pack(pady=(0, 12))

    table = tk.Frame(card, bg=C_PARCH)
    table.pack(padx=10, pady=(0, 12))

    def score_color(v):
        if v > 0:
            return C_GREEN
        if v < 0:
            return C_RED
        return C_GOLD

    # show up to 5 placements with capes, then the rest without capes
    for i, (name, sc) in enumerate(standings):
        row = tk.Frame(table, bg=C_PARCH)
        row.pack(fill="x", pady=4)

        place = i + 1

        # Cape / place icon
        icon = None
        if 1 <= place <= 5:
            icon = cape_imgs[place - 1]

        if icon is not None:
            lbl_icon = tk.Label(row, image=icon, bg=C_PARCH)
            lbl_icon.image = icon
            lbl_icon.pack(side="left", padx=(0, 10))
        else:
            # fallback if missing image or beyond 5
            tk.Label(
                row,
                text=f"{place}.",
                font=FONT_UI_B,
                fg=C_TEXT_DARK,
                bg=C_PARCH,
                width=3,
                anchor="w"
            ).pack(side="left", padx=(0, 10))

        tk.Label(
            row,
            text=name,
            font=FONT_UI_B,
            fg=C_TEXT_DARK,
            bg=C_PARCH,
            width=18,
            anchor="w"
        ).pack(side="left")

        tk.Label(
            row,
            text=f"{sc:,} gp",
            font=FONT_UI_B,
            fg=score_color(sc),
            bg=C_PARCH,
            width=12,
            anchor="e"
        ).pack(side="right")

    btn_row = tk.Frame(card, bg=C_PARCH)
    btn_row.pack(pady=(4, 2))

    tk.Button(
        btn_row,
        text="OK",
        font=FONT_UI_B,
        bg=C_PARCH2,
        fg=C_TEXT_DARK,
        activebackground=C_GOLD,
        activeforeground=C_TEXT_DARK,
        relief="raised",
        bd=2,
        padx=18,
        pady=6,
        command=pop.destroy
    ).pack()

    center_window(pop, window)

def play_punishment_anim(event: dict):
    duration = int(event.get("gif_duration_ms", 7000))
    size = tuple(event.get("gif_size", [220, 220]))

    left_gif = event.get("gif_left")
    right_gif = event.get("gif_right")

    if left_gif:
        left_path = os.path.join(ANIM_DIR, left_gif)
        left_anim.play(left_path, duration_ms=duration, size=size)

    if right_gif:
        right_path = os.path.join(ANIM_DIR, right_gif)
        right_anim.play(right_path, duration_ms=duration, size=size)

def apply_punishment(player_idx: int, value: int) -> str:
    if not PUNISHMENTS:
        return ""

    event = random.choice(PUNISHMENTS)

    # optional: gifs + sfx
    play_punishment_anim(event)
    play_sfx(event.get("sound"))

    rule = event.get("amounts", "default")
    if rule == "half":
        amt = max(50, value // 2)
    elif rule == "default":
        amt = random.choice([value, value // 2, 200])
    elif isinstance(rule, list):
        amt = random.choice(rule)
    else:
        amt = random.choice([value, value // 2, 200])

    scores[player_idx] -= amt
    update_scoreboard()
    show_coin_delta(player_idx, amt, False)

    show_event_popup(
        title=event.get("title", "Misfortune!"),
        text=event.get("text", f"You lost {amt:,} gp."),
        image_filename=event.get("image"),
        auto_close_ms=5600
    )

    return f"{event.get('title', 'Misfortune!')} -{amt:,} gp"

# -------------------------
# MINIGAME 1: RUNE RECALL (Memory)
# -------------------------
def run_minigame(cat_idx, clue_idx):
    load_rune_icons()

    if not players:
        messagebox.showinfo("No players", "Set up players first.")
        return

    p = selected_player.get()
    value = selected_clues[cat_idx][clue_idx]["value"]

    # Difficulty rules based on tile value
    if value <= 200:
        seq_len = 3
        time_limit_ms = 5500
    elif value <= 400:
        seq_len = 5
        time_limit_ms = 5000
    else:
        seq_len = 6
        time_limit_ms = 6800

    TICK_MS = 100
    SHOW_MS = 3700

    win_amt = value
    lose_amt = max(50, value // 2)

    state = {"remaining_ms": time_limit_ms, "timer_job": None}

    RUNES = ["air", "water", "earth", "fire", "death", "blood", "chaos"]
    DISPLAY = {r: r.title() for r in RUNES}

    sequence = [random.choice(RUNES) for _ in range(seq_len)]

    mg = tk.Toplevel(window)
    mg.title("Mini-game: Rune Recall")
    mg.configure(bg=C_BG)
    mg.resizable(False, False)
    mg.transient(window)
    mg.grab_set()
    mg.lift()
    mg.focus_force()

    card = tk.Frame(mg, bg=C_PARCH, bd=2, relief="groove",
                    highlightbackground=C_BORDER, highlightthickness=3)
    card.pack(padx=14, pady=14)

    tk.Label(card, text="RUNE RECALL", font=FONT_HEAD, bg=C_PARCH, fg=C_TEXT_DARK)\
        .pack(pady=(12, 6))

    tk.Label(card, text=f"{players[p]} — memorize the runes, then click them in order!",
             font=FONT_UI_B, bg=C_PARCH, fg=C_TEXT_DARK)\
        .pack(pady=(0, 10))

    # Timer + status
    top_row = tk.Frame(card, bg=C_PARCH)
    top_row.pack(pady=(0, 10))

    time_var = tk.StringVar(value=f"Time: {time_limit_ms/1000:.1f}s")
    status_var = tk.StringVar(value="Memorize...")

    tk.Label(top_row, textvariable=time_var, font=FONT_UI_B, bg=C_PARCH, fg=C_TEXT_DARK)\
        .pack(side="left", padx=16)
    tk.Label(top_row, textvariable=status_var, font=FONT_UI_B, bg=C_PARCH, fg=C_TEXT_DARK)\
        .pack(side="right", padx=16)

    seq_label = tk.Label(
        card,
        text="  •  ".join(DISPLAY[r] for r in sequence),
        font=("Georgia", 16, "bold"),
        bg=C_PARCH,
        fg=C_TEXT_DARK,
        wraplength=520,
        justify="center"
    )
    seq_label.pack(padx=18, pady=(6, 12))

    grid = tk.Frame(card, bg=C_PARCH)
    grid.pack(padx=14, pady=(6, 14))

    result = tk.Label(card, text="", font=FONT_UI_B, bg=C_PARCH, fg=C_TEXT_DARK)
    result.pack(pady=(0, 12))

    idx = 0
    ended = False

    def finish(win: bool, reason: str = ""):
        nonlocal ended
        if ended:
            return
        ended = True

        if state["timer_job"] is not None:
            try:
                mg.after_cancel(state["timer_job"])
            except Exception:
                pass
            state["timer_job"] = None

        if win:
            scores[p] += win_amt
            update_scoreboard()
            show_coin_delta(p, win_amt, True)
            result.config(fg=C_GREEN, text=f"SUCCESS! +{win_amt:,} gp")
        else:
            scores[p] -= lose_amt
            update_scoreboard()
            show_coin_delta(p, lose_amt, False)
            result.config(
                fg=C_RED,
                text=f"FAILED! -{lose_amt:,} gp" + (f"  ({reason})" if reason else "")
            )

        # consume the tile + advance
        mark_tile_used(cat_idx, clue_idx)

        selected_player.set((selected_player.get() + 1) % len(players))
        update_scoreboard()

        if all_done():
            final_lines = [f"{players[i]}: {scores[i]:,} gp" for i in range(len(players))]
            window.after(900, show_final_scores_popup)

        mg.after(1600, mg.destroy)

    def on_rune_click(rune_name: str):
        nonlocal idx
        if ended:
            return

        expected = sequence[idx]
        if rune_name != expected:
            finish(False, f"expected {DISPLAY[expected]}")
            return

        idx += 1
        status_var.set(f"Correct! ({idx}/{seq_len})")

        if idx >= seq_len:
            finish(True)

    buttons = []
    for i, rune in enumerate(RUNES):
        icon = rune_icons.get(rune)

        b = tk.Button(
            grid,
            image=icon if icon else "",
            text=DISPLAY[rune] if not icon else "",
            font=FONT_UI_B,
            width=RUNE_SIZE[0],
            height=RUNE_SIZE[1],
            bg=C_PARCH2,
            fg=C_TEXT_DARK,
            activebackground=C_GOLD,
            activeforeground=C_TEXT_DARK,
            relief="raised",
            bd=2,
            compound="center",
            command=lambda r=rune: on_rune_click(r)
        )
        b.grid(row=i // 3, column=i % 3, padx=8, pady=8)
        b.config(state="disabled")
        b.image = icon
        buttons.append(b)

    def tick_timer():
        if ended:
            return

        state["remaining_ms"] -= TICK_MS
        if state["remaining_ms"] <= 0:
            time_var.set("Time: 0.0s")
            finish(False, "time")
            return

        time_var.set(f"Time: {state['remaining_ms']/1000:.1f}s")
        state["timer_job"] = mg.after(TICK_MS, tick_timer)

    def start_recall_phase():
        seq_label.config(text="  •  ".join(["???"] * seq_len))
        status_var.set("RECALL!")
        for b in buttons:
            b.config(state="normal")
        tick_timer()

    mg.update_idletasks()
    x = window.winfo_x() + (window.winfo_width() // 2) - (mg.winfo_width() // 2)
    y = window.winfo_y() + 120
    mg.geometry(f"+{x}+{y}")

    mg.after(SHOW_MS, start_recall_phase)

# -------------------------
# MINIGAME 2: BARROWS CHEST (Gamble)
# -------------------------
def run_barrows_gamble(cat_idx, clue_idx):
    load_barrows_chest_images()
    load_barrows_brothers()

    if not players:
        messagebox.showinfo("No players", "Set up players first.")
        return

    p = selected_player.get()
    V = selected_clues[cat_idx][clue_idx]["value"]

    outcomes = [
        {"mult": +3, "label": "💎 BIG WIN!",  "color": C_GREEN, "title": "DOUBLE CHEST!",
         "text": "You got a Karil top + Guthan helm!", "sfx": "coins.wav"},
        {"mult": +1, "label": "💰 WIN!",      "color": C_GREEN, "title": "Karil's Coif!",
         "text": "Eh, better than nothing", "sfx": "coins.wav"},
        {"mult": -1, "label": "💀 LOSS!",     "color": C_RED,   "title": "Barrows Curse!",
         "text": "A cold dread settles over you...", "sfx": "ghost.wav"},
        {"mult": -2, "label": "☠️ BIG LOSS!", "color": C_RED,   "title": "Dharok is pissed!",
         "text": "He axes you a 79!", "sfx": "ghost.wav"},
    ]
    random.shuffle(outcomes)  # pure randomness each time

    mg = tk.Toplevel(window)
    mg.title("Mini-game: Barrows Chest")
    mg.configure(bg=C_BG)
    mg.resizable(False, False)
    mg.transient(window)
    mg.grab_set()
    mg.lift()
    mg.focus_force()

    outer = tk.Frame(mg, bg=C_BG)
    outer.pack(padx=14, pady=14)

    # Left brother (Dharok)
    left_lbl = tk.Label(outer, bg=C_BG)
    left_lbl.grid(row=0, column=0, padx=(0, 14), sticky="n")

    # Center card
    card = tk.Frame(
    outer,
    bg=C_PARCH,
    bd=2,
    relief="groove",
    highlightbackground=C_BORDER,
    highlightthickness=3
    )
    card.grid(row=0, column=1, sticky="n")

    # Right brother (Karil)
    right_lbl = tk.Label(outer, bg=C_BG)
    right_lbl.grid(row=0, column=2, padx=(14, 0), sticky="n")

    # Assign images
    if barrows_dharok_img:
        left_lbl.config(image=barrows_dharok_img)
        left_lbl.image = barrows_dharok_img

    if barrows_karil_img:
        right_lbl.config(image=barrows_karil_img)
        right_lbl.image = barrows_karil_img


    tk.Label(card, text="BARROWS CHEST", font=FONT_HEAD, bg=C_PARCH, fg=C_TEXT_DARK)\
        .pack(pady=(12, 6))

    tk.Label(card, text="You descend into the crypt… choose ONE chest.",
             font=FONT_UI_B, bg=C_PARCH, fg=C_TEXT_DARK)\
        .pack(pady=(0, 10))

    tk.Label(card, text=f"{board[cat_idx]['category']} • {V} gp",
             font=FONT_UI_B, fg=C_TEXT_DARK, bg=C_PARCH, justify="center")\
        .pack(pady=(0, 10), padx=18, fill="x")

    result_lbl = tk.Label(card, text="", font=FONT_UI_B, bg=C_PARCH, fg=C_TEXT_DARK)
    result_lbl.pack(pady=(0, 10))

    grid = tk.Frame(card, bg=C_PARCH)
    grid.pack(padx=12, pady=(6, 12))

    opened = {"done": False}
    buttons = []

    def finish_and_advance():
        mark_tile_used(cat_idx, clue_idx)
        selected_player.set((selected_player.get() + 1) % len(players))
        update_scoreboard()

        if all_done():
           window.after(900, show_final_scores_popup)

        mg.after(1400, mg.destroy)

    def open_chest(ix: int):
        if opened["done"]:
            return
        opened["done"] = True

        for b in buttons:
            b.config(state="disabled")

        play_sfx("chest_open.wav")

        picked = outcomes[ix]
        delta = picked["mult"] * V

        if chest_open_img is not None:
            buttons[ix].config(image=chest_open_img, text="")
            buttons[ix].image = chest_open_img
        else:
            buttons[ix].config(text="OPEN")

        if delta >= 0:
            scores[p] += delta
            update_scoreboard()
            show_coin_delta(p, delta, True)
        else:
            scores[p] += delta
            update_scoreboard()
            show_coin_delta(p, abs(delta), False)

        play_sfx(picked.get("sfx"))

        result_lbl.config(fg=picked["color"], text=f"{picked['label']}  ({delta:+,} gp)")

        show_event_popup(
            title=picked["title"],
            text=f"{picked['text']}\n\nResult: {delta:+,} gp",
            auto_close_ms=3600
        )

        finish_and_advance()

    for i in range(4):
        if chest_closed_img is not None:
            b = tk.Button(
                grid,
                image=chest_closed_img,
                bg=C_PARCH2,
                activebackground=C_GOLD,
                relief="raised",
                bd=2,
                command=lambda ix=i: open_chest(ix)
            )
            b.image = chest_closed_img
        else:
            b = tk.Button(
                grid,
                text="CHEST",
                font=FONT_UI_B,
                width=12,
                height=4,
                bg=C_PARCH2,
                fg=C_TEXT_DARK,
                activebackground=C_GOLD,
                relief="raised",
                bd=2,
                command=lambda ix=i: open_chest(ix)
            )
        b.grid(row=i // 2, column=i % 2, padx=14, pady=14)
        buttons.append(b)

    mg.update_idletasks()
    x = window.winfo_x() + (window.winfo_width() // 2) - (mg.winfo_width() // 2)
    y = window.winfo_y() + 120
    mg.geometry(f"+{x}+{y}")

# -------------------------
# MINIGAME DISPATCHER
# -------------------------
def run_random_minigame(cat_idx, clue_idx):
    MINIGAMES = [
        ("Rune Recall", run_minigame),
        ("Barrows Chest", run_barrows_gamble),
    ]
    name, fn = random.choice(MINIGAMES)
    print("Mini-game selected:", name)
    fn(cat_idx, clue_idx)

# -------------------------
# CLUE WINDOW
# -------------------------
def open_clue(cat_idx, clue_idx):
    clue = selected_clues[cat_idx][clue_idx]
    value = clue["value"]

    # ✅ Every tile click rolls a mini-game chance
    if random.random() < MINIGAME_CHANCE:
        run_random_minigame(cat_idx, clue_idx)
        return

    if not players:
        messagebox.showinfo("No players", "Set up players first.")
        return

    p = selected_player.get()

    win = tk.Toplevel(window)
    win.title("Trivia")
    win.configure(bg=C_BG)
    win.geometry("650x340")
    win.transient(window)
    win.lift()
    win.focus_force()
    win.grab_set()

    card = tk.Frame(
        win, bg=C_PARCH, bd=2, relief="groove",
        highlightbackground=C_BORDER, highlightthickness=3
    )
    card.pack(padx=14, pady=14, fill="both", expand=True)

    # --- MAIN QUESTION ---
    question_text = (
        clue.get("question")
        or clue.get("prompt")
        or clue.get("text")
        or clue.get("clue")
        or ""
    )
    if not question_text:
        question_text = "(Missing question text)"

    clue_label = tk.Label(
        card,
        text=question_text,
        font=("Georgia", 18, "bold"),
        wraplength=600,
        fg=C_TEXT_DARK,
        bg=C_PARCH,
        justify="center"
    )
    clue_label.pack(pady=(16, 8), padx=18, fill="x")

    # centered info row
    tk.Label(
        card,
        text=f"{board[cat_idx]['category']} • {value} gp",
        font=FONT_UI_B,
        fg=C_TEXT_DARK,
        bg=C_PARCH,
        justify="center"
    ).pack(pady=(0, 10), padx=18, fill="x")

    result_label = tk.Label(
        card,
        text="",
        font=FONT_UI_B,
        fg=C_TEXT_DARK,
        bg=C_PARCH,
        justify="center"
    )
    result_label.pack(pady=(0, 8), fill="x")

    entry = tk.Entry(
        card,
        font=FONT_UI_B,
        justify="center",
        bg="#fff6dc",
        fg=C_TEXT_DARK,
        insertbackground=C_TEXT_DARK,
        relief="solid",
        bd=1
    )
    entry.pack(pady=6, ipadx=8, ipady=6)

    def submit():
        user_answer = normalize(entry.get())
        correct_answer = normalize(clue.get("answer", ""))

        if user_answer == "":
            messagebox.showinfo("Answer needed", "Type an answer.")
            return

        if user_answer == correct_answer:
            scores[p] += value
            update_scoreboard()
            show_coin_delta(p, value, True)
            play_gain_sfx()
            bonus_msg = ""
            if clue.get("bonus_eligible"):
                bonus_msg = "\n" + apply_reward(p, value)

            result_label.config(fg=C_GREEN, text=f"Correct! +{value:,} gp{bonus_msg}")
            close_ms = 2500
        else:
            scores[p] -= value
            update_scoreboard()
            show_coin_delta(p, value, False)

            punish_msg = ""
            if clue.get("punish_eligible"):
                punish_msg = "\n" + apply_punishment(p, value)

            result_label.config(
                fg=C_RED,
                text=f"Wrong! -{value:,} gp\nCorrect: {clue.get('answer','')}{punish_msg}"
            )
            close_ms = 4900

        mark_tile_used(cat_idx, clue_idx)
        selected_player.set((selected_player.get() + 1) % len(players))
        update_scoreboard()

        if all_done():
            window.after(900, show_final_scores_popup)

        win.after(close_ms, win.destroy)

    entry.focus_set()
    entry.bind("<Return>", lambda e: (submit(), "break"))

    tk.Button(
        card,
        text="Submit",
        font=FONT_UI_B,
        bg=C_PARCH2, fg=C_TEXT_DARK,
        activebackground=C_GOLD, activeforeground=C_TEXT_DARK,
        relief="raised", bd=2, padx=14, pady=6,
        highlightbackground=C_BORDER, highlightthickness=1,
        command=submit
    ).pack(pady=12)

    win.update_idletasks()
    x = window.winfo_x() + (window.winfo_width() // 2) - (win.winfo_width() // 2)
    y = window.winfo_y() + 120
    win.geometry(f"+{x}+{y}")
    win.resizable(False, False)

# -------------------------
# MAIN UI
# -------------------------
window = tk.Tk()
window.title("OSRS TRIVIA")
window.geometry("1500x800")
window.resizable(True, True)
window.configure(bg=C_BG)

# Start music
window.after(0, play_music_random)

# Menu
menu = tk.Menu(window)
game_menu = tk.Menu(menu, tearoff=0)
game_menu.add_command(label="Setup Players", command=open_player_setup)
game_menu.add_separator()
game_menu.add_command(label="Next Track", command=play_music_random)
game_menu.add_command(label="Stop Music", command=stop_music)
game_menu.add_separator()
game_menu.add_command(label="Quit", command=lambda: (stop_music(), window.destroy()))
menu.add_cascade(label="Game", menu=game_menu)
window.config(menu=menu)

# Header / logo / anims
logo_path = os.path.join(ASSETS_DIR, "gielinor_gauntlet.png")
logo_img = Image.open(logo_path).convert("RGBA").resize((420, 190), Image.LANCZOS)
gielinor_logo = ImageTk.PhotoImage(logo_img)

top_frame = tk.Frame(window, bg=C_BG)
top_frame.pack(side="top", fill="x", padx=12, pady=(2, 0))

header_frame = tk.Frame(top_frame, bg=C_BG)
header_frame.pack(fill="x", pady=(0, 0))

for col in range(5):
    header_frame.grid_columnconfigure(col, weight=1)

exit_btn = tk.Button(
    header_frame,
    text="❌ Exit",
    command=window.destroy,
    font=FONT_UI_B,
    bg=C_PARCH2,
    fg=C_TEXT_DARK,
    activebackground="#b33a3a",
    activeforeground="white",
    relief="raised",
    bd=2
)
exit_btn.grid(row=0, column=0, sticky="nw", padx=10, pady=6)

left_anim_label = tk.Label(header_frame, bg=C_BG)
left_anim_label.grid(row=0, column=1, sticky="e", padx=10, pady=6)

logo_label = tk.Label(header_frame, image=gielinor_logo, bg=C_BG)
logo_label.grid(row=0, column=2, pady=0)

right_anim_label = tk.Label(header_frame, bg=C_BG)
right_anim_label.grid(row=0, column=3, sticky="w", padx=10, pady=6)

left_anim = GifPlayer(left_anim_label)
right_anim = GifPlayer(right_anim_label)

mute_btn = tk.Button(
    header_frame,
    text="🔊 Mute",
    command=toggle_mute,
    font=FONT_UI_B,
    bg=C_PARCH2,
    fg=C_TEXT_DARK,
    activebackground=C_GOLD,
    activeforeground=C_TEXT_DARK,
    relief="raised",
    bd=2
)
mute_btn.grid(row=0, column=4, sticky="ne", padx=10, pady=6)

# Scoreboard
scoreboard_frame = tk.Frame(top_frame, bg=C_PANEL, bd=2, relief="groove",
                            highlightbackground=C_BORDER, highlightthickness=2)
scoreboard_frame.pack(anchor="w", fill="x")

score_left = tk.Frame(scoreboard_frame, bg=C_PANEL)
score_left.pack(side="left", padx=14, pady=8)

tk.Label(
    score_left,
    text="Adventurers:",
    font=FONT_HEAD,
    fg=C_GOLD,
    bg=C_PANEL
).pack(anchor="w")

player_bar = tk.Frame(scoreboard_frame, bg=C_PANEL)
player_bar.pack(side="left", fill="both", expand=True, padx=10, pady=8)

# Board container
board_outer = tk.Frame(window, bg=C_BG)
board_outer.pack(side="top", fill="both", expand=True, padx=12, pady=(0, 12))

board_frame = tk.Frame(board_outer, bg=C_PANEL, bd=2, relief="groove",
                       highlightbackground=C_BORDER, highlightthickness=2)
board_frame.pack(fill="both", expand=True)

selected_player = tk.IntVar(master=window, value=0)

# Initial scoreboard
update_scoreboard()

# -------------------------
# BUILD BOARD
# -------------------------
selected_clues.clear()
clue_buttons.clear()

for c, cat in enumerate(board):
    lbl = tk.Label(
        board_frame,
        text=cat["category"],
        font=FONT_HEAD,
        bg=C_PARCH2,
        fg=C_TEXT_DARK,
        bd=2,
        relief="ridge",
        padx=8,
        pady=8
    )
    lbl.grid(row=0, column=c, padx=PAD_X, pady=PAD_Y, sticky="nsew")

for c, cat in enumerate(board):
    col_buttons = []
    selected_clues.append([])

    for r, val in enumerate(VALUES, start=1):
        pool = [cl for cl in cat["clues"] if cl["value"] == val]

        if not pool:
            print(f"ERROR: Missing {val} question in category '{cat['category']}'")
            chosen = {
                "value": val,
                "question": f"Missing {val} question in {cat['category']}",
                "answer": "placeholder"
            }
        else:
            chosen = dict(random.choice(pool))

        chosen["bonus_eligible"] = random.random() < BONUS_CHANCE
        chosen["punish_eligible"] = random.random() < PUNISH_CHANCE

        selected_clues[c].append(chosen)

        btn = tk.Button(
            board_frame,
            text=f"{val} gp",
            font=FONT_TILE,
            bg=C_PARCH,
            fg=C_TEXT_DARK,
            activebackground=C_GOLD,
            activeforeground=C_TEXT_DARK,
            relief="raised",
            bd=2,
            highlightbackground=C_BORDER,
            highlightthickness=1,
            command=lambda c=c, r=r-1: open_clue(c, r)
        )
        btn.grid(row=r, column=c, padx=PAD_X, pady=PAD_Y, sticky="nsew")
        col_buttons.append(btn)

    clue_buttons.append(col_buttons)

# Make the board stretch evenly across the whole window
for c in range(len(board)):
    board_frame.grid_columnconfigure(c, weight=1, uniform="board_col")

for r in range(len(VALUES) + 1):
    board_frame.grid_rowconfigure(r, weight=1, uniform="board_row")

# Prompt player setup on startup
window.after(200, open_player_setup)

window.mainloop()
