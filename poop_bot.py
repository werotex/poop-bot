
optimized_code = '''import json
import os
import random
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = "8653103518:AAHs8a4Qeg4JSDeZ_fDAPk8du5V99nBykVQ"

DATA_FILE = "players.json"

# Кэш данных в памяти
data_cache = None
last_save = None
SAVE_INTERVAL = 5  # Сохраняем на диск каждые 5 секунд минимум

# Ивент "Золотая какашка"
GOLDEN_POOP_EVENT = {
    "active": False,
    "end_time": None,
    "multiplier": 3,
    "duration_minutes": 5
}

CLICK_UPGRADES = [
    {"id": "c1", "icon": "💨", "name": "Газовая атака",   "desc": "+2 за клик",   "cost": 15,    "val": 2,   "type": "click"},
    {"id": "c2", "icon": "🌬️", "name": "Ветряной залп",  "desc": "+5 за клик",   "cost": 80,    "val": 5,   "type": "click"},
    {"id": "c3", "icon": "🔥", "name": "Огненный пук",    "desc": "+15 за клик",  "cost": 350,   "val": 15,  "type": "click"},
    {"id": "c4", "icon": "⚡", "name": "Молния вонизма",  "desc": "+40 за клик",  "cost": 1500,  "val": 40,  "type": "click"},
    {"id": "c5", "icon": "🌪️", "name": "Торнадо-пук",    "desc": "+120 за клик", "cost": 8000,  "val": 120, "type": "click"},
    {"id": "c6", "icon": "💥", "name": "Ядерный пердёж",  "desc": "+400 за клик", "cost": 40000, "val": 400, "type": "click"},
]

AUTO_UPGRADES = [
    {"id": "a1", "icon": "🐛", "name": "Червячок",    "desc": "+1/сек",   "cost": 50,     "val": 1,   "type": "auto"},
    {"id": "a2", "icon": "🐄", "name": "Корова",      "desc": "+4/сек",   "cost": 250,    "val": 4,   "type": "auto"},
    {"id": "a3", "icon": "🏗️", "name": "Фабрика",    "desc": "+12/сек",  "cost": 1200,   "val": 12,  "type": "auto"},
    {"id": "a4", "icon": "🚀", "name": "Пук-ракета",  "desc": "+35/сек",  "cost": 6000,   "val": 35,  "type": "auto"},
    {"id": "a5", "icon": "🛸", "name": "НЛО какашек", "desc": "+100/сек", "cost": 30000,  "val": 100, "type": "auto"},
    {"id": "a6", "icon": "🌍", "name": "Планета пуков","desc": "+350/сек", "cost": 150000, "val": 350, "type": "auto"},
]

MULT_UPGRADES = [
    {"id": "m1", "icon": "🧪", "name": "Газовая смесь",   "desc": "Клик x1.5", "cost": 500,    "val": 1.5, "type": "mult_click"},
    {"id": "m2", "icon": "⚗️", "name": "Лаборатория",    "desc": "Авто x1.5", "cost": 2000,   "val": 1.5, "type": "mult_auto"},
    {"id": "m3", "icon": "🔬", "name": "Нано-пук",        "desc": "Клик x2",   "cost": 10000,  "val": 2.0, "type": "mult_click"},
    {"id": "m4", "icon": "🏛️", "name": "Институт газа",  "desc": "Авто x2",   "cost": 50000,  "val": 2.0, "type": "mult_auto"},
    {"id": "m5", "icon": "🌟", "name": "Золотая какашка", "desc": "Всё x1.5",  "cost": 100000, "val": 1.5, "type": "mult_all"},
    {"id": "m6", "icon": "👑", "name": "Царь-пук",        "desc": "Всё x3",    "cost": 500000, "val": 3.0, "type": "mult_all"},
]

ALL_UPGRADES = {u["id"]: u for u in CLICK_UPGRADES + AUTO_UPGRADES + MULT_UPGRADES}


def load_data():
    """Загружает данные с диска только если кэш пуст"""
    global data_cache
    if data_cache is not None:
        return data_cache
    
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data_cache = json.load(f)
                return data_cache
        except:
            pass
    
    data_cache = {"players": {}, "active_users": {}}
    return data_cache


def save_data(force=False):
    """Сохраняет данные на диск с задержкой"""
    global data_cache, last_save
    
    if data_cache is None:
        return
    
    now = datetime.now()
    if not force and last_save and (now - last_save).seconds < SAVE_INTERVAL:
        return  # Пропускаем частые сохранения
    
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data_cache, f, ensure_ascii=False, indent=2)
        last_save = now
    except Exception as e:
        print(f"Ошибка сохранения: {e}")


def get_player(uid, username=None):
    """Получает игрока из кэша"""
    data = load_data()
    uid = str(uid)
    
    if "players" not in data:
        data["players"] = {}
    
    if uid not in data["players"]:
        data["players"][uid] = {
            "score": 0,
            "total": 0,
            "click_base": 1,
            "auto_base": 0,
            "mult_click": 1.0,
            "mult_auto": 1.0,
            "mult_all": 1.0,
            "prestige": 0,
            "prestige_mult": 1,
            "upg_costs": {},
            "bought": {},
            "username": username or "Unknown",
        }
    
    if username and data["players"][uid].get("username") != username:
        data["players"][uid]["username"] = username
    
    return data["players"][uid]


def update_active_user(uid, username):
    """Обновляет активность пользователя"""
    data = load_data()
    if "active_users" not in data:
        data["active_users"] = {}
    
    now = datetime.now().isoformat()
    data["active_users"][str(uid)] = {
        "username": username or "Unknown",
        "last_active": now
    }
    
    # Очищаем неактивных
    active_list = []
    for user_id, info in list(data["active_users"].items()):
        last_active = datetime.fromisoformat(info["last_active"])
        if datetime.now() - last_active > timedelta(minutes=5):
            del data["active_users"][user_id]
        else:
            active_list.append(info["username"])
    
    return active_list


def get_active_users_text():
    """Возвращает текст с активными пользователями"""
    data = load_data()
    if "active_users" not in data or len(data["active_users"]) < 2:
        return ""
    
    usernames = [info["username"] for info in data["active_users"].values()]
    if len(usernames) >= 2:
        return f"\\n\\n👥 Онлайн ({len(usernames)}): {', '.join(usernames)}"
    return ""


def check_golden_event():
    """Проверяет статус ивента"""
    global GOLDEN_POOP_EVENT
    
    if GOLDEN_POOP_EVENT["active"]:
        if datetime.now() >= GOLDEN_POOP_EVENT["end_time"]:
            GOLDEN_POOP_EVENT["active"] = False
            GOLDEN_POOP_EVENT["end_time"] = None
            return False, "ended"
        return True, "active"
    return False, "inactive"


def start_golden_event():
    """Запускает ивент"""
    global GOLDEN_POOP_EVENT
    GOLDEN_POOP_EVENT["active"] = True
    GOLDEN_POOP_EVENT["end_time"] = datetime.now() + timedelta(minutes=GOLDEN_POOP_EVENT["duration_minutes"])
    return GOLDEN_POOP_EVENT["end_time"]


def get_event_status_text():
    """Возвращает текст статуса ивента"""
    is_active, status = check_golden_event()
    if is_active:
        remaining = GOLDEN_POOP_EVENT["end_time"] - datetime.now()
        minutes = int(remaining.total_seconds() // 60)
        seconds = int(remaining.total_seconds() % 60)
        return f"\\n\\n🌟 ЗОЛОТАЯ КАКАШКА! x{GOLDEN_POOP_EVENT['multiplier']} фарма!\\n⏰ Осталось: {minutes}м {seconds}с"
    return ""


def get_event_multiplier():
    """Возвращает множитель ивента"""
    is_active, _ = check_golden_event()
    return GOLDEN_POOP_EVENT["multiplier"] if is_active else 1


def upg_cost(p):
    costs = {}
    for uid_upg, u in ALL_UPGRADES.items():
        costs[uid_upg] = p["upg_costs"].get(uid_upg, u["cost"])
    return costs


def click_power(p):
    base = max(1, round(p["click_base"] * p["mult_click"] * p["mult_all"] * p["prestige_mult"]))
    return base * get_event_multiplier()


def auto_power(p):
    base = p["auto_base"] * p["mult_auto"] * p["mult_all"] * p["prestige_mult"]
    return base * get_event_multiplier()


def fmt(n):
    n = int(n)
    if n >= 1_000_000_000:
        return f"{n/1e9:.1f}B"
    if n >= 1_000_000:
        return f"{n/1e6:.1f}M"
    if n >= 1_000:
        return f"{n/1e3:.1f}K"
    return str(n)


def prestige_cost(p):
    if p["prestige"] == 0:
        return 10_000
    return round(10_000 * (5 ** p["prestige"]))


def make_main_keyboard(p):
    ap = auto_power(p)
    auto_str = f" (+{fmt(ap)}/сек)" if ap > 0 else ""
    rows = [
        [InlineKeyboardButton(f"💩 Кликнуть (+{fmt(click_power(p))}){auto_str}", callback_data="click")],
        [
            InlineKeyboardButton("🛒 Прокачка", callback_data="menu_upgrades"),
            InlineKeyboardButton("📊 Стат", callback_data="menu_stats"),
        ],
        [InlineKeyboardButton(f"✨ Престиж ({fmt(prestige_cost(p))} 💩)", callback_data="menu_prestige")],
    ]
    return InlineKeyboardMarkup(rows)


def make_game_text(p):
    lines = [
        "💩 *Какашка Кликер*",
        "",
        f"💰 Какашек: *{fmt(p['score'])}*",
        f"👆 За клик: *{fmt(click_power(p))}*",
        f"⚙️ В секунду: *{fmt(auto_power(p))}*",
        f"📦 Всего: *{fmt(p['total'])}*",
    ]
    if p["prestige"] > 0:
        lines.append(f"✨ Престиж: *{p['prestige']}* (x{p['prestige_mult']})")
    
    text = "\\n".join(lines)
    text += get_event_status_text()
    text += get_active_users_text()
    return text


def make_upgrades_keyboard(p, category):
    costs = upg_cost(p)
    cats = {"click": CLICK_UPGRADES, "auto": AUTO_UPGRADES, "mult": MULT_UPGRADES}
    upgrades = cats.get(category, CLICK_UPGRADES)
    rows = []
    for u in upgrades:
        cost = costs[u["id"]]
        can = "✅" if p["score"] >= cost else "🔒"
        btn_text = f"{can} {u['icon']} {u['name']} — {fmt(cost)} 💩"
        rows.append([InlineKeyboardButton(btn_text, callback_data=f"buy_{u['id']}")])

    nav = [
        InlineKeyboardButton("👆 Клик", callback_data="menu_upg_click"),
        InlineKeyboardButton("⚙️ Авто", callback_data="menu_upg_auto"),
        InlineKeyboardButton("⚡ Множ.", callback_data="menu_upg_mult"),
    ]
    rows.append(nav)
    rows.append([InlineKeyboardButton("← Назад", callback_data="menu_main")])
    return InlineKeyboardMarkup(rows)


def make_upgrades_text(p, category):
    costs = upg_cost(p)
    cats = {"click": ("👆 Клик-улучшения", CLICK_UPGRADES),
            "auto":  ("⚙️ Авто-производство", AUTO_UPGRADES),
            "mult":  ("⚡ Мультипликаторы", MULT_UPGRADES)}
    title, upgrades = cats.get(category, cats["click"])
    lines = [f"*{title}*", ""]
    for u in upgrades:
        cost = costs[u["id"]]
        status = "✅" if p["score"] >= cost else "🔒"
        cnt = p["bought"].get(u["id"], 0)
        cnt_str = f" (куплено: {cnt})" if cnt else ""
        lines.append(f"{status} {u['icon']} *{u['name']}* — {u['desc']}{cnt_str}")
        lines.append(f"   Цена: {fmt(cost)} 💩")
    return "\\n".join(lines)


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    p = get_player(uid, username)
    update_active_user(uid, username)
    
    await update.message.reply_text(
        make_game_text(p),
        parse_mode="Markdown",
        reply_markup=make_main_keyboard(p),
    )


async def button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = str(query.from_user.id)
    username = query.from_user.username or query.from_user.first_name
    p = get_player(uid, username)
    cb = query.data

    active_users = update_active_user(uid, username)

    if cb == "click":
        earned = click_power(p)
        p["score"] += earned
        p["total"] += earned
        
        is_event, _ = check_golden_event()
        bonus_text = " 🌟 x3 ИВЕНТ!" if is_event else ""
        
        await query.edit_message_text(
            make_game_text(p) + f"\\n\\n💥 +{fmt(earned)} какашек!{bonus_text}",
            parse_mode="Markdown",
            reply_markup=make_main_keyboard(p),
        )

    elif cb == "menu_main":
        await query.edit_message_text(
            make_game_text(p),
            parse_mode="Markdown",
            reply_markup=make_main_keyboard(p),
        )

    elif cb == "menu_upgrades" or cb == "menu_upg_click":
        await query.edit_message_text(
            make_upgrades_text(p, "click"),
            parse_mode="Markdown",
            reply_markup=make_upgrades_keyboard(p, "click"),
        )

    elif cb == "menu_upg_auto":
        await query.edit_message_text(
            make_upgrades_text(p, "auto"),
            parse_mode="Markdown",
            reply_markup=make_upgrades_keyboard(p, "auto"),
        )

    elif cb == "menu_upg_mult":
        await query.edit_message_text(
            make_upgrades_text(p, "mult"),
            parse_mode="Markdown",
            reply_markup=make_upgrades_keyboard(p, "mult"),
        )

    elif cb == "menu_stats":
        lines = [
            "📊 *Статистика*",
            "",
            f"💰 Сейчас: {fmt(p['score'])} 💩",
            f"📦 Всего заработано: {fmt(p['total'])} 💩",
            f"👆 За клик: {fmt(click_power(p))} 💩",
            f"⚙️ В секунду: {fmt(auto_power(p))} 💩",
            f"🖱 База клика: {fmt(p['click_base'])}",
            f"⚙️ База авто: {fmt(p['auto_base'])}",
            f"⚡ Множ. клик: x{p['mult_click']:.1f}",
            f"⚡ Множ. авто: x{p['mult_auto']:.1f}",
            f"⚡ Множ. всё: x{p['mult_all']:.1f}",
            f"✨ Престиж: {p['prestige']} (x{p['prestige_mult']})",
        ]
        if len(active_users) >= 2:
            lines.append(f"\\n👥 Онлайн: {', '.join(active_users)}")
        
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("← Назад", callback_data="menu_main")]])
        await query.edit_message_text("\\n".join(lines), parse_mode="Markdown", reply_markup=kb)

    elif cb == "menu_prestige":
        cost = prestige_cost(p)
        new_mult = p["prestige_mult"] * 2
        lines = [
            "✨ *Престиж*",
            "",
            f"Стоимость: *{fmt(cost)} 💩*",
            f"Твои какашки: *{fmt(p['score'])}*",
            "",
            "⚠️ Сброс: очки, улучшения, базы",
            f"✅ Награда: постоянный множитель *x{new_mult}* (сейчас x{p['prestige_mult']})",
        ]
        can = p["score"] >= cost
        btns = []
        if can:
            btns.append(InlineKeyboardButton("✨ Подтвердить престиж!", callback_data="do_prestige"))
        btns_row = [InlineKeyboardButton("← Назад", callback_data="menu_main")]
        kb = InlineKeyboardMarkup([btns, btns_row] if btns else [btns_row])
        await query.edit_message_text("\\n".join(lines), parse_mode="Markdown", reply_markup=kb)

    elif cb == "do_prestige":
        cost = prestige_cost(p)
        if p["score"] >= cost:
            p["prestige"] += 1
            p["prestige_mult"] = 2 ** p["prestige"]
            p["score"] = 0
            p["total"] = 0
            p["click_base"] = 1
            p["auto_base"] = 0
            p["mult_click"] = 1.0
            p["mult_auto"] = 1.0
            p["mult_all"] = 1.0
            p["upg_costs"] = {}
            p["bought"] = {}
            await query.edit_message_text(
                f"✨ *Престиж {p['prestige']} активирован!*\\n\\nМножитель: x{p['prestige_mult']}\\n\\nНачинаем заново...",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Играть!", callback_data="menu_main")]]),
            )
        else:
            await query.answer("Недостаточно какашек!", show_alert=True)

    elif cb.startswith("buy_"):
        upg_id = cb[4:]
        u = ALL_UPGRADES.get(upg_id)
        if not u:
            return
        cost = p["upg_costs"].get(upg_id, u["cost"])
        if p["score"] < cost:
            await query.answer("Недостаточно 💩!", show_alert=True)
            return
        p["score"] -= cost
        mult = 4 if u["type"].startswith("mult") else 2.8
        p["upg_costs"][upg_id] = round(cost * mult)
        p["bought"][upg_id] = p["bought"].get(upg_id, 0) + 1
        if u["type"] == "click":
            p["click_base"] += u["val"]
        elif u["type"] == "auto":
            p["auto_base"] += u["val"]
        elif u["type"] == "mult_click":
            p["mult_click"] *= u["val"]
        elif u["type"] == "mult_auto":
            p["mult_auto"] *= u["val"]
        elif u["type"] == "mult_all":
            p["mult_all"] *= u["val"]
        await query.answer(f"Куплено: {u['name']}!")
        await query.edit_message_text(
            make_upgrades_text(p, "click" if u["type"] == "click" else ("auto" if u["type"] == "auto" else "mult")),
            parse_mode="Markdown",
            reply_markup=make_upgrades_keyboard(p, "click" if u["type"] == "click" else ("auto" if u["type"] == "auto" else "mult")),
        )


async def auto_save_task():
    """Фоновая задача автосохранения"""
    while True:
        await asyncio.sleep(10)  # Сохраняем каждые 10 секунд
        save_data()


async def event_task(context: ContextTypes.DEFAULT_TYPE):
    """Фоновая задача ивентов каждые 10 минут"""
    while True:
        await asyncio.sleep(600)  # 10 минут
        
        if random.random() < 0.3:  # 30% шанс
            end_time = start_golden_event()
            print(f"🌟 Золотая какашка! До: {end_time}")
            
            # Уведомляем всех активных
            data = load_data()
            if "active_users" in data:
                for uid in data["active_users"]:
                    try:
                        await context.bot.send_message(
                            chat_id=int(uid),
                            text="🌟 *ЗОЛОТАЯ КАКАШКА НАЧАЛАСЬ!*\\n\\nx3 фарм на 5 минут!",
                            parse_mode="Markdown"
                        )
                    except:
                        pass


def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    
    # Запускаем фоновые задачи
    asyncio.create_task(auto_save_task())
    
    print("Бот запущен! 🚀")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
'''

print("Оптимизированный код готов!")
print("\n🔧 Основные изменения:")
print("1. Кэширование данных в памяти (не читаем файл каждый раз)")
print("2. Автосохранение каждые 10 секунд вместо каждого действия")
print("3. Убраны лишние вызовы save_data()")
print("4. Упрощены функции, убраны лишние параметры")
print("5. drop_pending_updates=True - игнорирует старые сообщения при перезапуске")
