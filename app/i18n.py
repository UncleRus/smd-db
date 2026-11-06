"""User-interface translations for SMD-DB.

The catalogue itself is stored in English (part names, descriptions and
function names come straight from the source database). Only the application
chrome — labels, navigation, empty states and the About page — is translated.

Languages: English (``en``), Russian (``ru``) and Simplified Chinese (``zh``).
"""

from __future__ import annotations

DEFAULT_LANG: str = "en"

#: ``(code, label)`` pairs for the language switcher, in display order.
LANGUAGES: tuple[tuple[str, str], ...] = (
    ("en", "EN"),
    ("ru", "RU"),
    ("zh", "中文"),
)

#: Theme identifiers from the bundled elumkit design system.
THEMES: tuple[str, ...] = ("iron", "neon", "dust")
DEFAULT_THEME: str = "iron"

TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "app.title": "SMD-DB",
        "nav.primary": "Primary",
        "nav.skip": "Skip to content",
        "nav.search": "search",
        "nav.about": "about",
        "label.theme": "theme",
        "label.language": "Language",
        # Search form
        "form.aria": "Part search",
        "field.marking": "Marking code",
        "field.name": "Part name",
        "field.function": "Function",
        "field.manufacturer": "Manufacturer",
        "field.package": "Package",
        "field.pins": "Pins / leads",
        "placeholder.pins": "e.g. 8",
        "field.description": "Description",
        "select.any": "Any",
        "select.any.function": "Any",
        "action.search": "Search",
        "action.reset": "Reset",
        "action.back": "Back to results",
        # Results
        "toolbar.aria": "Result actions",
        "results.matches": "matches",
        "results.page": "page",
        "results.aria": "Part search results",
        "sort.label": "Sort",
        "sort.marking": "Marking A\u2192Z",
        "sort.name": "Name A\u2192Z",
        "sort.manufacturer": "Manufacturer",
        "sort.package": "Package",
        "per.label": "Per page",
        "empty.title": "No results",
        "empty.message": "Adjust the conditions and try again.",
        "idle.title": "Start with a marking code",
        "idle.message": "Enter a marking code, or narrow the search by name, function, manufacturer, package or pin count.",
        # Pagination
        "pagination.aria": "Pagination",
        "pagination.prev": "Prev",
        "pagination.next": "Next",
        "pagination.prev_aria": "Previous page",
        "pagination.next_aria": "Next page",
        # Part detail
        "part.actions": "Part actions",
        "part.same_marking": "Same marking code",
        "part.package_pins": "{package} \u00b7 {pins} pins",
        "part.no_image": "No package drawing available",
        # Footer
        "footer.brand": "SMD-DB \u00b7 offline component database",
        "footer.status": "parts {parts} \u00b7 manufacturers {manufacturers} \u00b7 packages {packages} \u00b7 functions {functions}",
        # About
        "about.title": "SMD-DB \u2014 offline SMD component database",
        "about.subtitle": "A local search interface over a SQLite catalogue of surface-mount parts.",
        "about.intro1": (
            "SMD-DB is a read-only web application for identifying surface-mount "
            "components from the marking printed on the package. Enter a marking code, "
            "optionally narrow the result by part name, function, manufacturer, package or "
            "pin count, and open a part to see its full record and package drawing."
        ),
        "about.intro2": (
            "The catalogue lives in a single smd.sqlite file that ships with the "
            "application, so the tool works fully offline and needs no network access."
        ),
        "about.repo": "Source code:",
        "about.catalogue": "Catalogue",
        "about.metric.parts": "Parts",
        "about.metric.markings": "Marking codes",
        "about.metric.manufacturers": "Manufacturers",
        "about.metric.packages": "Packages",
        "about.metric.functions": "Functions",
        "about.fields": "Record fields",
        "about.field.marking": "The code printed on the package \u2014 the primary search key.",
        "about.field.name": "Full manufacturer part number.",
        "about.field.package": "Package outline code, pin count and a package drawing.",
        "about.field.manufacturer": "The company that makes the part.",
        "about.field.function": "Component class, such as diode or voltage regulator IC.",
        "about.field.description": "Key electrical parameters and features.",
        "about.app": "Application",
        "about.app.data": "Database format: SQLite 3, opened read-only",
        "about.app.i18n": "Interface languages: English, Russian, Chinese",
        "about.app.note": "Description text is shown exactly as stored in the source database",
        "about.tag.data": "data",
        "about.tag.i18n": "i18n",
        # Error pages
        "error.title.404": "Page not found",
        "error.title.500": "Server error",
        "error.title.generic": "Error",
        "error.message.404": "The page you requested does not exist.",
        "error.message.500": "The server could not complete the request.",
        "error.message.generic": "The request could not be completed.",
        "error.back": "Back to search",
    },
    "ru": {
        "app.title": "SMD-DB",
        "nav.primary": "Основная навигация",
        "nav.skip": "Перейти к содержимому",
        "nav.search": "поиск",
        "nav.about": "о базе",
        "label.theme": "тема",
        "label.language": "Язык",
        "form.aria": "Поиск деталей",
        "field.marking": "Маркировка",
        "field.name": "Название",
        "field.function": "Функция",
        "field.manufacturer": "Производитель",
        "field.package": "Корпус",
        "field.pins": "Кол-во выводов",
        "placeholder.pins": "напр. 8",
        "field.description": "Описание",
        "select.any": "Любой",
        "select.any.function": "Любая",
        "action.search": "Найти",
        "action.reset": "Сброс",
        "action.back": "К результатам",
        "toolbar.aria": "Действия с результатами",
        "results.matches": "совпадений",
        "results.page": "стр.",
        "results.aria": "Результаты поиска деталей",
        "sort.label": "Сортировка",
        "sort.marking": "Маркировка А\u2192Я",
        "sort.name": "Название А\u2192Я",
        "sort.manufacturer": "Производитель",
        "sort.package": "Корпус",
        "per.label": "На странице",
        "empty.title": "Ничего не найдено",
        "empty.message": "Измените условия поиска и повторите.",
        "idle.title": "Начните с кода маркировки",
        "idle.message": "Введите код маркировки или ограничьте поиск названием, функцией, производителем, корпусом либо числом выводов.",
        "pagination.aria": "Постраничная навигация",
        "pagination.prev": "Предыдущая",
        "pagination.next": "Следующая",
        "pagination.prev_aria": "Предыдущая страница",
        "pagination.next_aria": "Следующая страница",
        "part.actions": "Действия с деталью",
        "part.same_marking": "С тем же кодом маркировки",
        "part.package_pins": "{package} \u00b7 выводов: {pins}",
        "part.no_image": "Чертёж корпуса отсутствует",
        "footer.brand": "SMD-DB \u00b7 оффлайн-база компонентов",
        "footer.status": "деталей {parts} \u00b7 производителей {manufacturers} \u00b7 корпусов {packages} \u00b7 функций {functions}",
        "about.title": "SMD-DB \u2014 оффлайн-база SMD-компонентов",
        "about.subtitle": "Локальный поиск по каталогу компонентов для поверхностного монтажа в формате SQLite.",
        "about.intro1": (
            "SMD-DB \u2014 веб-приложение только для чтения, помогающее опознать компонент "
            "поверхностного монтажа по маркировке на корпусе. Введите код маркировки, при "
            "необходимости ограничьте выборку названием, функцией, производителем, корпусом "
            "или числом выводов и откройте деталь, чтобы увидеть полную карточку и чертёж корпуса."
        ),
        "about.intro2": (
            "Каталог хранится в одном файле smd.sqlite, который поставляется вместе с "
            "приложением, поэтому инструмент работает полностью оффлайн и не требует доступа к сети."
        ),
        "about.repo": "Исходный код:",
        "about.catalogue": "Каталог",
        "about.metric.parts": "Деталей",
        "about.metric.markings": "Кодов маркировки",
        "about.metric.manufacturers": "Производителей",
        "about.metric.packages": "Корпусов",
        "about.metric.functions": "Функций",
        "about.fields": "Поля записи",
        "about.field.marking": "Код, нанесённый на корпус \u2014 основной ключ поиска.",
        "about.field.name": "Полное обозначение детали у производителя.",
        "about.field.package": "Код корпуса, число выводов и чертёж корпуса.",
        "about.field.manufacturer": "Компания-производитель детали.",
        "about.field.function": "Класс компонента, например диод или микросхема стабилизатора.",
        "about.field.description": "Ключевые электрические параметры и особенности.",
        "about.app": "Приложение",
        "about.app.data": "Формат базы: SQLite 3, открытие только для чтения",
        "about.app.i18n": "Языки интерфейса: английский, русский, китайский",
        "about.app.note": "Описание выводится точно так, как хранится в исходной базе",
        "about.tag.data": "данные",
        "about.tag.i18n": "языки",
        "error.title.404": "Страница не найдена",
        "error.title.500": "Ошибка сервера",
        "error.title.generic": "Ошибка",
        "error.message.404": "Запрошенная страница не существует.",
        "error.message.500": "Сервер не смог обработать запрос.",
        "error.message.generic": "Запрос не удалось выполнить.",
        "error.back": "К поиску",
    },
    "zh": {
        "app.title": "SMD-DB",
        "nav.primary": "主导航",
        "nav.skip": "跳到内容",
        "nav.search": "搜索",
        "nav.about": "关于",
        "label.theme": "主题",
        "label.language": "语言",
        "form.aria": "元件搜索",
        "field.marking": "丝印代码",
        "field.name": "型号",
        "field.function": "功能",
        "field.manufacturer": "制造商",
        "field.package": "封装",
        "field.pins": "引脚数",
        "placeholder.pins": "例如 8",
        "field.description": "描述",
        "select.any": "全部",
        "select.any.function": "全部",
        "action.search": "搜索",
        "action.reset": "重置",
        "action.back": "返回结果",
        "toolbar.aria": "结果操作",
        "results.matches": "条匹配",
        "results.page": "页",
        "results.aria": "元件搜索结果",
        "sort.label": "排序",
        "sort.marking": "丝印 A\u2192Z",
        "sort.name": "型号 A\u2192Z",
        "sort.manufacturer": "制造商",
        "sort.package": "封装",
        "per.label": "每页",
        "empty.title": "无结果",
        "empty.message": "请调整条件后重试。",
        "idle.title": "从丝印代码开始",
        "idle.message": "输入丝印代码，或按型号、功能、制造商、封装或引脚数缩小范围。",
        "pagination.aria": "分页",
        "pagination.prev": "上一页",
        "pagination.next": "下一页",
        "pagination.prev_aria": "上一页",
        "pagination.next_aria": "下一页",
        "part.actions": "元件操作",
        "part.same_marking": "相同丝印代码",
        "part.package_pins": "{package} \u00b7 {pins} 引脚",
        "part.no_image": "暂无封装图",
        "footer.brand": "SMD-DB \u00b7 离线元件数据库",
        "footer.status": "元件 {parts} \u00b7 制造商 {manufacturers} \u00b7 封装 {packages} \u00b7 功能 {functions}",
        "about.title": "SMD-DB \u2014 离线 SMD 元件数据库",
        "about.subtitle": "基于 SQLite 元件目录的本地搜索界面。",
        "about.intro1": (
            "SMD-DB 是一个只读 Web 应用，可根据封装上的丝印识别表面贴装元件。输入丝印代码，"
            "可选按型号、功能、制造商、封装或引脚数缩小范围，打开元件即可查看完整记录与封装图。"
        ),
        "about.intro2": (
            "目录存放在随应用一同分发的单个 smd.sqlite 文件中，因此工具可完全离线运行，无需网络访问。"
        ),
        "about.repo": "源代码：",
        "about.catalogue": "目录",
        "about.metric.parts": "元件",
        "about.metric.markings": "丝印代码",
        "about.metric.manufacturers": "制造商",
        "about.metric.packages": "封装",
        "about.metric.functions": "功能",
        "about.fields": "记录字段",
        "about.field.marking": "印在封装上的代码 \u2014 主要搜索键。",
        "about.field.name": "制造商完整型号。",
        "about.field.package": "封装外形代码、引脚数与封装图。",
        "about.field.manufacturer": "生产该元件的公司。",
        "about.field.function": "元件类别，例如二极管或稳压器 IC。",
        "about.field.description": "关键电气参数与特性。",
        "about.app": "应用",
        "about.app.data": "数据库格式：SQLite 3，只读打开",
        "about.app.i18n": "界面语言：英语、俄语、中文",
        "about.app.note": "描述文本按源数据库原样显示",
        "about.tag.data": "数据",
        "about.tag.i18n": "语言",
        "error.title.404": "页面未找到",
        "error.title.500": "服务器错误",
        "error.title.generic": "错误",
        "error.message.404": "请求的页面不存在。",
        "error.message.500": "服务器无法完成该请求。",
        "error.message.generic": "无法完成该请求。",
        "error.back": "返回搜索",
    },
}


def translate(lang: str, key: str, **kwargs: object) -> str:
    """Return the translation of ``key`` for ``lang``.

    Falls back to the default language and then to the key itself so a missing
    translation never raises inside a template.

    Args:
        lang: Requested language code.
        key: Translation key.
        **kwargs: Values substituted into ``str.format`` placeholders.

    Returns:
        The localized string.
    """
    table = TRANSLATIONS.get(lang, {})
    text = table.get(key)
    if text is None:
        text = TRANSLATIONS[DEFAULT_LANG].get(key, key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return text
