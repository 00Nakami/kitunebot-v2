import aiosqlite
from typing import List, Tuple, Optional, Dict
from constants import MUTATION_INDEX

DB_PATH = "luckyblock.db"

CREATE_USERS = """CREATE TABLE IF NOT EXISTS users (
 user_id INTEGER PRIMARY KEY,
 credits INTEGER NOT NULL DEFAULT 0,
 last_open INTEGER NOT NULL DEFAULT 0,
 last_daily INTEGER NOT NULL DEFAULT 0
);"""

CREATE_BASE = """CREATE TABLE IF NOT EXISTS base_slots (
 user_id INTEGER NOT NULL,
 slot INTEGER NOT NULL,
 name TEXT, -- NULL=空
 PRIMARY KEY (user_id, slot)
);"""

CREATE_MUT_INDEX = """CREATE TABLE IF NOT EXISTS mutation_index (
 name TEXT PRIMARY KEY,
 idx INTEGER NOT NULL
);"""

# /daily の受取回数カウンタを持つ
CREATE_USER_META = """CREATE TABLE IF NOT EXISTS user_meta (
 user_id INTEGER PRIMARY KEY,
 daily_count INTEGER NOT NULL DEFAULT 0
);"""

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(CREATE_USERS)
        await db.execute(CREATE_BASE)
        await db.execute(CREATE_MUT_INDEX)
        await db.execute(CREATE_USER_META)
        # ミューテーションインデックスを反映
        for name, idx in MUTATION_INDEX.items():
            await db.execute(
                "INSERT INTO mutation_index(name, idx) VALUES(?,?) "
                "ON CONFLICT(name) DO UPDATE SET idx=excluded.idx",
                (name, idx)
            )
        await db.commit()

# users 基本
async def get_user_row(uid:int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur=await db.execute("SELECT credits,last_open,last_daily FROM users WHERE user_id=?", (uid,))
        r=await cur.fetchone()
        if not r:
            await db.execute("INSERT INTO users(user_id,credits,last_open,last_daily) VALUES(?,0,0,0)", (uid,))
            await db.execute("INSERT INTO user_meta(user_id,daily_count) VALUES(?,0) ON CONFLICT(user_id) DO NOTHING", (uid,))
            await db.commit()
            return 0,0,0
        # user_meta 側が無い古いデータに対処
        await db.execute("INSERT INTO user_meta(user_id,daily_count) VALUES(?,0) ON CONFLICT(user_id) DO NOTHING", (uid,))
        await db.commit()
        return r[0], r[1], r[2]

async def update_user(uid:int,*,credits=None,last_open=None,last_daily=None):
    sets=[];params=[]
    if credits is not None: sets.append("credits=?");params.append(credits)
    if last_open is not None: sets.append("last_open=?");params.append(last_open)
    if last_daily is not None: sets.append("last_daily=?");params.append(last_daily)
    if not sets: return
    params.append(uid)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE users SET {', '.join(sets)} WHERE user_id=?", params)
        await db.commit()

# /daily カウント
async def get_daily_count(uid:int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT daily_count FROM user_meta WHERE user_id=?", (uid,))
        r = await cur.fetchone()
        if not r:
            await db.execute("INSERT INTO user_meta(user_id,daily_count) VALUES(?,0)", (uid,))
            await db.commit()
            return 0
        return int(r[0])

async def increment_daily_count(uid:int) -> int:
    """カウントを+1して新しい値を返す"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO user_meta(user_id,daily_count) VALUES(?,0) ON CONFLICT(user_id) DO NOTHING", (uid,))
        await db.execute("UPDATE user_meta SET daily_count = daily_count + 1 WHERE user_id=?", (uid,))
        await db.commit()
        cur = await db.execute("SELECT daily_count FROM user_meta WHERE user_id=?", (uid,))
        r = await cur.fetchone()
        return int(r[0]) if r else 0

# base
async def ensure_base(uid:int):
    async with aiosqlite.connect(DB_PATH) as db:
        for i in range(1, 26):
            await db.execute("INSERT INTO base_slots(user_id, slot, name) VALUES(?, ?, NULL) ON CONFLICT(user_id,slot) DO NOTHING", (uid, i))
        await db.commit()

async def list_base(uid:int) -> List[Tuple[int, Optional[str]]]:
    await ensure_base(uid)
    async with aiosqlite.connect(DB_PATH) as db:
        cur=await db.execute("SELECT slot,name FROM base_slots WHERE user_id=? ORDER BY slot ASC", (uid,))
        return await cur.fetchall()

async def free_slots(uid:int) -> List[int]:
    rows = await list_base(uid)
    return [slot for slot, name in rows if name is None]

async def place_in_first_free(uid:int, name:str) -> Optional[int]:
    frees = await free_slots(uid)
    if not frees: return None
    slot = min(frees)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE base_slots SET name=? WHERE user_id=? AND slot=?", (name, uid, slot))
        await db.commit()
    return slot

async def set_slot_value(uid:int, slot:int, name:Optional[str]):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE base_slots SET name=? WHERE user_id=? AND slot=?", (name, uid, slot))
        await db.commit()

async def get_slot_name(uid:int, slot:int) -> Optional[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        cur=await db.execute("SELECT name FROM base_slots WHERE user_id=? AND slot=?", (uid, slot))
        row=await cur.fetchone()
        return None if not row else row[0]

async def remove_from_slot(uid:int, slot:int) -> Optional[str]:
    name = await get_slot_name(uid, slot)
    if name is None: return None
    await set_slot_value(uid, slot, None)
    return name

async def place_bulk(uid:int, pulls:Dict[str,int]):
    placed, overflow = {}, {}
    for n, c in pulls.items():
        for _ in range(c):
            s = await place_in_first_free(uid, n)
            if s is None:
                overflow[n] = overflow.get(n, 0) + 1
            else:
                placed[n] = placed.get(n, 0) + 1
    return placed, overflow

# leaderboards
async def top_base_values(limit:int=10):
    from utils import base_value
    res=[]
    async with aiosqlite.connect(DB_PATH) as db:
        cur=await db.execute("SELECT DISTINCT user_id FROM base_slots")
        users=[r[0] for r in await cur.fetchall()]
    for uid in users:
        rows = await list_base(uid)
        s = sum(base_value(name) for _, name in rows if name)
        res.append((uid, s))
    res.sort(key=lambda x: x[1], reverse=True)
    return res[:limit]

async def top_credits(limit:int=10):
    async with aiosqlite.connect(DB_PATH) as db:
        cur=await db.execute("SELECT user_id, credits FROM users ORDER BY credits DESC LIMIT ?", (limit,))
        return await cur.fetchall()
