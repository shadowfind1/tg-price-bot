import io
import re
import random
import tempfile
import os
import fitz
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from datetime import datetime, timezone, timedelta
from config import (
    BOT_TOKEN, PRICE_PAGE, PRICE_TILE_SIZE,
    TILE_NUMBER_X_START, TILE_TENGE_SEARCH_X, TILE_TENGE_GAP,
    TILE_TEXT_COLOR, TILE_BG_COLOR, FONT_PATH, FONT_SIZE, FONT_STROKE, TILE_TEXT_Y_TOP,
    DATE_TILE_SIZE, DATE_FONT_PATH, DATE_FONT_SIZE, DATE_TEXT_Y_TOP, DATE_TEXT_X_RIGHT, DATE_TEXT_COLOR,
    ANON_TILE_SIZE, ANON_FONT_PATH, ANON_FONT_SIZE, ANON_TEXT_COLOR, ANON_TEXT_Y_TOP, ANON_DEFAULT,
    RECEIPT_FONT_PATH, RECEIPT_FONT_SIZE, RECEIPT_TEXT_COLOR, RECEIPT_TEXT_Y_TOP, RECEIPT_TEXT_X_RIGHT,
)

_SMASK_RE = re.compile(r'/SMask\s+(\d+)\s+0\s+R')


def almaty_now() -> str:
    """Текущее время Алматы в формате DD.MM.YYYY H:MM"""
    now = datetime.now(timezone(timedelta(hours=5)))
    return f"{now.day:02d}.{now.month:02d}.{now.year} {now.hour}:{now.minute:02d}"


def find_date_tile(doc, page):
    """Возвращает (xref, smask_xref, pil) тайла с датой.
    Дата — 2-й тайл DATE_TILE_SIZE в правом столбце (x>200), отсортированный по y."""
    candidates = []
    for img in page.get_images(full=True):
        xref = img[0]
        base = doc.extract_image(xref)
        pil = Image.open(io.BytesIO(base["image"]))
        if pil.size != DATE_TILE_SIZE:
            continue
        obj = doc.xref_object(xref)
        smask_m = _SMASK_RE.search(obj)
        if not smask_m:
            continue
        rects = page.get_image_rects(xref)
        if not rects or rects[0].x0 < 200:
            continue
        candidates.append((rects[0].y0, xref, int(smask_m.group(1)), pil))
    candidates.sort()
    if len(candidates) >= 2:
        _, xref, smask_xref, pil = candidates[1]
        return xref, smask_xref, pil
    return None, None, None


def extract_receipt_num(filename: str):
    """Берёт самую длинную последовательность цифр из имени файла."""
    sequences = re.findall(r'\d+', filename)
    if not sequences:
        return None
    return max(sequences, key=len)


def find_receipt_tile(doc, page):
    """Возвращает (xref, smask_xref) тайла с номером квитанции —
    1-й правый 504x50 тайл (по y-позиции на странице)."""
    candidates = []
    for img in page.get_images(full=True):
        xref = img[0]
        base = doc.extract_image(xref)
        pil = Image.open(io.BytesIO(base["image"]))
        if pil.size != DATE_TILE_SIZE:
            continue
        obj = doc.xref_object(xref)
        smask_m = _SMASK_RE.search(obj)
        if not smask_m:
            continue
        rects = page.get_image_rects(xref)
        if not rects or rects[0].x0 < 200:
            continue
        candidates.append((rects[0].y0, xref, int(smask_m.group(1))))
    candidates.sort()
    if candidates:
        _, xref, smask_xref = candidates[0]
        return xref, smask_xref
    return None, None


def find_anon_tile(doc, page):
    """Возвращает (xref, smask_xref) тайла с именем (Анонимно)."""
    for img in page.get_images(full=True):
        xref = img[0]
        base = doc.extract_image(xref)
        pil = Image.open(io.BytesIO(base["image"]))
        if pil.size != ANON_TILE_SIZE:
            continue
        obj = doc.xref_object(xref)
        smask_m = _SMASK_RE.search(obj)
        return xref, int(smask_m.group(1)) if smask_m else None
    return None, None


def get_anon_font(text: str) -> ImageFont.FreeTypeFont:
    """Шрифт для имени — уменьшается если текст шире тайла."""
    size = ANON_FONT_SIZE
    max_w = ANON_TILE_SIZE[0] - 5
    while size > 10:
        font = ImageFont.truetype(ANON_FONT_PATH, size)
        bb = font.getbbox(text)
        if bb[2] - bb[0] <= max_w:
            return font
        size -= 1
    return ImageFont.truetype(ANON_FONT_PATH, 10)


def find_price_tile(doc, page):
    for img in page.get_images(full=True):
        xref = img[0]
        base = doc.extract_image(xref)
        pil = Image.open(io.BytesIO(base["image"]))
        if pil.size == PRICE_TILE_SIZE:
            return xref, pil
    return None, None


def find_tenge_metrics(smask_img: Image.Image, search_from_x: int):
    """Return (x0, x1, y0, y1) — pixel bounding box of the tenge glyph in the SMask."""
    arr = np.array(smask_img)
    cols = np.any(arr[:, search_from_x:] > 128, axis=0)
    col_nz = np.where(cols)[0]
    if len(col_nz) == 0:
        return None, None, None, None
    x0 = int(col_nz[0]) + search_from_x
    x1 = int(col_nz[-1]) + search_from_x + 1
    rows = np.any(arr[:, x0:x1] > 128, axis=1)
    row_nz = np.where(rows)[0]
    if len(row_nz) == 0:
        return x0, x1, None, None
    return x0, x1, int(row_nz[0]), int(row_nz[-1]) + 1




def replace_price_in_pdf(input_path: str, output_path: str, new_price: str,
                         new_name: str = None, receipt_num: str = None) -> None:
    if new_name is None:
        new_name = ANON_DEFAULT
    doc = fitz.open(input_path)
    page = doc[PRICE_PAGE]

    xref, tile_pil = find_price_tile(doc, page)
    if xref is None:
        raise ValueError("Тайл с ценой не найден — возможно другой шаблон PDF.")

    smask_match = _SMASK_RE.search(doc.xref_object(xref))
    smask_xref = int(smask_match.group(1)) if smask_match else None

    rgb_img = tile_pil.convert("RGB")

    if smask_xref:
        base_m = doc.extract_image(smask_xref)
        mask_img = Image.open(io.BytesIO(base_m["image"])).convert("L")
    else:
        mask_img = None

    # ── Измеряем реальные размеры знака "т" из SMask ───────
    if mask_img:
        tx0, tx1, ty0, ty1 = find_tenge_metrics(mask_img, TILE_TENGE_SEARCH_X)
    else:
        tx0 = tx1 = ty0 = ty1 = None

    if ty0 is None:
        raise ValueError("Знак 'т' не найден в SMask.")

    tenge_w = tx1 - tx0

    # ── Фиксированный шрифт из оригинала ────────────────────
    font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    bb8 = font.getbbox("8")
    y_pos = TILE_TEXT_Y_TOP - bb8[1]

    # ── Вырезаем "т" из обоих тайлов ───────────────────────
    h = rgb_img.height
    tenge_rgb  = rgb_img.crop((tx0, 0, tx1, h))
    tenge_mask = mask_img.crop((tx0, 0, tx1, h)) if mask_img else None

    # ── Ширина нового числа с учётом stroke ─────────────────
    _tmp = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    measured = _tmp.textbbox((0, 0), new_price, font=font, stroke_width=FONT_STROKE)
    new_text_w = measured[2]
    new_tenge_x = TILE_NUMBER_X_START + new_text_w + TILE_TENGE_GAP

    # ── Область очистки (старая + новая) ────────────────────
    clear_end = max(tx1 + 5, new_tenge_x + tenge_w + 5)

    # ── Редактируем RGB тайл ────────────────────────────────
    d = ImageDraw.Draw(rgb_img)
    d.rectangle([0, 0, clear_end, h], fill=TILE_BG_COLOR)
    d.text((TILE_NUMBER_X_START, y_pos), new_price, fill=TILE_TEXT_COLOR, font=font,
           stroke_width=FONT_STROKE, stroke_fill=TILE_TEXT_COLOR)
    rgb_img.paste(tenge_rgb, (new_tenge_x, 0))
    doc.update_stream(xref, rgb_img.tobytes(), compress=True)

    # ── Редактируем SMask ───────────────────────────────────
    if mask_img and tenge_mask:
        dm = ImageDraw.Draw(mask_img)
        dm.rectangle([0, 0, clear_end, h], fill=0)
        dm.text((TILE_NUMBER_X_START, y_pos), new_price, fill=255, font=font,
                stroke_width=FONT_STROKE, stroke_fill=255)
        mask_img.paste(tenge_mask, (new_tenge_x, 0))
        doc.update_stream(smask_xref, mask_img.tobytes(), compress=True)

    # ── Замена даты ─────────────────────────────────────────
    d_xref, d_smask_xref, _ = find_date_tile(doc, page)
    if d_xref is not None:
        date_str = almaty_now()
        date_font = ImageFont.truetype(DATE_FONT_PATH, DATE_FONT_SIZE)
        bb0 = date_font.getbbox("0")
        d_y_pos = DATE_TEXT_Y_TOP - bb0[1]
        text_bb = date_font.getbbox(date_str)
        d_x_pos = DATE_TEXT_X_RIGHT - text_bb[2]

        # Обновляем RGB тайл (цвет текста)
        d_base = doc.extract_image(d_xref)
        d_rgb = Image.open(io.BytesIO(d_base["image"])).convert("RGB")
        dr = ImageDraw.Draw(d_rgb)
        dr.rectangle([150, 0, DATE_TILE_SIZE[0], DATE_TILE_SIZE[1]], fill=(0, 0, 0))
        dr.text((d_x_pos, d_y_pos), date_str, fill=DATE_TEXT_COLOR, font=date_font)
        doc.update_stream(d_xref, d_rgb.tobytes(), compress=True)

        # Обновляем SMask (видимость пикселей)
        d_smask_data = doc.extract_image(d_smask_xref)
        d_mask = Image.open(io.BytesIO(d_smask_data["image"])).convert("L")
        dm2 = ImageDraw.Draw(d_mask)
        dm2.rectangle([150, 0, DATE_TILE_SIZE[0], DATE_TILE_SIZE[1]], fill=0)
        dm2.text((d_x_pos, d_y_pos), date_str, fill=255, font=date_font)
        doc.update_stream(d_smask_xref, d_mask.tobytes(), compress=True)

    # ── Замена номера квитанции ──────────────────────────────
    if receipt_num:
        r_xref, r_smask_xref = find_receipt_tile(doc, page)
        if r_xref is not None:
            r_font = ImageFont.truetype(RECEIPT_FONT_PATH, RECEIPT_FONT_SIZE)
            r_bb0 = r_font.getbbox("8")
            r_y_pos = RECEIPT_TEXT_Y_TOP - r_bb0[1]
            r_tbb = r_font.getbbox(receipt_num)
            r_x_pos = RECEIPT_TEXT_X_RIGHT - r_tbb[2]

            r_base = doc.extract_image(r_xref)
            r_rgb = Image.open(io.BytesIO(r_base["image"])).convert("RGB")
            rr = ImageDraw.Draw(r_rgb)
            rr.rectangle([0, 0, DATE_TILE_SIZE[0], DATE_TILE_SIZE[1]], fill=(0, 0, 0))
            rr.text((r_x_pos, r_y_pos), receipt_num, fill=RECEIPT_TEXT_COLOR, font=r_font)
            doc.update_stream(r_xref, r_rgb.tobytes(), compress=True)

            if r_smask_xref:
                r_sm_data = doc.extract_image(r_smask_xref)
                r_mask = Image.open(io.BytesIO(r_sm_data["image"])).convert("L")
                rm = ImageDraw.Draw(r_mask)
                rm.rectangle([0, 0, DATE_TILE_SIZE[0], DATE_TILE_SIZE[1]], fill=0)
                rm.text((r_x_pos, r_y_pos), receipt_num, fill=255, font=r_font)
                doc.update_stream(r_smask_xref, r_mask.tobytes(), compress=True)

    # ── Замена имени (Анонимно) ──────────────────────────────
    a_xref, a_smask_xref = find_anon_tile(doc, page)
    if a_xref is not None:
        a_font = get_anon_font(new_name)
        a_bb = a_font.getbbox("А")
        a_y_pos = ANON_TEXT_Y_TOP - a_bb[1]
        a_text_bb = a_font.getbbox(new_name)
        a_x_pos = 0 - a_text_bb[0]  # left-aligned, compensate bearing

        a_base = doc.extract_image(a_xref)
        a_rgb = Image.open(io.BytesIO(a_base["image"])).convert("RGB")
        ar = ImageDraw.Draw(a_rgb)
        ar.rectangle([0, 0, ANON_TILE_SIZE[0], ANON_TILE_SIZE[1]], fill=(0, 0, 0))
        ar.text((a_x_pos, a_y_pos), new_name, fill=ANON_TEXT_COLOR, font=a_font)
        doc.update_stream(a_xref, a_rgb.tobytes(), compress=True)

        if a_smask_xref:
            a_smask_data = doc.extract_image(a_smask_xref)
            a_mask = Image.open(io.BytesIO(a_smask_data["image"])).convert("L")
            am = ImageDraw.Draw(a_mask)
            am.rectangle([0, 0, ANON_TILE_SIZE[0], ANON_TILE_SIZE[1]], fill=0)
            am.text((a_x_pos, a_y_pos), new_name, fill=255, font=a_font)
            doc.update_stream(a_smask_xref, a_mask.tobytes(), compress=True)

    doc.save(output_path)
    doc.close()


def make_filename() -> str:
    digits = str(random.randint(1, 9)) + "".join(str(random.randint(0, 9)) for _ in range(17))
    return f"transfer-receipt_{digits}.pdf"


async def process_pdf(message, file_id: str, new_price: str, new_name: str = None) -> None:
    clean_price = re.sub(r"[\s,]", "", new_price)
    # Генерируем имя один раз — из него же берём номер квитанции
    out_filename = make_filename()
    receipt_num = extract_receipt_num(out_filename)
    await message.reply_text("Обрабатываю...")
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.pdf")
        output_path = os.path.join(tmpdir, "result.pdf")
        tg_file = await message.get_bot().get_file(file_id)
        await tg_file.download_to_drive(input_path)
        try:
            replace_price_in_pdf(input_path, output_path, clean_price, new_name, receipt_num)
        except ValueError as e:
            await message.reply_text(str(e))
            return
        with open(output_path, "rb") as f:
            await message.reply_document(f, filename=out_filename)


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    doc_file = message.document

    if not doc_file or not doc_file.file_name.lower().endswith(".pdf"):
        await message.reply_text("Отправь PDF файл с новой ценой.")
        return

    caption = message.caption or ""
    price_match = re.match(r'\s*(\d[\d\s,.]*)(.*)', caption, re.DOTALL)

    if price_match:
        price_str = price_match.group(1).strip()
        name_str = price_match.group(2).strip() or None
        await process_pdf(message, doc_file.file_id, price_str, name_str)
    else:
        context.user_data["pending_file_id"] = doc_file.file_id
        await message.reply_text("Файл получен. Теперь отправь цену (и имя через пробел, если нужно).\nПример: <b>9500 Иван</b>", parse_mode="HTML")


async def handle_price_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    text = message.text or ""
    price_match = re.match(r'\s*(\d[\d\s,.]*)(.*)', text, re.DOTALL)

    if not price_match:
        await message.reply_text("Не понял цену. Пример: <b>9500</b> или <b>9500 Иван</b>", parse_mode="HTML")
        return

    file_id = context.user_data.pop("pending_file_id", None)
    if not file_id:
        await message.reply_text("Сначала отправь PDF файл.")
        return

    price_str = price_match.group(1).strip()
    name_str = price_match.group(2).strip() or None
    await process_pdf(message, file_id, price_str, name_str)


async def error_handler(update, context):
    from telegram.error import Conflict, TimedOut, NetworkError
    if isinstance(context.error, (TimedOut, NetworkError, Conflict)):
        return
    raise context.error


def kill_existing_instance():
    import signal
    pid_file = os.path.join(os.path.dirname(__file__), "bot.pid")
    if os.path.exists(pid_file):
        try:
            with open(pid_file) as f:
                old_pid = int(f.read().strip())
            os.kill(old_pid, signal.SIGTERM)
            import time; time.sleep(1)
        except (ProcessLookupError, ValueError, OSError):
            pass
        try:
            os.remove(pid_file)
        except OSError:
            pass
    with open(pid_file, "w") as f:
        f.write(str(os.getpid()))


def main():
    import asyncio
    import time
    kill_existing_instance()

    while True:
        try:
            asyncio.set_event_loop(asyncio.new_event_loop())
            app = (
                Application.builder()
                .token(BOT_TOKEN)
                .connect_timeout(60)
                .read_timeout(60)
                .write_timeout(60)
                .pool_timeout(60)
                .build()
            )
            app.add_handler(MessageHandler(filters.Document.PDF, handle_document))
            app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_price_text))
            app.add_error_handler(error_handler)
            print("Бот запущен. Нажми Ctrl+C для остановки.")
            app.run_polling(drop_pending_updates=True)
            break
        except KeyboardInterrupt:
            print("Остановлено.")
            break
        except Exception as e:
            print(f"Ошибка подключения: {e}\nПовтор через 10 секунд...")
            time.sleep(10)


if __name__ == "__main__":
    main()
