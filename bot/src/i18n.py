"""Client-facing bot translations (Russian / Uzbek).

Only messages sent TO CLIENTS are translated — admin notifications and the
/orders panel stay in Russian (the business owner is Russian-speaking). The
client's language is stored on User.language_code ("ru" default, "uz"); the
bot reads it before sending and falls back to Russian for anything unknown.

Usage: t("key", lang, order_id=5) — keys with {placeholders} are .format()ted.
"""

DEFAULT_LANG = "ru"
SUPPORTED_LANGS = ("ru", "uz")


def normalize_lang(lang: str | None) -> str:
    return lang if lang in SUPPORTED_LANGS else DEFAULT_LANG


# Client-facing order status labels (used in the "status changed" notification).
STATUS_LABELS = {
    "created": {"ru": "🆕 Создан", "uz": "🆕 Yaratildi"},
    "in_progress": {"ru": "✅ Одобрен", "uz": "✅ Tasdiqlandi"},
    "taken": {"ru": "📦 У клиента", "uz": "📦 Mijozda"},
    "paused": {"ru": "⏸ Приостановлен", "uz": "⏸ To'xtatildi"},
    "returned": {"ru": "✅ Завершён", "uz": "✅ Yakunlandi"},
    "completed": {"ru": "✅ Завершён", "uz": "✅ Yakunlandi"},
    "canceled": {"ru": "❌ Отменён", "uz": "❌ Bekor qilindi"},
}


def status_label(status: str, lang: str) -> str:
    lang = normalize_lang(lang)
    entry = STATUS_LABELS.get(status)
    if not entry:
        return status
    return entry.get(lang, entry["ru"])


TRANSLATIONS: dict[str, dict[str, str]] = {
    # ─── Language selection ───────────────────────────────────────────────
    "choose_language": {
        "ru": "Выберите язык / Tilni tanlang 👇",
        "uz": "Tilni tanlang / Выберите язык 👇",
    },
    "language_set": {
        "ru": "✅ Язык установлен: Русский",
        "uz": "✅ Til tanlandi: O‘zbekcha",
    },
    "menu_language": {
        "ru": "🌐 Язык",
        "uz": "🌐 Til",
    },
    "menu_refreshed": {
        "ru": "Клавиатура обновлена.",
        "uz": "Klaviatura yangilandi.",
    },
    "menu_my_orders": {
        "ru": "📋 Мои заказы",
        "uz": "📋 Buyurtmalarim",
    },
    "my_orders_empty": {
        "ru": "У вас нет активных заказов.",
        "uz": "Sizda faol buyurtmalar yo‘q.",
    },
    "my_orders_header": {
        "ru": "📋 <b>Ваши активные заказы:</b>",
        "uz": "📋 <b>Sizning faol buyurtmalaringiz:</b>",
    },
    "pay_card": {
        "ru": "Картой",
        "uz": "Karta orqali",
    },
    "pay_cash": {
        "ru": "Наличными",
        "uz": "Naqd pul",
    },
    # ─── Registration ─────────────────────────────────────────────────────
    "phone_prompt": {
        "ru": (
            "Чтобы оформлять заказы, нам нужен ваш номер телефона.\n"
            "Нажмите кнопку ниже, чтобы поделиться контактом 👇\n\n"
            "Или просто отправьте номер сообщением, например: +998 90 123 45 67"
        ),
        "uz": (
            "Buyurtma berish uchun telefon raqamingiz kerak.\n"
            "Kontaktni ulashish uchun quyidagi tugmani bosing 👇\n\n"
            "Yoki raqamni xabar sifatida yuboring, masalan: +998 90 123 45 67"
        ),
    },
    "phone_button": {
        "ru": "📱 Отправить номер",
        "uz": "📱 Raqamni yuborish",
    },
    "phone_invalid": {
        "ru": (
            "Не похоже на номер телефона 🤔\n"
            "Нажмите кнопку «📱 Отправить номер» или пришлите номер в формате +998 90 123 45 67."
        ),
        "uz": (
            "Bu telefon raqamiga o‘xshamaydi 🤔\n"
            "«📱 Raqamni yuborish» tugmasini bosing yoki raqamni +998 90 123 45 67 ko‘rinishida yuboring."
        ),
    },
    "foreign_contact": {
        "ru": "Пожалуйста, отправьте свой собственный контакт кнопкой ниже.",
        "uz": "Iltimos, quyidagi tugma orqali o‘zingizning kontaktingizni yuboring.",
    },
    "name_prompt": {
        "ru": "Отлично! Как к вам обращаться? Напишите имя или выберите вариант ниже 👇",
        "uz": "Ajoyib! Sizga qanday murojaat qilaylik? Ismingizni yozing yoki quyidagidan tanlang 👇",
    },
    "name_invalid": {
        "ru": "Пожалуйста, отправьте имя обычным текстовым сообщением.",
        "uz": "Iltimos, ismingizni oddiy matn sifatida yuboring.",
    },
    "registration_done": {
        "ru": (
            "✅ Регистрация завершена!\n\n"
            "Нажмите на кнопку «Магазин», чтобы открыть мини-приложение — "
            "имя и телефон подставятся в заказ автоматически."
        ),
        "uz": (
            "✅ Ro‘yxatdan o‘tish yakunlandi!\n\n"
            "Mini-ilovani ochish uchun «Do‘kon» tugmasini bosing — "
            "ism va telefon buyurtmaga avtomatik qo‘yiladi."
        ),
    },
    # ─── General ──────────────────────────────────────────────────────────
    "welcome": {
        "ru": "Добро пожаловать! Нажмите на кнопку «Магазин», чтобы открыть мини-приложение.",
        "uz": "Xush kelibsiz! Mini-ilovani ochish uchun «Do‘kon» tugmasini bosing.",
    },
    "service_unavailable": {
        "ru": "Сервис временно недоступен. Пожалуйста, попробуйте позже.",
        "uz": "Xizmat vaqtincha ishlamayapti. Iltimos, keyinroq urinib ko‘ring.",
    },
    "unexpected_error": {
        "ru": "Произошла непредвиденная ошибка. Пожалуйста, попробуйте позже.",
        "uz": "Kutilmagan xatolik yuz berdi. Iltimos, keyinroq urinib ko‘ring.",
    },
    "banned_notice": {
        "ru": (
            "🚫 <b>Ваш аккаунт заблокирован.</b>\n"
            "Оформление заказов недоступно.\n\n"
            "По вопросам обращайтесь к менеджеру: {manager}"
        ),
        "uz": (
            "🚫 <b>Hisobingiz bloklangan.</b>\n"
            "Buyurtma berish mavjud emas.\n\n"
            "Savollar bo‘yicha menejerga murojaat qiling: {manager}"
        ),
    },
    # ─── Receipt flow ─────────────────────────────────────────────────────
    "no_pending_orders": {
        "ru": "У вас нет заказов, ожидающих подтверждения оплаты.",
        "uz": "Sizda to‘lov tasdig‘ini kutayotgan buyurtma yo‘q.",
    },
    "receipt_which_order": {
        "ru": "У вас несколько заказов, ожидающих оплаты. К какому из них относится этот чек?",
        "uz": "Sizda to‘lovni kutayotgan bir nechta buyurtma bor. Bu chek qaysi biriga tegishli?",
    },
    "receipt_order_button": {
        "ru": "Заказ #{order_id} — {price} сум",
        "uz": "#{order_id} buyurtma — {price} so‘m",
    },
    "receipt_received": {
        "ru": "Чек получен, проверяем оплату...",
        "uz": "Chek qabul qilindi, to‘lovni tekshiryapmiz...",
    },
    "receipt_not_found": {
        "ru": "Чек не найден, отправьте его ещё раз.",
        "uz": "Chek topilmadi, uni qayta yuboring.",
    },
    "payment_confirmed": {
        "ru": "✅ Оплата по заказу #{order_id} подтверждена, бронь закреплена за вами.",
        "uz": "✅ #{order_id} buyurtma bo‘yicha to‘lov tasdiqlandi, bron siz uchun saqlab qo‘yildi.",
    },
    "pickup_location": {
        "ru": "Вот локация где можно забрать снаряжение:",
        "uz": "Jihozlarni olib ketish mumkin bo‘lgan manzil:",
    },
    "card_for_booking": {
        "ru": "Вот номер карты для брони: <code>{card_number}</code>",
        "uz": "Bron uchun karta raqami: <code>{card_number}</code>",
    },
    "dates_taken_canceled": {
        "ru": (
            "❌ К сожалению, эти даты по заказу #{order_id} уже забронировал другой клиент. "
            "Заказ отменён — оформите новый на актуальные даты, если снаряжение всё ещё нужно."
        ),
        "uz": (
            "❌ Afsuski, #{order_id} buyurtmadagi bu sanalarni boshqa mijoz band qildi. "
            "Buyurtma bekor qilindi — jihozlar hali kerak bo‘lsa, mavjud sanalarga yangi buyurtma bering."
        ),
    },
    # ─── Order created (deposit request) ──────────────────────────────────
    "order_created": {
        "ru": "⭕️ <b>Ваш заказ #{order_id} создан!</b>\n\n",
        "uz": "⭕️ <b>#{order_id} buyurtmangiz yaratildi!</b>\n\n",
    },
    "pickup_date": {
        "ru": "📅 Дата получения: <b>{dt}</b>\n",
        "uz": "📅 Olish sanasi: <b>{dt}</b>\n",
    },
    "return_date": {
        "ru": "📆 Дата возврата: <b>{dt}</b>\n",
        "uz": "📆 Qaytarish sanasi: <b>{dt}</b>\n",
    },
    "pickup_address": {
        "ru": "📍 Адрес выдачи: <b>{address}</b>\n\n",
        "uz": "📍 Berish manzili: <b>{address}</b>\n\n",
    },
    "address_pending": {
        "ru": "уточняется у менеджера",
        "uz": "menejer bilan aniqlanadi",
    },
    "deposit_instructions": {
        "ru": "❕Для подтверждения переведите предоплату <b>{deposit} сум</b> на карту:\n\n",
        "uz": "❕Tasdiqlash uchun <b>{deposit} so‘m</b> oldindan to‘lovni kartaga o‘tkazing:\n\n",
    },
    "deposit_card": {
        "ru": "💳 <b><code>{card_number}</code></b>\n\n",
        "uz": "💳 <b><code>{card_number}</code></b>\n\n",
    },
    "send_receipt_hint": {
        "ru": "❗️ <b>После оплаты отправьте фото чека в этот чат</b>\n\n",
        "uz": "❗️ <b>To‘lovdan so‘ng chek rasmini shu chatga yuboring</b>\n\n",
    },
    "order_items_header": {
        "ru": "📦 <b>Состав:</b>\n{items}\n\n",
        "uz": "📦 <b>Tarkib:</b>\n{items}\n\n",
    },
    "coins_redeemed": {
        "ru": "🎁 Списано баллов: <b>{amount} сум</b>\n\n",
        "uz": "🎁 Ball hisobidan yechildi: <b>{amount} so‘m</b>\n\n",
    },
    "coins_earned": {
        "ru": "🎁 Вам начислено бонусных баллов: <b>{amount} сум</b> — можно использовать на следующий заказ.",
        "uz": "🎁 Sizga bonus ball hisoblandi: <b>{amount} so‘m</b> — keyingi buyurtmada ishlatishingiz mumkin.",
    },
    # ─── Reminders & status ───────────────────────────────────────────────
    "pickup_reminder": {
        "ru": "⏰ <b>Напоминание:</b> через ~2 часа вы должны забрать заказ <b>#{order_id}</b>.",
        "uz": "⏰ <b>Eslatma:</b> ~2 soatdan so‘ng <b>#{order_id}</b> buyurtmani olib ketishingiz kerak.",
    },
    "return_reminder": {
        "ru": "⏰ <b>Напоминание:</b> через ~2 часа вы должны вернуть заказ <b>#{order_id}</b>.",
        "uz": "⏰ <b>Eslatma:</b> ~2 soatdan so‘ng <b>#{order_id}</b> buyurtmani qaytarishingiz kerak.",
    },
    "status_changed": {
        "ru": "ℹ️ <b>Статус вашего заказа #{order_id} изменён:</b> {status}",
        "uz": "ℹ️ <b>#{order_id} buyurtmangiz holati o‘zgardi:</b> {status}",
    },
    "hold_expired": {
        "ru": (
            "❌ <b>Заказ #{order_id} отменён.</b>\n"
            "Если снаряжение всё ещё нужно — оформите новый заказ на актуальные даты."
        ),
        "uz": (
            "❌ <b>#{order_id} buyurtma bekor qilindi.</b>\n"
            "Jihozlar hali kerak bo‘lsa — mavjud sanalarga yangi buyurtma bering."
        ),
    },
    "order_returned": {
        "ru": "✅ <b>Заказ #{order_id} завершён.</b>\n\nСпасибо, что выбрали нас. Будем ждать вас снова!",
        "uz": "✅ <b>#{order_id} buyurtma yakunlandi.</b>\n\nBizni tanlaganingiz uchun rahmat. Sizni yana kutamiz!",
    },
    "order_approved": {
        "ru": "✅ <b>Ваш заказ #{order_id} подтверждён!</b> Ждём вас.",
        "uz": "✅ <b>#{order_id} buyurtmangiz tasdiqlandi!</b> Sizni kutamiz.",
    },
    "order_paused_client": {
        "ru": "⏸ <b>Ваш заказ #{order_id} приостановлен.</b>",
        "uz": "⏸ <b>#{order_id} buyurtmangiz to‘xtatildi.</b>",
    },
    "order_closed_client": {
        "ru": "🔒 <b>Ваш заказ #{order_id} закрыт.</b>",
        "uz": "🔒 <b>#{order_id} buyurtmangiz yopildi.</b>",
    },
    "order_resumed_client": {
        "ru": "▶️ <b>Ваш заказ #{order_id} возобновлён.</b>",
        "uz": "▶️ <b>#{order_id} buyurtmangiz qayta tiklandi.</b>",
    },
}


def t(key: str, lang: str | None, **kwargs) -> str:
    lang = normalize_lang(lang)
    entry = TRANSLATIONS.get(key)
    if entry is None:
        return key
    template = entry.get(lang, entry.get(DEFAULT_LANG, key))
    return template.format(**kwargs) if kwargs else template
