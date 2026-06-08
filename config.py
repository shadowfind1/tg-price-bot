import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "8964059495:AAFHS2_p4iMQj4qfcHBjzgAK0YThiNIlb-0")

_BASE = os.path.dirname(os.path.abspath(__file__))

# Страница в PDF (0 = первая)
PRICE_PAGE = 0

# xref тайла с ценой (определяется по размеру 1044x141)
PRICE_TILE_SIZE = (1044, 141)

# Координаты внутри тайла
TILE_NUMBER_X_START = 2     # x где начинается число (выровнено по левому краю "С" сверху)
TILE_TENGE_SEARCH_X = 270   # с какого x искать знак "т" в SMask
TILE_TENGE_GAP      = 41    # пиксельный зазор между числом и "т"

# Цвет текста и фона тайла
TILE_TEXT_COLOR = (50, 138, 71)
TILE_BG_COLOR   = (0, 0, 0)

# Шрифт (Arial Regular + stroke = ~600 weight)
FONT_PATH   = os.path.join(_BASE, "arial.ttf")
FONT_SIZE   = 123        # соответствует высоте цифр 89px в оригинале
FONT_STROKE = 2          # stroke_width для симуляции weight 650
TILE_TEXT_Y_TOP = 23     # y верхнего края цифр в оригинальном тайле

# Тайл с датой (504x50, правый столбец таблицы)
DATE_TILE_SIZE   = (504, 50)
DATE_FONT_PATH   = os.path.join(_BASE, "SF-Pro-Display-Regular.otf")
DATE_FONT_SIZE   = 40
DATE_TEXT_Y_TOP  = 9    # y верхнего края текста даты
DATE_TEXT_X_RIGHT = 500  # x правого края текста (right-aligned)
DATE_TEXT_COLOR  = (31, 31, 31)  # цвет текста (как у номера квитанции)

# Тайл с именем (Анонимно / Жасырын)
ANON_TILE_SIZE   = (300, 57)
ANON_FONT_PATH   = os.path.join(_BASE, "SF-Pro-Display-Regular.otf")
ANON_FONT_SIZE   = 49
ANON_TEXT_COLOR  = (31, 31, 31)
ANON_TEXT_Y_TOP  = 12
ANON_DEFAULT     = "Жасырын"

# Тайл с номером квитанции (504x50, правый столбец, 1-й по y)
RECEIPT_FONT_PATH   = DATE_FONT_PATH   # SF Pro Regular
RECEIPT_FONT_SIZE   = DATE_FONT_SIZE   # 40
RECEIPT_TEXT_COLOR  = DATE_TEXT_COLOR  # (31, 31, 31)
RECEIPT_TEXT_Y_TOP  = DATE_TEXT_Y_TOP  # 9
RECEIPT_TEXT_X_RIGHT = DATE_TEXT_X_RIGHT  # 500
