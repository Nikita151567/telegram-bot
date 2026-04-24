import os
import threading
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from sympy import symbols, Eq, solve, sympify

# --- WEB СЕРВЕР (чтобы Render не выключал) ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Bot is alive!"

def run_web():
    web_app.run(host='0.0.0.0', port=10000)

threading.Thread(target=run_web, daemon=True).start()
# --------------------------------------------

x = symbols('x')

async def calc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        text = " ".join(context.args).replace(" ", "")
        if not text:
            await update.message.reply_text(
                "📐 *Калькулятор*\n\n"
                "Примеры:\n"
                "`/calc 5*5`\n"
                "`/calc (5/2)/(2/5)`\n"
                "`/calc 2*x+3=7`",
                parse_mode="Markdown"
            )
            return
        if "=" in text:
            left, right = text.split("=", 1)
            eq = Eq(sympify(left), sympify(right))
            sol = solve(eq, x)
            if sol:
                result = sol[0] if len(sol) == 1 else sol
                await update.message.reply_text(f"✅ x = {result}")
            else:
                await update.message.reply_text("❌ Нет решений")
        else:
            result = sympify(text)
            await update.message.reply_text(f"✅ Ответ: {result}")
    except Exception:
        await update.message.reply_text(
            "😅 Ошибка! Проверь формат.\n\n"
            "Примеры:\n"
            "`/calc 2*x+3=7`\n"
            "`/calc 5/2+3`",
            parse_mode="Markdown"
        )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я математический бот.\n\n"
        "Команды:\n"
        "/calc — решить пример или уравнение\n"
        "/help — помощь"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Помощь*\n\n"
        "*Примеры:*\n"
        "`/calc 5*5` → 25\n"
        "`/calc 10/4` → 2.5\n"
        "`/calc (5/2)/(2/5)` → 6.25\n"
        "`/calc 2*x+3=7` → x = 2\n"
        "`/calc x**2=9` → x = ±3",
        parse_mode="Markdown"
    )

def main():
    token = os.environ.get("8716382261:AAGmytsdSxS77Xmys1yJmZIMYasMTzRL9lU")
    if not token:
        raise ValueError("BOT_TOKEN не задан! Добавь его в Environment на Render.")
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("calc", calc))
    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
