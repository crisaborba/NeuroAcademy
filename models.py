from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash


class Row:
    """Generic wrapper around a sqlite3.Row exposing columns as attributes."""

    def __init__(self, row=None, **kwargs):
        data = dict(row) if row is not None else {}
        data.update(kwargs)
        self._data = data
        for k, v in data.items():
            setattr(self, k, v)

    def get(self, key, default=None):
        return self._data.get(key, default)


class User(Row):
    is_authenticated = True
    is_active = True
    is_anonymous = False

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def set_password_hash(self, password):
        self.password_hash = generate_password_hash(password)

    @property
    def initial(self):
        return (self.name or self.username or "?")[0].upper()

    def get_id(self):
        return str(self.id)


class AnonymousUser:
    is_authenticated = False
    is_active = False
    is_anonymous = True
    id = None
    name = ""
    username = ""
    email = ""
    bio = ""
    plan = "Gratuito"
    role = ""
    points = 0
    streak = 0
    email_notifications = 0
    community_notifications = 0
    news_notifications = 0
    marketing_notifications = 0

    @property
    def initial(self):
        return "?"


class Course(Row):
    def __init__(self, row=None, **kwargs):
        super().__init__(row, **kwargs)
        self.modules = []  # filled in by repo layer when needed

    @property
    def img_url(self):
        if self.img and str(self.img).startswith("http"):
            return self.img
        return f"https://images.unsplash.com/{self.img}?w=640&h=360&fit=crop&auto=format"


class Module(Row):
    def __init__(self, row=None, **kwargs):
        super().__init__(row, **kwargs)
        self.lessons = []


class Lesson(Row):
    pass


class Enrollment(Row):
    def __init__(self, row=None, **kwargs):
        super().__init__(row, **kwargs)
        self.course = None


class LessonProgress(Row):
    pass


class Certificate(Row):
    def __init__(self, row=None, **kwargs):
        super().__init__(row, **kwargs)
        self.course = None
        if isinstance(self.get("issued_at"), str):
            try:
                self.issued_at = datetime.strptime(self.issued_at[:19], "%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                self.issued_at = datetime.utcnow()


class BlogPost(Row):
    @property
    def img_url(self):
        return f"https://images.unsplash.com/{self.img}?w=640&h=360&fit=crop&auto=format"


class NewsArticle(Row):
    @property
    def img_url(self):
        return f"https://images.unsplash.com/{self.img}?w=640&h=360&fit=crop&auto=format"


class Tool(Row):
    @property
    def img_url(self):
        return f"https://images.unsplash.com/{self.img}?w=480&h=280&fit=crop&auto=format"

    @property
    def tag_list(self):
        return [t for t in (self.tags or "").split(",") if t]


class CommunityPost(Row):
    def __init__(self, row=None, **kwargs):
        super().__init__(row, **kwargs)
        self.author_user = None
        self.comment_count = 0

    @property
    def tag_list(self):
        return [t for t in (self.tags or "").split(",") if t]


class CommunityComment(Row):
    def __init__(self, row=None, **kwargs):
        super().__init__(row, **kwargs)
        self.author = None


class Roadmap(Row):
    def __init__(self, row=None, **kwargs):
        super().__init__(row, **kwargs)
        self.steps = []


class Achievement(Row):
    RARITY_COLORS = {
        "Comum": "#9AA5B8",
        "Incomum": "#22c55e",
        "Rara": "#4D7EFF",
        "Épica": "#9B59FF",
        "Lendária": "#FF9F4D",
        "Platina": "#00D4FF",
    }

    @property
    def rarity_color(self):
        return self.RARITY_COLORS.get(self.rarity, "#9AA5B8")


class RoadmapStep(Row):
    pass
