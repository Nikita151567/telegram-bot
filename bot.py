import os
import threading
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from sympy import symbols, Eq, solve, sympify, expand, Rational, sqrt, simplify, im

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
user_vars = {}

def fmt(val):
    try:
        v = complex(val.evalf())
    except Exception:
        return str(val)
    real = round(v.real, 4)
    imag = round(v.imag, 4)
    if abs(imag) < 1e-9:
        return str(int(real)) if real == int(real) else str(real)
    elif abs(real) < 1e-9:
        i = round(abs(imag), 2)
        i_str = str(int(i)) if i == int(i) else str(i)
        return f"{i_str}i"
    else:
        r_str = str(int(real)) if real == int(real) else str(round(real, 2))
        i_str = str(int(abs(imag))) if abs(imag) == int(abs(imag)) else str(round(abs(imag), 2))
        sign = "+" if imag > 0 else "-"
        return f"{r_str}{sign}{i_str}i"

def preprocess(text):
    """Заменяем математические символы на sympy-совместимые"""
    return text.replace("√", "sqrt").replace("^", "**")

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
    steps.append(f"➡️ *Делим обе части на {a}:*\n`x = {-b}/{a} = {fmt(sol)}`")
    steps.append(f"✅ *Ответ: x = {fmt(sol)}*")
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
        x1 = simplify((-b + sqrt(D)) / (2*a))
        x2 = simplify((-b - sqrt(D)) / (2*a))
        v1 = complex(x1.evalf())
        v2 = complex(x2.evalf())
        if abs(v1.real) < 1e-9 and abs(v2.real) < 1e-9 and abs(abs(v1.imag) - abs(v2.imag)) < 1e-9:
            i_val = round(abs(v1.imag), 2)
            i_str = str(int(i_val)) if i_val == int(i_val) else str(i_val)
            steps.append(
                f"❌ *D < 0 — действительных корней нет*\n\n"
                f"🔢 *Комплексные корни:*\n"
                f"  x = ±{i_str}i"
            )
        else:
            steps.append(
                f"❌ *D < 0 — действительных корней нет*\n\n"
                f"🔢 *Комплексные корни:*\n"
                f"  x₁ = {fmt(x1)}\n"
                f"  x₂ = {fmt(x2)}"
            )
        return steps, [x1, x2]
    elif D == 0:
        x1 = simplify((-b + sqrt(D)) / (2*a))
        steps.append(
            f"✅ *D = 0 — один корень:*\n"
            f"  x = -b / 2a = {-b} / {2*a} = {fmt(x1)}"
        )
        return steps, [x1]
    else:
        x1 = simplify((-b + sqrt(D)) / (2*a))
        x2 = simplify((-b - sqrt(D)) / (2*a))
        v1 = complex(x1.evalf())
        v2 = complex(x2.evalf())
        if abs(v1.real + v2.real) < 1e-9 and abs(v1.imag) < 1e-9:
            steps.append(
                f"✅ *D > 0 — два корня:*\n"
                f"  x = ±{fmt(x1)}"
            )
        else:
            steps.append(
                f"✅ *D > 0 — два корня:*\n"
                f"  x₁ = (-b + √D) / 2a = ({-b} + √{D}) / {2*a} = {fmt(x1)}\n"
                f"  x₂ = (-b - √D) / 2a = ({-b} - √{D}) / {2*a} = {fmt(x2)}"
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

async def setvar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text(
            "📦 *Использование:*\n"
            "`/setvar y=2` — задать переменную\n"
            "`/setvar y=2 z=5` — несколько переменных\n"
            "`/unsetvar` — сбросить все переменные",
            parse_mode="Markdown"
        )
        return
    text = preprocess(" ".join(context.args))
    user_vars[user_id] = {}
    assigned = []
    for part in text.split():
        if "=" in part:
            var, val = part.split("=", 1)
            var = var.strip()
            val = val.strip()
            try:
                user_vars[user_id][var] = sympify(val)
                assigned.append(f"{var} = {val}")
            except Exception:
                await update.message.reply_text(f"😅 Не удалось распознать: `{part}`", parse_mode="Markdown")
                return
        else:
            await update.message.reply_text(
                f"😅 Неверный формат: `{part}`\n\nПример: `/setvar y=2`",
                parse_mode="Markdown"
            )
            return
    lines = "\n".join(f"  {a}" for a in assigned)
    await update.message.reply_text(
        f"✅ *Сохранено:*\n{lines}",
        parse_mode="Markdown"
    )

async def unsetvar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_vars and user_vars[user_id]:
        old = ", ".join(f"{k}={v}" for k, v in user_vars[user_id].items())
        user_vars.pop(user_id)
        await update.message.reply_text(
            f"🗑️ *Переменные сброшены:*\n  {old}",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("ℹ️ Нет сохранённых переменных.")

async def calc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        text = preprocess(" ".join(context.args).replace(" ", ""))
        if not text:
            await update.message.reply_text(
                "📐 *Калькулятор*\n\n"
                "Примеры:\n"
                "`/calc 5*5`\n"
                "`/calc √25`\n"
                "`/calc 2*x+3=7`\n"
                "`/calc x**2-5*x+6=0`\n"
                "`/calc x*x/(24+9)+√25`",
                parse_mode="Markdown"
            )
            return
        saved = user_vars.pop(user_id, {})
        if "=" in text:
            left, right = text.split("=", 1)
            left_sym = sympify(left).subs(saved)
            right_sym = sympify(right).subs(saved)
            moved = expand(left_sym - right_sym)
            sub_note = ""
            if saved:
                sub_note = ", ".join(f"{k}={v}" for k, v in saved.items())
            a2 = moved.coeff(x, 2)
            a1 = moved.coeff(x, 1)
            if a2 != 0:
                steps, solutions = solve_quadratic_steps(str(left_sym), str(right_sym))
            elif a1 != 0:
                steps, solutions = solve_linear_steps(str(left_sym), str(right_sym))
            else:
                eq = Eq(left_sym, right_sym)
                free_vars = eq.free_symbols
                steps = [f"📋 *Уравнение:* `{left} = {right}`"]
                if sub_note:
                    steps.append(f"🔧 *Подставлено:* {sub_note}")
                if len(free_vars) > 1:
                    raw = solve(eq, x)
                    if raw:
                        steps.append("🔍 *Несколько переменных, решаем относительно x:*")
                        for i, s in enumerate(raw):
                            sub = '₁₂₃₄'[i] if len(raw) > 1 else ''
                            steps.append(f"  x{sub} = {s}")
                    else:
                        steps.append("❌ *Не удалось решить относительно x*")
                    solutions = raw if raw else []
                else:
                    raw = solve(eq, x)
                    real_sols = [s for s in raw if im(s) == 0]
                    if real_sols:
                        steps.append(f"✅ *Ответ: x = {', '.join(fmt(s) for s in real_sols)}*")
                    else:
                        steps.append("❌ *Действительных корней нет*")
                    solutions = real_sols
            if sub_note and (a2 != 0 or a1 != 0):
                steps.insert(1, f"🔧 *Подставлено:* {sub_note}")
            await update.message.reply_text(
                "\n\n".join(steps),
                parse_mode="Markdown"
            )
        else:
            expr_sym = sympify(text).subs(saved)
            steps, result = calc_steps(str(expr_sym))
            await update.message.reply_text(
                "\n\n".join(steps),
                parse_mode="Markdown"
            )
    except Exception:
        await update.message.reply_text(
            "😅 Ошибка! Проверь формат.\n\n"
            "Примеры:\n"
            "`/calc 2*x+3=7`\n"
            "`/calc √25`\n"
            "`/calc x*x/(24+9)+√25`",
            parse_mode="Markdown"
        )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я математический бот.\n\n"
        "Команды:\n"
        "/calc — решить пример или уравнение с шагами\n"
        "/setvar — задать переменные\n"
        "/unsetvar — сбросить переменные\n"
        "/help — помощь"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Помощь*\n\n"
        "*Обычные примеры:*\n"
        "`/calc 5*5` → 25\n"
        "`/calc √25` → 5\n"
        "`/calc 10/4` → 2.5\n\n"
        "*Уравнения:*\n"
        "`/calc 2*x+3=7` → x = 2\n"
        "`/calc x**2-5*x+6=0` → x = 2, 3\n"
        "`/calc x**2=9` → x = ±3\n\n"
        "*Переменные:*\n"
        "`/setvar y=2` → потом `/calc x**3/y=10`\n"
        "`/unsetvar` — сбросить переменные",
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
    app.add_handler(CommandHandler("setvar", setvar))
    app.add_handler(CommandHandler("unsetvar", unsetvar))
    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
