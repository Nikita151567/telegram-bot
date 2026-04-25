import os
import threading
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from sympy import symbols, Eq, solve, sympify, factor, expand, Rational, sqrt, simplify

# --- WEB СЕРВЕР ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Bot is alive!"

def run_web():
    web_app.run(host='0.0.0.0', port=10000)

threading.Thread(target=run_web, daemon=True).start()
# ------------------

x = symbols('x')

def solve_linear_steps(left_expr, right_expr):
    """Шаги для линейного уравнения ax + b = c"""
    steps = []
    steps.append(f"📋 *Уравнение:* `{left_expr} = {right_expr}`")

    # Перенос всего влево: left - right = 0
    moved = sympify(left_expr) - sympify(right_expr)
    expanded = expand(moved)
    steps.append(f"➡️ *Переносим всё влево:*\n`{expanded} = 0`")

    # Коэффициенты
    a = expanded.coeff(x, 1)
    b = expanded.coeff(x, 0)

    if a == 0:
        return steps, None  # не линейное

    steps.append(f"🔍 *Коэффициенты:*\n  a = {a}, b = {b}")

    if b != 0:
        steps.append(f"➡️ *Переносим {b} вправо:*\n`{a}x = {-b}`")

    steps.append(f"➡️ *Делим обе части на {a}:*\n`x = {-b}/{a} = {Rational(-b, a)}`")

    sol = Rational(-b, a)
    steps.append(f"✅ *Ответ: x = {sol}*")
    return steps, sol

def solve_quadratic_steps(left_expr, right_expr):
    """Шаги для квадратного уравнения"""
    steps = []
    steps.append(f"📋 *Уравнение:* `{left_expr} = {right_expr}`")

    moved = expand(sympify(left_expr) - sympify(right_expr))
    steps.append(f"➡️ *Переносим всё влево:*\n`{moved} = 0`")

    a = moved.coeff(x, 2)
    b = moved.coeff(x, 1)
    c = moved.coeff(x, 0)

    steps.append(f"🔍 *Коэффициенты:*\n  a = {a}, b = {b}, c = {c}")

    D = b**2 - 4*a*c
    steps.append(f"📐 *Дискриминант:*\n  D = b² - 4ac = {b}² - 4·{a}·{c} = {b**2} - {4*a*c} = {D}")

    if D < 0:
        steps.append("❌ *D < 0 — действительных корней нет*")
        return steps, []
    elif D == 0:
        x1 = Rational(-b, 2*a)
        steps.append(f"✅ *D = 0 — один корень:*\n  x = -b / 2a = {-b} / {2*a} = {x1}")
        return steps, [x1]
    else:
        steps.append(f"✅ *D > 0 — два корня:*")
        x1 = (-b + sqrt(D)) / (2*a)
        x2 = (-b - sqrt(D)) / (2*a)
        x1s = simplify(x1)
        x2s = simplify(x2)
        steps.append(
            f"  x₁ = (-b + √D) / 2a = ({-b} + √{D}) / {2*a} = {x1s}\n"
            f"  x₂ = (-b - √D) / 2a = ({-b} - √{D}) / {2*a} = {x2s}"
        )
        return steps, [x1s, x2s]

def calc_steps(text):
    """Шаги для обычного вычисления"""
    expr = sympify(text)
    steps = []
    steps.append(f"📋 *Выражение:* `{text}`")

    # Показываем упрощённый вид если отличается
    expanded = expand(expr)
    if str(expanded) != str(expr):
        steps.append(f"➡️ *Раскрываем скобки:* `{expanded}`")

    result = expr.evalf()
    # Если результат целый — показываем как целое
    if result == int(result):
        result = int(result)
    else:
        result = float(round(float(result), 6))

    steps.append(f"➡️ *Вычисляем:* `{result}`")
    steps.append(f"✅ *Ответ: {result}*")
    return steps, result

async def calc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        text = " ".join(context.args).replace(" ", "")
        if not text:
            await update.message.reply_text(
                "📐 *Калькулятор*\n\n"
                "Примеры:\n"
                "`/calc 5*5`\n"
                "`/calc (5/2)/(2/5)`\n"
                "`/calc 2*x+3=7`\n"
                "`/calc x**2-5*x+6=0`",
                parse_mode="Markdown"
            )
            return

        if "=" in text:
            left, right = text.split("=", 1)
            left_expr = sympify(left)
            right_expr = sympify(right)
            moved = expand(left_expr - right_expr)

            a2 = moved.coeff(x, 2)
            a1 = moved.coeff(x, 1)

            if a2 != 0:
                # Квадратное уравнение
                steps, solutions = solve_quadratic_steps(left, right)
            elif a1 != 0:
                # Линейное уравнение
                steps, solutions = solve_linear_steps(left, right)
            else:
                # Другое — общий solve
                eq = Eq(left_expr, right_expr)
                sol = solve(eq, x)
                steps = [f"📋 *Уравнение:* `{left} = {right}`"]
                steps.append(f"✅ *Ответ: x = {sol}*")
                solutions = sol

            await update.message.reply_text(
                "\n\n".join(steps),
                parse_mode="Markdown"
            )
        else:
            steps, result = calc_steps(text)
            await update.message.reply_text(
                "\n\n".join(steps),
                parse_mode="Markdown"
            )

    except Exception as e:
        await update.message.reply_text(
            "😅 Ошибка! Проверь формат.\n\n"
            "Примеры:\n"
            "`/calc 2*x+3=7`\n"
            "`/calc x**2-5*x+6=0`\n"
            "`/calc 5/2+3`",
            parse_mode="Markdown"
        )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я математический бот.\n\n"
        "Команды:\n"
        "/calc — решить пример или уравнение с шагами\n"
        "/help — помощь"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Помощь*\n\n"
        "*Примеры:*\n"
        "`/calc 5*5` → покажет шаги вычисления\n"
        "`/calc 10/4` → покажет шаги\n"
        "`/calc 2*x+3=7` → линейное уравнение с шагами\n"
        "`/calc x**2-5*x+6=0` → квадратное с дискриминантом\n"
        "`/calc x**2=9` → x = ±3 с шагами",
        parse_mode="Markdown"
    )

def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN не задан!")
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("calc", calc))
    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
