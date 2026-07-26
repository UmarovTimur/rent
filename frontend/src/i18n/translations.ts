// Client-facing Mini App translations (Russian / Uzbek). Product content
// (names/descriptions) stays as-is from the DB — only the UI chrome is
// translated. Keys are flat; use useTranslation().t('key').

export type Lang = 'ru' | 'uz'

export const SUPPORTED_LANGS: Lang[] = ['ru', 'uz']

export const normalizeLang = (value: string | null | undefined): Lang =>
    value === 'uz' ? 'uz' : 'ru'

export const translations: Record<string, Record<Lang, string>> = {
    // ─── Header / clock / search ──────────────────────────────────────────
    rentalDate: { ru: 'Дата аренды', uz: 'Ijara sanasi' },
    rentalTime: { ru: 'Время аренды', uz: 'Ijara vaqti' },
    rentalDatesTitle: { ru: 'Даты аренды', uz: 'Ijara sanalari' },
    rentalDatesHint: {
        ru: 'Показываем доступные товары на выбранные даты аренды.',
        uz: 'Tanlangan ijara sanalariga mavjud mahsulotlarni ko‘rsatamiz.',
    },
    searchPlaceholder: { ru: 'Поиск по названию и описанию...', uz: 'Nom va tavsif bo‘yicha qidiruv...' },
    clockTooltip: { ru: 'Все даты и время аренды — по Ташкенту', uz: 'Barcha sanalar va vaqt — Toshkent bo‘yicha' },
    clockCity: { ru: 'Ташкент', uz: 'Toshkent' },

    // ─── Main list ────────────────────────────────────────────────────────
    nothingFound: { ru: 'Ничего не найдено', uz: 'Hech narsa topilmadi' },
    categoryEmpty: { ru: 'В этой категории пока нет товаров', uz: 'Bu turkumda hozircha mahsulot yo‘q' },

    // ─── Product card / page ──────────────────────────────────────────────
    unavailable: { ru: 'Недоступно', uz: 'Mavjud emas' },
    perDay: { ru: 'в день', uz: 'kuniga' },
    perDayShort: { ru: '/сут', uz: '/kun' },
    perDaySuffix: { ru: '/сутки', uz: '/kun' },
    perOnce: { ru: 'разово', uz: 'bir martalik' },
    specifyDates: { ru: 'Укажите даты аренды', uz: 'Ijara sanalarini kiriting' },
    unavailableForDates: { ru: 'Недоступно на эти даты', uz: 'Bu sanalarga mavjud emas' },
    alreadyInCartMax: { ru: 'Уже в корзине (максимум)', uz: 'Savatda (maksimal)' },
    chooseOptions: { ru: 'Выберите опции', uz: 'Variantlarni tanlang' },
    addToCart: { ru: 'В корзину', uz: 'Savatga' },
    limitTitle: { ru: 'Превышен лимит', uz: 'Chegara oshib ketdi' },
    limitBody: {
        ru: 'В корзине может быть не более 99 единиц одного товара',
        uz: 'Savatda bitta mahsulotdan 99 donadan ko‘p bo‘lishi mumkin emas',
    },
    gotIt: { ru: 'Понятно', uz: 'Tushunarli' },
    additionally: { ru: 'Дополнительно', uz: 'Qo‘shimcha' },

    // ─── Basket ───────────────────────────────────────────────────────────
    cart: { ru: 'Корзина', uz: 'Savat' },
    checkout: { ru: 'Оформить', uz: 'Rasmiylashtirish' },
    order: { ru: 'Заказать', uz: 'Buyurtma berish' },
    removeItemTitle: { ru: 'Удаление товара', uz: 'Mahsulotni o‘chirish' },
    removeItemMessage: { ru: 'Удалить «{name}» из корзины?', uz: '«{name}» savatdan o‘chirilsinmi?' },
    remove: { ru: 'Удалить', uz: 'O‘chirish' },
    cancel: { ru: 'Отмена', uz: 'Bekor qilish' },

    // ─── Checkout form ────────────────────────────────────────────────────
    checkoutTitle: { ru: 'Оформление', uz: 'Rasmiylashtirish' },
    payCard: { ru: 'Картой', uz: 'Karta orqali' },
    payCash: { ru: 'Наличными', uz: 'Naqd pul' },
    rentalPeriod: { ru: 'Период аренды', uz: 'Ijara muddati' },
    pickupAddressLabel: { ru: 'Адрес выдачи', uz: 'Berish manzili' },
    namePlaceholder: { ru: 'Имя', uz: 'Ism' },
    paymentPlaceholder: { ru: 'Способ оплаты', uz: 'To‘lov usuli' },
    commentPlaceholder: { ru: 'Комментарий к заказу...', uz: 'Buyurtmaga izoh...' },
    depositPassport: { ru: 'В залог — Паспорт', uz: 'Garov sifatida — Pasport' },
    useCoinsLabel: { ru: 'Списать {amount} баллов', uz: '{amount} ball yechish' },

    // ─── Order success dialog ─────────────────────────────────────────────
    orderAcceptedTitle: { ru: '⏳ Заявка принята', uz: '⏳ Ariza qabul qilindi' },
    orderAcceptedBody: {
        ru: 'Бронь ещё не подтверждена. Мы отправили вам в Telegram-бот реквизиты для предоплаты — переведите её и пришлите боту чек из банковского приложения. После проверки чека мы подтвердим вашу бронь.',
        uz: 'Bron hali tasdiqlanmagan. Oldindan to‘lov rekvizitlarini Telegram-botga yubordik — to‘lovni amalga oshiring va bank ilovasidan chekni botga yuboring. Chek tekshirilgach, bronni tasdiqlaymiz.',
    },
    sendReceiptToBot: { ru: 'Отправить чек боту', uz: 'Chekni botga yuborish' },
    later: { ru: 'Позже', uz: 'Keyinroq' },

    // ─── Profile ──────────────────────────────────────────────────────────
    profileTitle: { ru: 'Профиль', uz: 'Profil' },
    userFallback: { ru: 'Пользователь', uz: 'Foydalanuvchi' },
    usernameHidden: { ru: 'Юзернейм скрыт', uz: 'Foydalanuvchi nomi yashirilgan' },
    coinsBalance: { ru: '🎁 Баллов: {amount}', uz: '🎁 Ballar: {amount}' },
    orderHistory: { ru: 'История заказов', uz: 'Buyurtmalar tarixi' },
    noOrders: { ru: 'У вас пока нет заказов', uz: 'Sizda hozircha buyurtma yo‘q' },
    orderNumber: { ru: 'Заказ №{id}', uz: '№{id} buyurtma' },
    period: { ru: 'Период', uz: 'Muddat' },
    productFallback: { ru: 'Товар #{id}', uz: '#{id} mahsulot' },
    paymentMethod: { ru: 'Способ оплаты', uz: 'To‘lov usuli' },
    totalSum: { ru: 'Итоговая сумма', uz: 'Umumiy summa' },
    addressLabel: { ru: 'Адрес', uz: 'Manzil' },
    cancelOrder: { ru: 'Отменить заказ', uz: 'Buyurtmani bekor qilish' },
    cancelOrderTitle: { ru: 'Отменить заказ?', uz: 'Buyurtma bekor qilinsinmi?' },
    cancelOrderMessage: {
        ru: 'Вы уверены, что хотите отменить этот заказ? Это действие нельзя отменить.',
        uz: 'Buyurtmani bekor qilmoqchimisiz? Bu amalni ortga qaytarib bo‘lmaydi.',
    },
    cancelOrderConfirm: { ru: 'Да, отменить', uz: 'Ha, bekor qilish' },
    logout: { ru: 'Выйти из аккаунта', uz: 'Hisobdan chiqish' },
    dateUnknown: { ru: 'Дата неизвестна', uz: 'Sana noma’lum' },
    language: { ru: 'Язык', uz: 'Til' },

    // Order status labels (client-facing)
    status_created: { ru: 'В процессе', uz: 'Jarayonda' },
    status_in_progress: { ru: 'Одобрен', uz: 'Tasdiqlandi' },
    status_taken: { ru: 'У клиента', uz: 'Mijozda' },
    status_paused: { ru: 'Одобрен', uz: 'Tasdiqlandi' },
    status_returned: { ru: 'Завершён', uz: 'Yakunlandi' },
    status_completed: { ru: 'Закрыт', uz: 'Yopilgan' },
    status_canceled: { ru: 'Отменён', uz: 'Bekor qilindi' },

    // ─── Validation / error toasts ────────────────────────────────────────
    requiredField: { ru: 'Обязательное поле', uz: 'Majburiy maydon' },
    fillRequired: { ru: 'Заполните обязательные поля', uz: 'Majburiy maydonlarni to‘ldiring' },
    invalidPhone: { ru: 'Некорректный номер телефона', uz: 'Telefon raqami noto‘g‘ri' },
    fixFieldErrors: { ru: 'Исправьте ошибки в полях', uz: 'Maydonlardagi xatolarni tuzating' },
    invalidBasket: { ru: 'Некорректная корзина', uz: 'Savat noto‘g‘ri' },
    orderCreateError: { ru: 'Ошибка при оформлении заказа', uz: 'Buyurtma berishda xatolik' },
    basketUpdateError: { ru: 'Ошибка обновления корзины', uz: 'Savatni yangilashda xatolik' },
    basketAddError: { ru: 'Ошибка добавления в корзину', uz: 'Savatga qo‘shishda xatolik' },
    basketQtyError: { ru: 'Ошибка изменения количества', uz: 'Miqdorni o‘zgartirishda xatolik' },
    basketRemoveError: { ru: 'Ошибка удаления товара', uz: 'Mahsulotni o‘chirishda xatolik' },
    basketRecalcError: { ru: 'Ошибка пересчета корзины при смене дат', uz: 'Sanalar o‘zgarganda savatni qayta hisoblashda xatolik' },
    maxQty99: { ru: 'Максимальное количество товара — 99', uz: 'Mahsulotning maksimal miqdori — 99' },
    dateInvalid: { ru: 'Проверьте корректность даты и времени аренды', uz: 'Ijara sana va vaqtini tekshiring' },
    startInPast: { ru: 'Начало аренды не может быть в прошлом', uz: 'Ijara boshlanishi o‘tmishda bo‘lishi mumkin emas' },
    returnBeforePickup: { ru: 'Время возврата должно быть позже времени получения', uz: 'Qaytarish vaqti olish vaqtidan keyin bo‘lishi kerak' },

    // ─── App gate (non-Telegram) ──────────────────────────────────────────
    telegramOnlyTitle: { ru: 'Доступно в Telegram', uz: 'Telegramda mavjud' },
    telegramOnlyBody: {
        ru: 'Приложение работает внутри Telegram. Откройте нашего бота, чтобы оформить аренду.',
        uz: 'Ilova Telegram ichida ishlaydi. Ijara rasmiylashtirish uchun botimizni oching.',
    },
    openInTelegram: { ru: 'Открыть в Telegram', uz: 'Telegramda ochish' },

    // ─── Banned account ────────────────────────────────────────────────────
    // Short label only — the actionable "contact the manager" text is pushed to
    // the client in the bot at block time, not shown here.
    userBanned: { ru: 'Пользователь заблокирован', uz: 'Foydalanuvchi bloklangan' },
}
