import os
import threading
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from sympy import symbols, Eq, solve, sympify, factor, expand, Rational, sqrt, simplify, im

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
    steps = []
    steps.append(f"📋 *Уравнение:* `{left_expr} = {right_expr}`")

    moved = expand(sympify(left_expr) - sympify(right_expr))
    steps.append(f"➡️ *Переносим всё влево:*\n`{moved} = 0`")

    a = moved.coeff(x, 1)
    b = moved.coeff(x, 0)

    if a == 0:
        return steps, None

    steps.append(f"🔍 *Коэффициенты:*\n  a = {a}, b = {b}")

    if b != 0:
        steps.append(f"➡️ *Переносим {b} вправо:*\n`{a}x = {-b}`")

    sol = Rational(-b, a)
    steps.append(f"➡️ *Делим обе части на {a}:*\n`x = {-b}/{a} = {sol}`")
    steps.append(f"✅ *Ответ: x = {sol}*")
    return steps, [sol]

def solve_quadratic_steps(left_expr, right_expr):
    steps = []
    steps.append(f"📋 *Уравнение:* `{left_expr} = {right_expr}`")

    moved = expand(sympify(left_expr) - sympify(right_expr))
    steps.append(f"➡️ *Переносим всё влево:*\n`{moved} = 0`")

    a = moved.coeff(x, 2)
    b = moved.coeff(x, 1)
    c = moved.coeff(x, 0)

    steps.append(f"🔍 *Коэффициенты:*\n  a = {a}, b = {b}, c = {c}")

    D = b**2 - 4*a*c
    steps.append(
        f"📐 *Дискриминант:*\n"
        f"  D = b² - 4ac = {b}² - 4·{a}·{c} = {b**2} - {4*a*c} = {D}"
    )

    if D < 0:
        steps.append("❌ *D < 0 — действительных корней нет*")
        return steps, []
    elif D == 0:
        x1 = Rational(-b, 2*a)
        steps.append(
            f"✅ *D = 0 — один корень:*\n"
            f"  x = -b / 2a = {-b} / {2*a} = {x1}"
        )
        return steps, [x1]
    else:
        x1 = simplify((-b + sqrt(D)) / (2*a))
        x2 = simplify((-b - sqrt(D)) / (2*a))
        steps.append(
            f"✅ *D > 0 — два корня:*\n"
            f"  x₁ = (-b + √D) / 2a = ({-b} + √{D}) / {2*a} = {x1}\n"
            f"  x₂ = (-b - √D) / 2a = ({-b} - √{D}) / {2*a} = {x2}"
        )
        return steps, [x1, x2]

def calc_steps(text):
    expr = sympify(text)
    steps = []
    steps.append(f"📋 *Выражение:* `{text}`")

    expanded = expand(expr)
    if str(expanded) != str(expr):
        steps.append(f"➡️ *Раскрываем скобки:* `{expanded}`")

    result = expr.evalf()
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
            left_sym = sympify(left)
            right_sym = sympify(right)
            moved = expand(left_sym - right_sym)

            a2 = moved.coeff(x, 2)
            a1 = moved.coeff(x, 1)

            if a2 != 0:
                steps, solutions = solve_quadratic_steps(left, right)
            elif a1 != 0:
                steps, solutions = solve_linear_steps(left, right)
            else:
                # Другие уравнения
                eq = Eq(left_sym, right_sym)
                raw = solve(eq, x)
                # Фильтруем комплексные корни
                real_sols = [s for s in raw if im(s) == 0]
                steps = [f"📋 *Уравнение:* `{left} = {right}`"]
                if real_sols:
                    steps.append(f"✅ *Ответ: x = {real_sols if len(real_sols) > 1 else real_sols[0]}*")
                else:
                    steps.append("❌ *Действительных корней нет*")
                solutions = real_sols

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

    except Exception:
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
        "`/calc 5*5` → шаги вычисления\n"
        "`/calc 10/4` → шаги\n"
        "`/calc 2*x+3=7` → линейное с шагами\n"
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
