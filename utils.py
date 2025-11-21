# utils.py
import random
import re
import unicodedata
from typing import Optional, Tuple, Dict, Any, List
from constants import MUTATIONS, MUTATION_MULT, TIERS, CHAR_VALUES

# ======================
# 表示ユーティリティ
# ======================

def fmt_compact(n: int) -> str:
    """
    数値を k/m/b/t 付きで短縮表示。
    ・10未満の値は小数1桁を表示（1.2m, 9.8k など、四捨五入）
    ・10以上は小数を付けず整数（12m, 15b など）
    ・単位は k(千) / m(百万) / b(十億) / t(兆)
    ・1000未満はカンマ区切りでそのまま
    """
    sign = "-" if n < 0 else ""
    n = abs(float(n))

    units = [
        (1_000_000_000_000, "t"),  # trillion
        (1_000_000_000, "b"),      # billion
        (1_000_000, "m"),          # million
        (1_000, "k"),              # thousand
    ]

    for v, s in units:
        if n >= v:
            val = n / v
            # 10以上は小数なし、10未満は小数1桁
            if val >= 10:
                return f"{sign}{int(val)}{s}"
            else:
                # 小数1桁（四捨五入）。例: 1.15b -> 1.2b, 9.95k -> 10.0k（次の行で整数化）
                text = f"{val:.1f}"
                # 10.0 に丸まったら整数表示にする（10.0k -> 10k）
                if text.endswith(".0"):
                    return f"{sign}{int(round(val))}{s}"
                return f"{sign}{text}{s}"

    # 1000未満はそのまま（カンマ区切り）
    return f"{sign}{int(n):,}"

def fmt_remain(seconds: int) -> str:
    h, rem = divmod(max(0, seconds), 3600)
    m, s = divmod(rem, 60)
    if h: return f"{h}時間{m}分"
    if m: return f"{m}分{s}秒"
    return f"{s}秒"

def fmt_num(n: int) -> str:
    return f"{int(n):,}"

# ======================
# 入力正規化（クイズ用）
# ======================

_DIGIT_RE = re.compile(r"\d+")

def parse_int_loose(s: str) -> Optional[int]:
    """
    文字列から連続した数字を拾って整数化。
    例: " 42", "答えは42です", "４２", "  0  " → 42 / 0
    複数ある場合は最初のかたまりを使用。
    """
    if not s:
        return None
    s = unicodedata.normalize("NFKC", s)  # 全角→半角等
    m = _DIGIT_RE.search(s)
    if not m:
        return None
    try:
        return int(m.group(0))
    except ValueError:
        return None

_HIRA_KEEP = set(list("ーゔ"))  # 例外許容

def sanitize_to_hiragana_core(s: str) -> str:
    """
    文字列をNFKC正規化 → 空白/句読点/記号などを除去。
    その上で ひらがな or 許容記号(ー/ゔ) のみ残す。
    """
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", s)
    out = []
    for ch in s:
        code = ord(ch)
        # 空白・制御・句読点などはスキップ
        if ch.isspace() or unicodedata.category(ch).startswith(("P", "C")):
            continue
        # ひらがな or 許容記号のみ残す
        if 0x3040 <= code <= 0x309F or ch in _HIRA_KEEP:
            out.append(ch)
        # それ以外（カタカナ・英字・絵文字など）は無視
    return "".join(out)

def is_hiragana_strict_after_sanitize(s: str) -> bool:
    """sanitize 後の文字列が空でなく、すべて ひらがな（と許容記号）であるか"""
    s = sanitize_to_hiragana_core(s)
    if not s:
        return False
    for ch in s:
        code = ord(ch)
        if not (0x3040 <= code <= 0x309F or ch in _HIRA_KEEP):
            return False
    return True

# ======================
# ガチャ/価値計算
# ======================

def roll_mutation() -> Optional[str]:
    total_p = sum(p for _, _, p in MUTATIONS)
    none_p = max(0.0, 100.0 - total_p)
    names = [None] + [n for n, _, _ in MUTATIONS]
    weights = [none_p] + [p for _, _, p in MUTATIONS]
    return random.choices(names, weights=weights, k=1)[0]

def decorate_name(base: str, mutation: Optional[str]) -> str:
    return f"{base} ({mutation})" if mutation else base

def split_name(name_with_mut: str) -> Tuple[str, Optional[str]]:
    if name_with_mut.endswith(")"):
        i = name_with_mut.rfind(" (")
        if i != -1:
            return name_with_mut[:i], name_with_mut[i+2:-1]
    return name_with_mut, None

def choose_character(tier_name: str) -> str:
    e = TIERS[tier_name]["entries"]
    return random.choices([n for n,_ in e], weights=[w for _,w in e], k=1)[0]

def pull_once(tier_name: str) -> str:
    base = choose_character(tier_name)
    mut = roll_mutation()
    return decorate_name(base, mut)

def base_value(name_with_mut: str) -> int:
    base, mut = split_name(name_with_mut)
    v = int(CHAR_VALUES.get(base, 0))
    if mut and mut in MUTATION_MULT:
        v = int(v * MUTATION_MULT[mut])
    return v
