"""Telegram UI text content for Blue Psychology Test Bot."""

# Constants
MAX_MESSAGE_LENGTH = 4000
MAX_CAPTION_LENGTH = 1000
CHUNK_DELAY = 0.6

# Welcome messages
WELCOME_INTRO = (
    "سلام رفیق! \nمن **نورون** ام 🧠 \n"
    "یه هوش مصنوعی روانشناس که اومدم بهت کمک کنم خودتو بهتر بشناسی!\n"
    "اینجا میتونیم با هم گپ بزنیم و با تستهای باحال، یه سفر جذاب به دنیای درونت داشته باشیم.\n"
    "خیلی هم خوش اومدی! 😉\n\n"
    "خب، از کجا شروع کنیم؟ 👇"
)
WELCOME_KEYBOARD_HINT = "بزن بریم برا سفر به دنیای درونت 🍃"
TEST_SELECTION_CAPTION = "."

# Profile section
PROFILE_INTRO = (
    "🧑💼 *پروفایل من*\n\n"
    "در این بخش میتوانید به نتایج تستهای قبلی خود دسترسی داشته باشید یا وضعیت کیف پول خود را مشاهده و شارژ کنید."
)
NO_PREVIOUS_TESTS = "🚫 هنوز هیچ آزمونی انجام ندادهاید."
PREVIOUS_TESTS_TITLE = "📚 نتایج آزمونهای شما:"

# Wallet section
WALLET_BALANCE = "💰 موجودی کیف پول شما: {balance}هزار تومان"
CHARGE_WALLET_INSTRUCTIONS = (
    "🚧 برای شارژ کیف پول، لطفاً به لینک زیر مراجعه کنید:\n"
    "https://zarinp.al/amir_zolfi\n\n"
    "لطفاً مبلغ مورد نظر رو واریز کرده و اسکرینشات نتیجه پرداخت را در زیر بفرستید."
)
PAYMENT_RECEIVED = "📥 اسکرینشات دریافت شد. کیف پول شما پس از بررسی ظرف چند دقیقه شارژ خواهد شد."

# Test flow
ASK_NAME_AGE = (
    "🤝 <b>سلام! خوشحالم که تصمیم گرفتی این آزمون رو با من، انجام بدی.</b>\n\n"
    "برای شروع، لطفاً <b>نام و سن</b> خودت رو برام بنویس تا بتونم بهتر باهات ارتباط برقرار کنم.\n\n"
)
ASK_USER_INFO = (
    "عالی! 👏\n\n"
    "حالا لطفاً **چند خط در مورد خودت** بنویس. این اطلاعات به هوش مصنوعی کمک میکنه تا با تحلیل دقیق شما یک گزارش کامل و شخصیسازیشده بهت بده:\n\n"
    "• شغل یا تحصیلاتت\n• علاقهمندیهات\n• موقعیت زندگی فعلیت\n• هر نکته مهم دیگهای که دوست داری در نظر گرفته بشه\n\n"
    "*هرچی بیشتر بنویسی، نتیجه دقیقتر میشه! 🎯*"
)
INVALID_AGE = "❌ سن باید عدد باشد. لطفاً فقط عدد وارد کنید:"
TEST_PURCHASED = " تست با موفقیت خریداری شد! ✅\n 🚀 بزن بریم برای شروع! "
INSUFFICIENT_BALANCE = (
    "⚠️ موجودی کیف پول شما کافی نیست!\n\n"
    "موجودی فعلی: {balance} هزار تومان\nهزینه تست: {price} هزار تومان\n\n"
    "لطفاً ابتدا کیف پول خود را شارژ کنید."
)
TEST_START_INTRO = (
    "🎉 آماده شروع «{test_name}» هستی؟ 🎉\n\n"
    "🧮 {question_count} سوال  ⏰ {estimated_time}\n"
    "🎯 هدف: _{outcome}_\n✨ _{usage}_\n\n✍️ بیا شروع کنیم!"
)
ANALYZING_ANSWER = "⏳ نورون داره جواب شمارو آنالیز میکنه ... 🧠"

# Test completion
PROCESSING_MESSAGES = [
    "🔍 دارم الگوهای پاسخهات رو بررسی میکنم...",
    "🧠 دارم ویژگیهای روانشناختیت رو شناسایی میکنم...",
    "🖌️ دارم تصویر شخصیتت رو با هوش مصنوعی میسازم ",
    "📝 دارم pdf گزارش نهایی رو آماده میکنم..."
]
REPORT_READY = "🎉 گزارش آمادهست:"
PERSONALITY_IMAGE = "🖌️ تصویر شخصیت شما"
PDF_CAPTION = "📊 نسخه PDF نتایج آزمون شما"
RESULT_NOT_FOUND = "⚠️ نتیجهای برای این شناسه یافت نشد."
RESULT_HEADER = "🎯 نتیجه آزمون:\n{result_text}"
ERROR_GENERATING_RESULT = "⚠️ متأسفانه در تحلیل نتایج خطایی رخ داد. لطفاً با پشتیبانی تماس بگیرید."

# Smart packages
SMART_PACKAGES_INTRO = (
    "🧠 *پکیجهای هوشمند بلو* چیست؟\n\n"
    "هر پکیج شامل چندین تست روانشناسی تخصصی است که باید به ترتیب انجام دهید. "
    "پس از تکمیل همه تستهای هر پکیج، هوش مصنوعی بلو با تحلیل نتایج همه تستها، "
    "یک گزارش جامع و عمیق درباره شخصیت، توانمندیها و مسیر رشد شما ارائه میدهد.\n\n"
    "پکیجها:\n1️⃣ *پکیج خودآگاهی (Self-Aware Package)*\n"
    "2️⃣ *پکیج کسبوکار و شغلی (Business & Career Package)*\n"
    "3️⃣ *پکیج استعدادها و راهنمای مسیر آینده (Talents & Future Guide)*\n\n"
    "یکی از پکیجهای زیر را انتخاب کن:"
)
NO_PACKAGES_PURCHASED = "🚫 شما هنوز هیچ پکیجی خریداری نکردهاید."
PURCHASED_PACKAGES_TITLE = "🧠 پکیجهای خریداری شده شما:"

# Smart therapy
SMART_THERAPY_COMING_SOON = (
    "💬 جلسه هوشمند درمانی با هوش مصنوعی به زودی فعال خواهد شد!\n"
    "در آینده میتوانید با هوش مصنوعی بلو یک جلسه درمانی اختصاصی داشته باشید."
)

# Admin panel
ADMIN_PANEL_TITLE = "🛠️ Admin Panel:"
ADMIN_UNAUTHORIZED = "🚫 You are not authorized to use this command."
ADMIN_NO_USERS = "🚫 No users found."
ADMIN_USERS_LIST_TITLE = "🔍 All users:"
ADMIN_USER_ACTIONS_TITLE = "Actions for {user_id}:"
ADMIN_CHARGE_PROMPT = "🔢 Enter amount to charge user {user_id}:"
ADMIN_REDUCE_PROMPT = "🔢 مقدار کاهش کیف پول کاربر {user_id} را وارد کنید (هزار تومان):"
ADMIN_CHARGE_SUCCESS = (
    "✅ کیف پول کاربر {user_id} با موفقیت به میزان {amount} هزار تومان شارژ شد.\n"
    "موجودی جدید: {balance} هزار تومان."
)
ADMIN_REDUCE_SUCCESS = (
    "✅ از کیف پول کاربر {user_id} با موفقیت مبلغ {amount} هزار تومان کسر شد.\n"
    "موجودی جدید: {balance} هزار تومان."
)
ADMIN_INVALID_AMOUNT = "❌ مبلغ وارد شده نامعتبر است. لطفاً فقط عدد وارد کنید:"
ADMIN_AMOUNT_MUST_BE_POSITIVE = "❌ مبلغ باید یک عدد مثبت باشد. لطفاً دوباره تلاش کنید:"
ADMIN_AMOUNT_EXCEEDS_BALANCE = "❌ مبلغ کاهش ({amount} هزار تومان) بیشتر از موجودی فعلی کاربر ({balance} هزار تومان) است."

# User notifications
USER_WALLET_CHARGED = "🎉 کیف پول شما به مبلغ {amount} هزار تومان شارژ شد.\nموجودی: {balance} هزار تومان"
USER_WALLET_REDUCED = "ℹ️ کیف پول شما به میزان {amount} هزار تومان کاهش یافت.\nموجودی: {balance} هزار تومان"
USER_ADMIN_CHARGED = "🎉 مدیر سیستم کیف پول شما را به میزان {amount} هزار تومان شارژ کرد.\nموجودی جدید شما: {balance} هزار تومان."
USER_ADMIN_REDUCED = "⚠️ مدیر سیستم مبلغ {amount} هزار تومان از کیف پول شما کسر کرد.\nموجودی جدید شما: {balance} هزار تومان."

# Package test completion
PACKAGE_TEST_COMPLETED = "✅ تست با موفقیت تکمیل شد! میتوانید تست بعدی را انتخاب کنید."
PACKAGE_ALL_TESTS_COMPLETED = (
    "🎉 تبریک! شما تمام تستهای پکیج «{package_name}» را تکمیل کردهاید.\n\n"
    "گزارش جامع شما در حال آمادهسازی است..."
)
PACKAGE_TEST_COMPLETED_ALERT = "🔔 ✅ آفرین! تست شما با موفقیت ذخیره شد. برای ادامه، تست بعدی را انتخاب کنید."
PACKAGE_ALL_TESTS_COMPLETED_ALERT = "🔔 🎉 تبریک! شما تمام تستهای پکیج «{package_name}» را با موفقیت به پایان رساندید."

# Templates
TEST_INFO_TEMPLATE = (
    "*🎯 {name}*\n\n💲 *قیمت:* `{price}` *هزار تومان*\n"
    "🧮 *تعداد سوالات:* `{question_count}` عدد\n⏰ *زمان تخمینی:* {time}\n"
    "💡 *هدف و مزایای تست:*\n_{outcome}_\n_{usage}_"
)
PACKAGE_TEST_SELECTION = "📋بزن بریم برای شروع تست ها "
PACKAGE_TEST_ALREADY_COMPLETED = (
    "✅ شما قبلاً تست «{test_name}» را انجام دادهاید.\n"
    "میتوانید تست دیگری را انتخاب کنید یا نتایج قبلی خود را مشاهده کنید."
)
PACKAGE_CARD_WITH_TESTS = """<b>🧠 {name}</b>

<b>💲 قیمت:</b> {price} هزار تومان
<b>🧮 تعداد تستها:</b> {num_tests} عدد
<b>⏰ زمان تخمینی:</b> {time}

<b>📝 توضیحات:</b>
{description}

<b>💡 هدف و مزایا:</b>
{outcome}

<b>🎯 کاربرد:</b>
{usage}

<b>📋 تستهای شامل در این پکیج:</b>
{test_list}"""

# Result formatting
RESULT_HTML_HEADER = "<b>✨ نتایج آزمون {test_name} ✨</b>\n⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n\n"
RESULT_FALLBACK_TEXT = "نتایج آزمون {test_name}:\n\n(نمایش ساده به دلیل خطا در قالببندی)\n{summary}"
RESULT_CHUNK_CONTINUED = "\n\n<i>ادامه دارد...</i>"
RESULT_CHUNK_PART = "<b>بخش {part_num} از {total_parts}</b>\n\n"

# HTML formatting
QUESTION_HTML_FORMAT = "<b>✅ سوال {question_num}/{total_questions}</b>\n{question_text}"
ACKNOWLEDGMENT_HTML_FORMAT = "<b>پاسخ شما:</b> {user_response}\n<i>{acknowledgment}</i>"
RETRY_HTML_FORMAT = "<b>⚠️ لطفاً دوباره تلاش کنید:</b>\n{retry_message}"