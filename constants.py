import os
from dotenv import load_dotenv
load_dotenv()

GUILD_ID = os.getenv("GUILD_ID")  # なしならグローバル同期

# 経済バランス
COOLDOWN_LUCKY_SECONDS = 10
DAILY_COOLDOWN_SECONDS = 12 * 3600

# /daily：受取回数に応じて 100M ずつ増える（1回目=100M, 2回目=200M, 3回目=300M, ...）
DAILY_BASE_INC = 100_000_000  # 100M

GIVE_MIN_AMOUNT = 100_000_000   # /give 最低送金 100M

# クイズ報酬（/math & /english）：ランダム 10M〜50M
QUIZ_REWARD_MIN = 10_000_000
QUIZ_REWARD_MAX = 50_000_000

# ティア（価格改定済）
TIERS = {
    "Mythic": {
        "cost": 2_500_000,
        "thumbnail": "https://emoji.gg/assets/emoji/3125-cube.gif",
        "color": 0xF1C40F,
        "entries": [
            ("Spioniro Golubiro", 37.0),
            ("Tigrilini Watermelini", 30.0),
            ("Zibra Zubra Zibralini", 20.0),
            ("Carrotini Brainini", 10.0),
            ("Bananito Bandito", 3.0),
        ],
    },
    "Brainrot God": {
        "cost": 15_000_000,
        "thumbnail": "https://emoji.gg/assets/emoji/6322-shine.gif",
        "color": 0xE91E63,
        "entries": [
            ("Tigroligre Frutonni", 54.0),
            ("Orcalero Orcala", 30.0),
            ("Bulbito Bandito Traktorito", 10.0),
            ("Mastodontico Telepiedone", 5.0),
            ("Pop Pop Sahur", 1.0),
        ],
    },
    "Secret": {
        "cost": 750_000_000,
        "thumbnail": "https://emoji.gg/assets/emoji/5348-mysterybox.gif",
        "color": 0x8E44AD,
        "entries": [
            ("Torrtuginni Dragonfrutini", 74.5),
            ("Pot Hotspot", 21.0),
            ("Esok Sekolah", 3.0),
            ("Spaghetti Tualetti", 1.0),
            ("La Secret Combinasion", 0.5),
        ],
    },
    "Admin": {
        "cost": 100_000_000,
        "thumbnail": "https://emoji.gg/assets/emoji/9581-admin.png",
        "color": 0x00FFFF,
        "entries": [
            ("Carloo", 28.0),
            ("Alessio", 20.0),
            ("Los Bombinitos", 15.0),
            ("Crabbo Limonetta", 15.0),
            ("Blackhole Goat", 10.0),
            ("Guerriro Digitale", 7.5),
            ("67", 3.75),
            ("La Grande Combinasion", 0.75),
        ],
    },
    "Taco": {
        "cost": 50_000_000,
        "thumbnail": "https://emoji.gg/assets/emoji/6079-taco.png",
        "color": 0xF39C12,
        "entries": [
            ("Chihuanini Taconini", 50.5),
            ("Gattito Tacoto", 35.0),
            ("Los Tipi Tacos", 10.0),
            ("Quesadilla Crocodila", 3.0),
            ("Los Nooo My Hotspotsitos", 1.0),
            ("Burrito Bandito", 0.5),
        ],
    },
    "Los": {
        "cost": 250_000_000,
        "thumbnail": "https://emoji.gg/assets/emoji/3102-loss.png",
        "color": 0x3498DB,
        "entries": [
            ("Los Bombinitos", 40.0),
            ("Los Tungtungtungcitos", 25.0),
            ("Los Orcalitos", 15.0),
            ("Los Tipi Tacos", 10.0),
            ("Los Tortus", 5.0),
            ("Los Jobcitos", 3.5),
            ("Los Combinasionas", 1.0),
            ("Los 67", 0.5),
        ],
    },
    "Los Taco": {
        "cost": 300_000_000,
        "thumbnail": "https://emoji.gg/assets/emoji/9248-los-taco.gif",
        "color": 0xE67E22,
        "entries": [
            ("Los Chihuahinis", 75.0),
            ("Los Gattitos", 15.0),
            ("Los Cucarachas", 5.0),
            ("Los Quesadillos", 4.0),
            ("Los Burritos", 1.0),
        ],
    },
    "Spooky": {
        "cost": 350_000_000,
        "thumbnail": "https://emoji.gg/assets/emoji/7815-pumpkin.gif",
        "color": 0x800080,
        "entries": [
            ("Mummy Ambalabu", 32.7),
            ("Cappucino Clownino", 32.5),
            ("Jackorilla", 19.5),
            ("Pumpkini Spyderini", 9.0),
            ("Trickolino", 3.0),
            ("Telemorte", 2.0),
            ("Los Spooky Combinasionas", 1.0),
            ("La Casa Boo", 0.3),
        ],
    },

    # ===== 新ティア =====
    "Cat": {
        "cost": 22_000_000,
        "thumbnail": "https://emoji.gg/assets/emoji/1846-cat.png",
        "color": 0xFF66CC,
        "entries": [
            ("Gattatino Nyanino", 30.0),
            ("Gattatino Neonino", 30.0),
            ("Gattito Tacoto", 25.0),
            ("Los Gattitos", 14.99),
            ("Meowl", 0.01),
        ],
    },
    "Jandel vs Sammy": {
        "cost": 50_000_000,
        "thumbnail": "https://emoji.gg/assets/emoji/1719-raccoon.png",
        "color": 0x95A5A6,
        "entries": [
            ("Raccooni Jandelini", 50.0),
            ("Sammyni Spyderini", 50.0),
        ],
    },
    "Hacker": {
        "cost": 600_000_000,
        "thumbnail": "https://emoji.gg/assets/emoji/3536-hackermanskull.png",
        "color": 0x2C3E50,
        "entries": [
            ("1x1x1x1", 99.0),
            ("Guest 666", 1.0),
        ],
    },
    "Extinct": {
        "cost": 100_000_000,
        "thumbnail": "https://emoji.gg/assets/emoji/8450-dinosaur.png",
        "color": 0x16A085,
        "entries": [
            ("Extinct Ballerina", 60.0),
            ("Extinct Tralalero", 35.0),
            ("Extinct Matteo", 4.0),
            ("La Extinct Grande", 1.0),
        ],
    },
    "Witching Hour": {
        "cost": 100_000_000,
        "thumbnail": "https://emoji.gg/assets/emoji/4236-witchhat.png",
        "color": 0x9B59B6,
        "entries": [
            ("Vampira Cappucina", 60.0),
            ("Zombie Tralala", 33.0),
            ("Frankentteo", 4.0),
            ("La Vacca Jacko Linterino", 2.0),
            ("La Spooky Grande", 1.0),
        ],
    },
    "Fishing": {
        "cost": 150_000_000,
        "thumbnail": "https://emoji.gg/assets/emoji/3505-fishingrod.png",
        "color": 0x1ABC9C,
        "entries": [
            ("Zombie Tralala", 18.0),
            ("Los Tralaleritos", 18.0),
            ("Boatito Auratito", 18.0),
            ("Extinct Tralalero", 18.0),
            ("Las Tralaleritas", 18.0),
            ("Graipuss Medussi", 6.0),
            ("Tralaledon", 1.0),
            ("Eviledon", 1.0),
            ("Los Primos", 1.0),
            ("Orcaledon", 0.9),
            ("Capitano Moby", 0.1),
        ],
    },
}

# ミューテーション
MUTATIONS = [
    ("Gold",        1.25, 10.0),
    ("Diamond",     1.50, 5.0),
    ("Rainbow",     10.0, 1.0),
    ("Bloodrot",    2.00, 1.0),
    ("Candy",       4.00, 1.0),
    ("Lava",        6.00, 1.0),
    ("Galaxy",      7.00, 1.0),
    ("Yin Yang",    7.50, 1.0),
    ("Radioactive", 8.00, 1.0),
]
MUTATION_MULT = {n: m for n, m, _ in MUTATIONS}
MUTATION_INDEX = {name: idx + 1 for idx, (name, _, __) in enumerate(MUTATIONS)}  # 1始まり

# 価値表
M = 1_000_000
B = 1_000_000_000
CHAR_VALUES = {
    # Mythic
    "Spioniro Golubiro": 750_000,
    "Tigirlini Watermelini": 1_700_000,
    "Tigrilini Watermelini": 1_700_000,
    "Zibra Zubra Zibralini": 1_000_000,
    "Carrotini Brainini": 4_700_000,
    "Bananito Bandito": 4_900_000,
    # Brainrot God
    "Tigroligre Frutonni": 14 * M,
    "Orcalero Orcala": 25 * M,
    "Bulbito Bandito Traktorito": 25 * M,
    "Mastodontico Telepiedone": int(47.5 * M),
    "Pop Pop Sahur": 65 * M,
    # Secret
    "Torrtuginni Dragonfrutini": 125 * M,
    "Pot Hotspot": 600 * M,
    "Esok Sekolah": int(3.5 * B),
    "Spaghetti Tualetti": 15 * B,
    "La Secret Combinasion": 50 * B,
    # Admin
    "Carloo": int(4.5 * M),
    "Alessio": int(17.5 * M),
    "Los Bombinitos": int(42.5 * M),
    "Crabbo Limonetta": 46 * M,
    "Blackhole Goat": 75 * M,
    "Guerriro Digitale": 120 * M,
    "67": int(1.2 * B),
    "La Grande Combinasion": 1 * B,
    # Taco
    "Chihuanini Taconini": int(8.5 * M),
    "Gattito Tacoto": int(32.5 * M),
    "Los Tipi Tacos": 46 * M,
    "Quesadilla Crocodila": 700 * M,
    "Los Nooo My Hotspotsitos": 1 * B,
    "Burrito Bandito": 850 * M,
    # Los
    "Los Tungtungtungcitos": 37 * M,
    "Los Orcalitos": 45 * M,
    "Los Tortus": 100 * M,
    "Los Jobcitos": 500 * M,
    "Los Combinasionas": 2 * B,
    "Los 67": int(2.7 * B),

    # Los Taco
    "Los Chihuahinis": 32 * M,
    "Los Gattitos": int(47.5 * M),
    "Los Cucarachas": 300 * M,
    "Los Quesadillas": int(875 * M),
    "Los Quesadillos": int(875 * M),
    "Los Burritos": int(1.4 * B),

    # Spooky
    "Mummy Ambalabu": 45 * M,
    "Cappucino Clownino": int(48.5 * M),
    "Jackorilla": 80 * M,
    "Pumpkini Spyderini": 165 * M,
    "Trickolino": 235 * M,
    "Telemorte": 550 * M,
    "Los Spooky Combinasionas": 3 * B,
    "La Casa Boo": 40 * B,

    # ===== 新ティア: Cat =====
    "Gattatino Nyanino": int(7.5 * M),
    "Gattatino Neonino": int(7.5 * M),
    # Gattito Tacoto / Los Gattitos は既存の値を使用

    "Meowl": 350 * B,

    # ===== 新ティア: Jandel vs Sammy =====
    "Raccooni Jandelini": 1_300,           # 1.3K
    "Sammyni Spyderini": 75 * M,

    # ===== 新ティア: Hacker =====
    "1x1x1x1": int(255.5 * M),
    "Guest 666": int(1.1 * B),

    # ===== 新ティア: Extinct =====
    "Extinct Ballerina": int(23.5 * M),
    "Extinct Tralalero": 125 * M,
    "Extinct Matteo": 140 * M,
    "La Extinct Grande": int(3.2 * B),

    # ===== 新ティア: Witching Hour =====
    "Vampira Cappucina": int(24.5 * M),
    "Zombie Tralala": 100 * M,
    "Frankentteo": 175 * M,
    "La Vacca Jacko Linterino": 225 * M,
    "La Spooky Grande": int(2.9 * B),

    # ===== 新ティア: Fishing =====
    "Los Tralaleritos": 100 * M,
    "Boatito Auratito": 115 * M,
    "Las Tralaleritas": 150 * M,
    "Graipuss Medussi": 250 * M,
    "Tralaledon": int(3.5 * B),
    "Eviledon": int(3.8 * B),
    "Los Primos": int(3.7 * B),
    "Orcaledon": 7 * B,
    "Capitano Moby": 125 * B,
}
