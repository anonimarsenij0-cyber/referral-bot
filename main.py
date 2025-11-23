import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
import os

TOKEN = os.getenv("7659736800:AAGYhGWx1yKaE4MENKXdjF4p-BtW6ilLcwk", "7659736800:AAGYhGWx1yKaE4MENKXdjF4p-BtW6ilLcwk")

ADMINS = {6459081502, 8292011713, 7551001962}

bot = Bot(TOKEN)
dp = Dispatcher()

# ====== Память (вместо базы) ======
users = {}          # user_id: {"balance": int}
orders = {}         # order_id: {...}
current_order_id = 1

# ====== Цены ======
PRICING = {
    "Telegram": {
        "Подписчики (обычные)": 1,
        "Подписчики (навсегда)": 99,
        "Просмотры постов": 2,
        "Просмотры историй": 2,
        "Лайки на истории": 4
    },
    "TikTok": {"Любая услуга": 1},
    "Instagram": {"Любая услуга": 1},
    "VK": {"Любая услуга": 1},
    "YouTube": {"Любая услуга": 1},
    "Facebook": {"Любая услуга": 1},
    "Twitch": {"Любая услуга": 1},
}

# ====== Кнопки ======

def main_menu():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Накрутка 🔥", callback_data="boost")],
        [InlineKeyboardButton(text="Мой баланс", callback_data="balance")],
        [InlineKeyboardButton(text="Мои заказы", callback_data="my_orders")]
    ])
    return kb

def admin_menu():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Все заказы", callback_data="admin_orders")],
        [InlineKeyboardButton(text="Изменить цены", callback_data="edit_prices")],
        [InlineKeyboardButton(text="Изменить названия услуг", callback_data="edit_names")]
    ])
    return kb


# ====== СТАРТ ======

@dp.message(Command("start"))
async def start(message: types.Message):
    uid = message.from_user.id
    if uid not in users:
        users[uid] = {"balance": 100}   # стартовый баланс для теста

    text = "Привет! 👋\nДобро пожаловать в сервис накрутки.\nВыбери действие:"
    kb = main_menu()

    if uid in ADMINS:
        text += "\n\nВы админ."
        admin_kb = admin_menu()
        kb.inline_keyboard += admin_kb.inline_keyboard

    await message.answer(text, reply_markup=kb)

# ====== БАЛАНС ======
@dp.callback_query(lambda c: c.data == "balance")
async def show_balance(callback: types.CallbackQuery):
    uid = callback.from_user.id
    bal = users[uid]["balance"]
    await callback.message.edit_text(f"Ваш баланс: {bal}₽", reply_markup=main_menu())


# ====== КАТЕГОРИИ ======
@dp.callback_query(lambda c: c.data == "boost")
async def choose_category(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup()
    for cat in PRICING.keys():
        kb.add(InlineKeyboardButton(text=cat, callback_data=f"cat_{cat}"))
    kb.add(InlineKeyboardButton(text="⬅ Назад", callback_data="back_menu"))
    await callback.message.edit_text("Выберите категорию:", reply_markup=kb)


# ====== УСЛУГИ ======
@dp.callback_query(lambda c: c.data.startswith("cat_"))
async def choose_service(callback: types.CallbackQuery):
    category = callback.data.split("_", 1)[1]
    kb = InlineKeyboardMarkup()

    for service in PRICING[category]:
        kb.add(InlineKeyboardButton(text=service, callback_data=f"svc_{category}_{service}"))

    kb.add(InlineKeyboardButton(text="⬅ Назад", callback_data="boost"))

    await callback.message.edit_text(f"Услуги категории {category}:", reply_markup=kb)


# ====== СОЗДАНИЕ ЗАКАЗА (вопросы) ======

pending_order = {}   # user_id: {"category":..., "service":...}

@dp.callback_query(lambda c: c.data.startswith("svc_"))
async def service_selected(callback: types.CallbackQuery):
    uid = callback.from_user.id
    _, category, service = callback.data.split("_", 2)

    pending_order[uid] = {"category": category, "service": service}

    await callback.message.edit_text(
        f"📝 Услуга: {service}\nВведите количество:"
    )

    @dp.message()
    async def get_amount(message: types.Message):
        if message.from_user.id != uid:
            return
        try:
            amount = int(message.text)
        except:
            await message.answer("Введите число!")
            return

        pending_order[uid]["amount"] = amount
        await message.answer("Теперь отправьте ссылку:")
        
        @dp.message()
        async def get_link(msg: types.Message):
            if msg.from_user.id != uid:
                return

            pending_order[uid]["link"] = msg.text
            await msg.answer("Описание заказа:")
            
            @dp.message()
            async def get_desc(msg2: types.Message):
                if msg2.from_user.id != uid:
                    return

                pending_order[uid]["desc"] = msg2.text
                await msg2.answer("Ваш комментарий:")

                @dp.message()
                async def get_comment(msg3: types.Message):
                    if msg3.from_user.id != uid:
                        return

                    pending_order[uid]["comment"] = msg3.text
                    await msg3.answer("Ваш вопрос администратору:")

                    @dp.message()
                    async def get_question(msg4: types.Message):
                        if msg4.from_user.id != uid:
                            return

                        pending_order[uid]["question"] = msg4.text

                        # ===== СОЗДАНИЕ ЗАКАЗА =====
                        global current_order_id
                        oid = current_order_id
                        current_order_id += 1

                        order = pending_order[uid]
                        price_per_1000 = PRICING[order["category"]][order["service"]]
                        cost = price_per_1000 * (order["amount"] / 1000)

                        if users[uid]["balance"] < cost:
                            await msg4.answer(f"Недостаточно средств! Нужно: {cost}₽")
                            return

                        users[uid]["balance"] -= cost
                        order["user"] = uid
                        order["cost"] = cost
                        order["status"] = "Ожидание"
                        orders[oid] = order

                        await msg4.answer(f"Заказ №{oid} создан!\nСтатус: Ожидание")

                        # уведомление админам
                        for admin in ADMINS:
                            try:
                                await bot.send_message(
                                    admin,
                                    f"🆕 Новый заказ #{oid}\n"
                                    f"Категория: {order['category']}\n"
                                    f"Услуга: {order['service']}\n"
                                    f"Кол-во: {order['amount']}\n"
                                    f"Ссылка: {order['link']}\n"
                                    f"Описание: {order['desc']}\n"
                                    f"Комментарий: {order['comment']}\n"
                                    f"Вопрос: {order['question']}\n\n"
                                    f"/approve_{oid} — подтвердить\n"
                                    f"/reject_{oid} — отклонить"
                                )
                            except:
                                pass

                        del pending_order[uid]
                      # ====== МОИ ЗАКАЗЫ ======
@dp.callback_query(lambda c: c.data == "my_orders")
async def show_my_orders(callback: types.CallbackQuery):
    uid = callback.from_user.id
    text = "Ваши заказы:\n\n"
    empty = True

    for oid, order in orders.items():
        if order["user"] == uid:
            empty = False
            text += f"#{oid} — {order['service']} — {order['status']} — {order['cost']}₽\n"

    if empty:
        text = "У вас пока нет заказов."

    await callback.message.edit_text(text, reply_markup=main_menu())


# ====== АДМИН: ВСЕ ЗАКАЗЫ ======
@dp.callback_query(lambda c: c.data == "admin_orders")
async def admin_orders_list(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMINS:
        return

    text = "📦 Все заказы:\n\n"
    if not orders:
        text = "Заказов пока нет."

    for oid, order in orders.items():
        text += (
            f"#{oid} — {order['category']} / {order['service']}\n"
            f"Кол-во: {order['amount']}, Стоимость: {order['cost']}₽\n"
            f"Статус: {order['status']}\n"
            f"Пользователь: {order['user']}\n\n"
        )

    await callback.message.edit_text(text, reply_markup=admin_menu())


# ====== АДМИН: ИЗМЕНИТЬ БАЛАНС ======
@dp.message(Command("setbalance"))
async def set_balance(message: types.Message):
    if message.from_user.id not in ADMINS:
        return

    try:
        _, user_id, amount = message.text.split()
        user_id = int(user_id)
        amount = int(amount)
    except:
        await message.answer("Использование:\n/setbalance USER_ID NEW_BALANCE")
        return

    if user_id not in users:
        users[user_id] = {"balance": 0}

    users[user_id]["balance"] = amount
    await message.answer(f"Баланс пользователя {user_id} установлен: {amount}₽")


# ====== АДМИН: ПОДТВЕРДИТЬ ЗАКАЗ ======
@dp.message(lambda m: m.text.startswith("/approve_"))
async def approve_order(message: types.Message):
    if message.from_user.id not in ADMINS:
        return

    oid = int(message.text.replace("/approve_", ""))
    if oid not in orders:
        await message.answer("Такого заказа нет!")
        return

    orders[oid]["status"] = "Выполнен"

    uid = orders[oid]["user"]
    await bot.send_message(uid, f"✅ Ваш заказ #{oid} выполнен!")
    await message.answer(f"Заказ #{oid} подтверждён.")


# ====== АДМИН: ОТКЛОНИТЬ ЗАКАЗ ======
@dp.message(lambda m: m.text.startswith("/reject_"))
async def reject_order(message: types.Message):
    if message.from_user.id not in ADMINS:
        return

    oid = int(message.text.replace("/reject_", ""))
    if oid not in orders:
        await message.answer("Такого заказа нет!")
        return

    orders[oid]["status"] = "Отклонён"

    uid = orders[oid]["user"]
    await bot.send_message(uid, f"❌ Ваш заказ #{oid} отклонён!")
    await message.answer(f"Заказ #{oid} отклонён.")


# ====== КНОПКА НАЗАД ======
@dp.callback_query(lambda c: c.data == "back_menu")
async def back_to_menu(callback: types.CallbackQuery):
    await start(callback.message)


# ====== ЗАПУСК БОТА ======
async def main():
    print("Bot started!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
