import sys
from dataclasses import dataclass

from PyQt5.QtCore import Qt, QCoreApplication
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QStackedWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QTextEdit,
    QProgressBar,
    QScrollArea,
    QFileDialog,
    QFrame,
    QSizePolicy,
)


# ============================================================
#  APP STATE
# ============================================================

@dataclass
class AppState:
    # Login + user info
    current_username: str = ""
    current_company: str = ""
    current_role: str = "consumer"  # "business" or "consumer"

    # AI usage
    max_prompts_per_day: int = 8
    prompts_used_today: int = 0
    current_asi: float = 100.0
    prompt_limit_message: str = ""
    asi_interpretation: str = "Using AI sparingly today."

    # Sustainability index
    selected_image_path: str = ""
    selected_image_name: str = "No image selected"
    last_index_score: float = 0.0
    index_daily_limit: int = 1
    index_uses_today: int = 0
    index_limit_message: str = ""
    index_title: str = ""
    index_subtitle: str = ""
    index_form_label: str = ""
    index_materials_hint: str = ""
    index_tech_hint: str = ""
    index_score_line: str = "No score computed yet."
    index_score_interpretation: str = ""
    index_usage_limit_description: str = ""

    # Dashboard
    dashboard_subtitle: str = ""
    sustain_box_title: str = ""
    sustain_box_description: str = ""
    sustain_score_line: str = ""
    daily_tip: str = "Try solving a task manually first, then refine with AI."
    forum_highlight: str = "“How many prompts per day feels right?”"

    # News + forum
    news_items: list = None
    forum_threads: list = None

    def __post_init__(self):
        if self.news_items is None:
            self.news_items = [
                {
                    "title": "Data centers reduce water usage",
                    "summary": "Closed-loop cooling systems cut water consumption for AI workloads.",
                    "source": "EcoTech Journal",
                },
                {
                    "title": "Governments consider AI efficiency subsidies",
                    "summary": "Tax incentives for low-token AI workflows are being evaluated.",
                    "source": "PolicyWatch",
                },
            ]
        if self.forum_threads is None:
            self.forum_threads = []

    @property
    def current_user_label(self) -> str:
        base = self.current_username or "Guest"
        return f"{base} ({self.current_role.capitalize()})"


# ============================================================
#  REUSABLE WIDGETS
# ============================================================

class CardFrame(QFrame):
    def __init__(self, parent=None, vertical_expanding=True):
        super().__init__(parent)
        self.setProperty("card", True)
        self.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding if vertical_expanding else QSizePolicy.Preferred,
        )


class SustainTopBar(QWidget):
    def __init__(self, app_state: AppState, get_context_title, parent=None):
        super().__init__(parent)
        self.app_state = app_state
        self.get_context_title = get_context_title

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(12)

        self.app_title_label = QLabel("sustAIn")
        self.app_title_label.setStyleSheet("font-size: 16pt; font-weight: bold;")
        layout.addWidget(self.app_title_label)

        self.context_title_label = QLabel("")
        self.context_title_label.setStyleSheet("color: #555555; font-size: 11pt;")
        layout.addWidget(self.context_title_label, 1)

        layout.addStretch(1)

        self.user_label_btn = QPushButton(self.app_state.current_user_label)
        self.user_label_btn.setFixedWidth(240)
        layout.addWidget(self.user_label_btn)

    def refresh(self):
        self.context_title_label.setText(self.get_context_title())
        self.user_label_btn.setText(self.app_state.current_user_label)


class SustainSideNav(QWidget):
    def __init__(self, on_nav_clicked, on_switch_role, on_logout, parent=None):
        super().__init__(parent)
        self.on_nav_clicked = on_nav_clicked
        self.on_switch_role = on_switch_role
        self.on_logout = on_logout

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        title = QLabel("<b>Navigation</b>")
        layout.addWidget(title)

        def add_btn(text, target):
            btn = QPushButton(text)
            btn.clicked.connect(lambda: self.on_nav_clicked(target))
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            layout.addWidget(btn)

        add_btn("Dashboard", "dashboard")
        add_btn("AI Usage & ASI", "ai_usage")
        add_btn("Product / Waste Index", "sustain_index")
        add_btn("News", "news")
        add_btn("Forum", "forum")
        add_btn("Settings", "settings")

        layout.addStretch(1)

        switch_role_btn = QPushButton("Switch Role")
        switch_role_btn.clicked.connect(self.on_switch_role)
        layout.addWidget(switch_role_btn)

        logout_btn = QPushButton("Logout")
        logout_btn.clicked.connect(self.on_logout)
        layout.addWidget(logout_btn)


class NewsItemWidget(CardFrame):
    def __init__(self, title, summary, source, parent=None):
        super().__init__(parent, vertical_expanding=False)
        layout = QVBoxLayout(self)
        layout.setSpacing(4)

        t = QLabel(f"<b>{title}</b>")
        s = QLabel(summary)
        s.setWordWrap(True)
        src = QLabel(f"Source: {source}")
        src.setStyleSheet("font-size: 9pt; color: #666666;")

        layout.addWidget(t)
        layout.addWidget(s)
        layout.addWidget(src)


class ForumThreadItemWidget(CardFrame):
    def __init__(self, title, author, body, parent=None):
        super().__init__(parent, vertical_expanding=False)
        layout = QVBoxLayout(self)
        layout.setSpacing(4)

        t = QLabel(f"<b>{title}</b>")
        a = QLabel(f"By {author}")
        a.setStyleSheet("font-size: 9pt; color: #666666;")
        b = QLabel(body)
        b.setWordWrap(True)


        layout.addWidget(t)
        layout.addWidget(a)
        layout.addWidget(b)


# ============================================================
#  INNER MAIN SCREENS (CENTER PANEL)
# ============================================================

class DashboardScreen(QWidget):
    def __init__(self, app_state: AppState, parent=None):
        super().__init__(parent)
        self.app_state = app_state

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(8)

        header = QVBoxLayout()
        header.setSpacing(4)

        title = QLabel("Dashboard")
        title.setStyleSheet("font-size: 15pt; font-weight: bold;")
        header.addWidget(title)

        self.subtitle_label = QLabel("")
        self.subtitle_label.setWordWrap(True)
        header.addWidget(self.subtitle_label)

        root.addLayout(header)

        main_area = QVBoxLayout()
        main_area.setSpacing(8)

        row1 = QHBoxLayout()
        row1.setSpacing(8)

        self.usage_card = CardFrame()
        u_layout = QVBoxLayout(self.usage_card)
        u_layout.setSpacing(6)

        u_title = QLabel("<b>AI Usage snapshot</b>")
        u_title.setAlignment(Qt.AlignVCenter | Qt.AlignVCenter)
        u_layout.addWidget(u_title)

        self.max_prompts_label = QLabel()
        self.used_today_label = QLabel()
        self.asi_label = QLabel()
        u_layout.addWidget(self.max_prompts_label)
        u_layout.addWidget(self.used_today_label)
        u_layout.addWidget(self.asi_label)

        self.prompts_bar = QProgressBar()
        self.asi_bar = QProgressBar()
        u_layout.addWidget(self.prompts_bar)
        u_layout.addWidget(self.asi_bar)

        self.sustain_card = CardFrame()
        s_layout = QVBoxLayout(self.sustain_card)
        s_layout.setSpacing(6)

        self.sustain_title = QLabel("")
        self.sustain_title.setStyleSheet("font-weight: bold;")
        self.sustain_title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.sustain_desc = QLabel("")
        self.sustain_desc.setWordWrap(True)
        self.sustain_score_label = QLabel("")

        s_layout.addWidget(self.sustain_title)
        s_layout.addWidget(self.sustain_desc)
        s_layout.addWidget(self.sustain_score_label)

        row1.addWidget(self.usage_card)
        row1.addWidget(self.sustain_card)

        row2 = QHBoxLayout()
        row2.setSpacing(8)

        self.tip_card = CardFrame()
        t_layout = QVBoxLayout(self.tip_card)
        t_layout.setSpacing(4)
        t_title = QLabel("<b>Daily tip</b>")
        t_title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.tip_label = QLabel("")
        self.tip_label.setWordWrap(True)
        t_layout.addWidget(t_title)
        t_layout.addWidget(self.tip_label)

        self.forum_card = CardFrame()
        f_layout = QVBoxLayout(self.forum_card)
        f_layout.setSpacing(4)
        f_title = QLabel("<b>Forum highlight</b>")
        f_title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.forum_label = QLabel("")
        self.forum_label.setWordWrap(True)
        f_layout.addWidget(f_title)
        f_layout.addWidget(self.forum_label)

        row2.addWidget(self.tip_card)
        row2.addWidget(self.forum_card)

        main_area.addLayout(row1)
        main_area.addLayout(row2)

        root.addLayout(main_area)

        self.subtitle_label.setAlignment(Qt.AlignCenter)
        self.max_prompts_label.setAlignment(Qt.AlignCenter)
        self.used_today_label.setAlignment(Qt.AlignCenter)
        self.asi_label.setAlignment(Qt.AlignCenter)
        self.sustain_title.setAlignment(Qt.AlignCenter)
        self.sustain_desc.setAlignment(Qt.AlignCenter)
        self.sustain_score_label.setAlignment(Qt.AlignCenter)
        self.tip_label.setAlignment(Qt.AlignCenter)
        self.forum_label.setAlignment(Qt.AlignCenter)

        root.setStretchFactor(main_area, 1)

        self.refresh()

    def refresh(self):
        st = self.app_state
        self.subtitle_label.setText(st.dashboard_subtitle)

        self.max_prompts_label.setText(f"Max prompts: {st.max_prompts_per_day}")
        self.used_today_label.setText(f"Used today: {st.prompts_used_today}")
        self.asi_label.setText(f"ASI: {st.current_asi:.1f}/100")

        self.prompts_bar.setMaximum(st.max_prompts_per_day)
        self.prompts_bar.setValue(st.prompts_used_today)

        self.asi_bar.setMaximum(100)
        self.asi_bar.setValue(int(st.current_asi))

        self.sustain_title.setText(st.sustain_box_title)
        self.sustain_desc.setText(st.sustain_box_description)
        self.sustain_score_label.setText(st.sustain_score_line or "")

        self.tip_label.setText(st.daily_tip)
        self.forum_label.setText(st.forum_highlight)


class AIUsageScreen(QWidget):
    def __init__(self, app_state: AppState, on_simulate_use, on_reset, parent=None):
        super().__init__(parent)
        self.app_state = app_state
        self.on_simulate_use = on_simulate_use
        self.on_reset = on_reset

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(8)

        title = QLabel("AI Usage & ASI")
        title.setStyleSheet("font-size: 15pt; font-weight: bold;")
        root.addWidget(title)

        main_area = QHBoxLayout()
        main_area.setSpacing(8)

        controls_card = CardFrame()
        c_layout = QVBoxLayout(controls_card)
        c_layout.setSpacing(6)
        c_layout.setAlignment(Qt.AlignCenter)  # ✅ center all content

        c_layout.addStretch(1)

        c_title = QLabel("<b>Prompt usage</b>")
        c_title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        c_layout.addWidget(c_title)

        self.usage_label = QLabel("")
        c_layout.addWidget(self.usage_label)

        self.prompts_bar = QProgressBar()
        c_layout.addWidget(self.prompts_bar)

        simulate_btn = QPushButton("Simulate use")
        simulate_btn.clicked.connect(self.on_simulate_use)
        c_layout.addWidget(simulate_btn)

        reset_btn = QPushButton("Reset")
        reset_btn.clicked.connect(self.on_reset)
        c_layout.addWidget(reset_btn)

        self.limit_label = QLabel("")
        self.limit_label.setStyleSheet("color: red; font-size: 9pt;")
        c_layout.addWidget(self.limit_label)

        asi_card = CardFrame()
        a_layout = QVBoxLayout(asi_card)
        a_layout.setSpacing(6)
        a_layout.setAlignment(Qt.AlignCenter)
        a_layout.addStretch(1)

        a_title = QLabel("<b>ASI</b>")
        a_title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        a_layout.addWidget(a_title)

        self.asi_label = QLabel("")
        a_layout.addWidget(self.asi_label)

        self.asi_bar = QProgressBar()
        a_layout.addWidget(self.asi_bar)

        self.asi_interp_label = QLabel("")
        self.asi_interp_label.setWordWrap(True)
        a_layout.addWidget(self.asi_interp_label)

        main_area.addWidget(controls_card)
        main_area.addWidget(asi_card)

        root.addLayout(main_area)

        self.usage_label.setAlignment(Qt.AlignCenter)
        self.limit_label.setAlignment(Qt.AlignCenter)
        self.asi_label.setAlignment(Qt.AlignCenter)
        self.asi_interp_label.setAlignment(Qt.AlignCenter)

        root.setStretchFactor(main_area, 1)

        c_layout.addStretch(1)

        self.refresh()

    def refresh(self):
        st = self.app_state
        self.usage_label.setText(
            f"Used today: {st.prompts_used_today} / {st.max_prompts_per_day}"
        )
        self.prompts_bar.setMaximum(st.max_prompts_per_day)
        self.prompts_bar.setValue(st.prompts_used_today)
        self.limit_label.setText(st.prompt_limit_message)

        self.asi_label.setText(f"Your ASI: {st.current_asi:.1f}")
        self.asi_bar.setMaximum(100)
        self.asi_bar.setValue(int(st.current_asi))
        self.asi_interp_label.setText(st.asi_interpretation)


class SustainIndexScreen(QWidget):
    def __init__(self, app_state: AppState, on_pick_image, on_compute_score, parent=None):
        super().__init__(parent)
        self.app_state = app_state
        self.on_pick_image = on_pick_image
        self.on_compute_score = on_compute_score

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(8)

        self.title_label = QLabel("")
        self.title_label.setStyleSheet("font-size: 15pt; font-weight: bold;")
        root.addWidget(self.title_label)

        self.subtitle_label = QLabel("")
        self.subtitle_label.setWordWrap(True)
        root.addWidget(self.subtitle_label)

        main_area = QHBoxLayout()
        main_area.setSpacing(8)

        input_card = CardFrame()
        in_layout = QVBoxLayout(input_card)
        in_layout.setSpacing(6)

        self.form_label = QLabel("")
        self.form_label.setStyleSheet("font-weight: bold;")
        in_layout.addWidget(self.form_label)

        self.materials_input = QTextEdit()
        self.materials_input.setPlaceholderText("Describe the item or product...")
        in_layout.addWidget(self.materials_input)

        img_btn = QPushButton("Upload Image")
        img_btn.clicked.connect(self.on_pick_image)
        in_layout.addWidget(img_btn)

        self.image_label = QLabel("")
        self.image_label.setStyleSheet("font-size: 9pt; color: #555555;")
        in_layout.addWidget(self.image_label)

        compute_btn = QPushButton("Compute Score")
        compute_btn.clicked.connect(self.compute_clicked)
        in_layout.addWidget(compute_btn)

        self.limit_label = QLabel("")
        self.limit_label.setStyleSheet("color: red; font-size: 9pt;")
        in_layout.addWidget(self.limit_label)

        result_card = CardFrame()
        r_layout = QVBoxLayout(result_card)
        r_layout.setSpacing(6)

        r_title = QLabel("<b>Index result</b>")
        r_title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        r_layout.addWidget(r_title)

        self.score_line_label = QLabel("")
        r_layout.addWidget(self.score_line_label)

        self.score_interp_label = QLabel("")
        self.score_interp_label.setWordWrap(True)
        r_layout.addWidget(self.score_interp_label)

        self.usage_limit_label = QLabel("")
        self.usage_limit_label.setStyleSheet("font-size: 9pt; color: #555555;")
        r_layout.addWidget(self.usage_limit_label)

        main_area.addWidget(input_card)
        main_area.addWidget(result_card)

        root.addLayout(main_area)

        self.title_label.setAlignment(Qt.AlignCenter)
        self.subtitle_label.setAlignment(Qt.AlignCenter)
        self.form_label.setAlignment(Qt.AlignCenter)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.limit_label.setAlignment(Qt.AlignCenter)
        self.score_line_label.setAlignment(Qt.AlignCenter)
        self.score_interp_label.setAlignment(Qt.AlignCenter)
        self.usage_limit_label.setAlignment(Qt.AlignCenter)

        root.setStretchFactor(main_area, 1)

        self.refresh()

    def compute_clicked(self):
        materials = self.materials_input.toPlainText()
        self.on_compute_score(materials, "")

    def refresh(self):
        st = self.app_state
        self.title_label.setText(st.index_title)
        self.subtitle_label.setText(st.index_subtitle)
        self.form_label.setText(st.index_form_label)

        self.image_label.setText(st.selected_image_name)
        self.limit_label.setText(st.index_limit_message)
        self.score_line_label.setText(st.index_score_line)
        self.score_interp_label.setText(st.index_score_interpretation)
        self.usage_limit_label.setText(st.index_usage_limit_description)


class NewsScreen(QWidget):
    def __init__(self, app_state: AppState, parent=None):
        super().__init__(parent)
        self.app_state = app_state

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(8)

        title = QLabel("Sustainability News")
        title.setStyleSheet("font-size: 15pt; font-weight: bold;")
        root.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(8)
        scroll.setWidget(self.container)
        root.addWidget(scroll)
        root.setStretchFactor(scroll, 1)

        self.refresh()

    def refresh(self):
        while self.container_layout.count():
            item = self.container_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        for item in self.app_state.news_items:
            w = NewsItemWidget(item["title"], item["summary"], item["source"])
            self.container_layout.addWidget(w)

        self.container_layout.addStretch(1)


class ForumScreen(QWidget):
    def __init__(self, app_state: AppState, on_add_thread, parent=None):
        super().__init__(parent)
        self.app_state = app_state
        self.on_add_thread = on_add_thread

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(8)

        title = QLabel("Community Forum")
        title.setStyleSheet("font-size: 15pt; font-weight: bold;")
        root.addWidget(title)

        main_area = QHBoxLayout()
        main_area.setSpacing(8)

        threads_card = CardFrame()
        tlayout_outer = QVBoxLayout(threads_card)
        tlayout_outer.setSpacing(4)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.thread_container = QWidget()
        self.thread_layout = QVBoxLayout(self.thread_container)
        self.thread_layout.setContentsMargins(0, 0, 0, 0)
        self.thread_layout.setSpacing(6)
        scroll.setWidget(self.thread_container)

        tlayout_outer.addWidget(scroll)

        post_card = CardFrame()
        post_layout = QVBoxLayout(post_card)
        post_layout.setSpacing(6)

        p_title = QLabel("<b>Start a new thread</b>")
        p_title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        post_layout.addWidget(p_title)

        self.new_title_input = QLineEdit()
        self.new_title_input.setPlaceholderText("Thread title")
        post_layout.addWidget(self.new_title_input)

        self.new_body_input = QTextEdit()
        self.new_body_input.setPlaceholderText("Thread content")
        post_layout.addWidget(self.new_body_input)

        post_btn = QPushButton("Post")
        post_btn.clicked.connect(self.post_thread)
        post_layout.addWidget(post_btn)

        main_area.addWidget(threads_card, 3)
        main_area.addWidget(post_card, 2)

        root.addLayout(main_area)

        p_title.setAlignment(Qt.AlignCenter)

        root.setStretchFactor(main_area, 1)

        self.refresh()

    def post_thread(self):
        title = self.new_title_input.text().strip()
        body = self.new_body_input.toPlainText().strip()
        self.on_add_thread(title, body)
        self.new_title_input.clear()
        self.new_body_input.clear()
        self.refresh()

    def refresh(self):
        while self.thread_layout.count():
            item = self.thread_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        for t in self.app_state.forum_threads:
            w = ForumThreadItemWidget(t["title"], t["author"], t["body"])
            self.thread_layout.addWidget(w)

        mock_threads = [
            {
                "title": "How strict should prompt limits be?",
                "author": "TechCo Lead",
                "body": "We tested 8/day and saw better creativity.",
            },
            {
                "title": "Tracking AI water usage",
                "author": "Analyst",
                "body": "Anyone converting token usage to water metrics?",
            },
        ]
        for t in mock_threads:
            w = ForumThreadItemWidget(t["title"], t["author"], t["body"])
            self.thread_layout.addWidget(w)

        self.thread_layout.addStretch(1)


class SettingsScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(8)

        title = QLabel("Settings")
        title.setStyleSheet("font-size: 15pt; font-weight: bold;")
        root.addWidget(title)

        info_card = CardFrame()
        ilayout = QVBoxLayout(info_card)
        ilayout.setSpacing(6)
        info = QLabel("No settings available yet.")
        info.setWordWrap(True)

        info.setAlignment(Qt.AlignCenter)

        ilayout.addWidget(info, alignment=Qt.AlignCenter)

        root.addWidget(info_card)
        root.setStretchFactor(info_card, 1)


# ============================================================
#  LOGIN SCREEN (UPDATED FOR BETTER SCALING)
# ============================================================

class LoginScreen(QWidget):
    def __init__(self, app_state: AppState, on_login, parent=None):
        super().__init__(parent)
        self.app_state = app_state
        self.on_login = on_login

        # Outer layout to center the card
        outer_v = QVBoxLayout(self)
        outer_v.setContentsMargins(0, 0, 0, 0)
        outer_v.setSpacing(0)
        outer_v.addStretch(1)

        outer_h = QHBoxLayout()
        outer_h.setSpacing(0)
        outer_h.addStretch(1)

        # Card that fills most of the window
        container = CardFrame(vertical_expanding=True)
        #container.setFixedSize(self.screen_size_scaled(0.7, 0.7))  # 70% of screen
        w, h = self.screen_size_scaled(0.7, 0.7)
        container.setFixedSize(w, h)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # Title
        title = QLabel("sustAIn")
        title.setStyleSheet("font-size: 26pt; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Subtitle
        subtitle = QLabel("AI-powered sustainable usage")
        subtitle.setWordWrap(True)
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("font-size: 12pt; color: #555555;")
        layout.addWidget(subtitle)

        layout.addStretch(1)

        # Form
        form = QVBoxLayout()
        form.setSpacing(14)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        form.addWidget(self.username_input)

        self.company_input = QLineEdit()
        self.company_input.setPlaceholderText("Company (optional)")
        form.addWidget(self.company_input)

        btn = QPushButton("Continue")
        btn.setMinimumHeight(38)
        btn.clicked.connect(self.login_clicked)
        form.addWidget(btn)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: red; font-size: 10pt;")
        self.status_label.setAlignment(Qt.AlignCenter)
        form.addWidget(self.status_label)

        layout.addLayout(form)
        layout.addStretch(2)

        outer_h.addWidget(container)
        outer_h.addStretch(1)

        outer_v.addLayout(outer_h)
        outer_v.addStretch(1)

    def screen_size_scaled(self, w_ratio, h_ratio):
        screen = QApplication.primaryScreen().availableGeometry()
        w = int(screen.width() * w_ratio)
        h = int(screen.height() * h_ratio)
        return w, h

    def login_clicked(self):
        username = self.username_input.text().strip()
        company = self.company_input.text().strip()
        if not username:
            self.status_label.setText("Enter a username.")
            return
        self.status_label.setText("")
        self.on_login(username, company)


# ============================================================
#  ROLE SELECT + APP FRAME
# ============================================================

class RoleSelectScreen(QWidget):
    def __init__(self, app_state: AppState, on_select_role, parent=None):
        super().__init__(parent)
        self.app_state = app_state
        self.on_select_role = on_select_role

        root = QVBoxLayout(self)
        root.setContentsMargins(40, 40, 40, 40)
        root.setSpacing(16)

        title = QLabel("Select your role")
        title.setStyleSheet("font-size: 20pt; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        root.addWidget(title)

        main_area = QHBoxLayout()
        main_area.setSpacing(16)

        # Business card
        business_card = CardFrame(vertical_expanding=True)
        b_layout = QVBoxLayout(business_card)
        b_layout.setContentsMargins(24, 24, 24, 24)
        b_layout.setSpacing(12)

        b_title = QLabel("Business tier")
        b_title.setStyleSheet("font-size: 16pt; font-weight: bold;")
        b_title.setAlignment(Qt.AlignCenter)

        b_bullet_container = QWidget()
        b_bullet_layout = QVBoxLayout(b_bullet_container)
        b_bullet_layout.setContentsMargins(0, 0, 0, 0)
        b_bullet_layout.setSpacing(12)
        b_bullet_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        def make_bullet(text: str) -> QLabel:
            lbl = QLabel(f"• {text}")
            lbl.setWordWrap(True)
            lbl.setStyleSheet("font-size: 12pt;")
            return lbl

        b_bullet_layout.addWidget(make_bullet("Limit prompts per day"))
        b_bullet_layout.addWidget(make_bullet("Track ASI (AI Sustainability Index)"))
        b_bullet_layout.addWidget(make_bullet("Compute PSI (Product Sustainability Index)"))
        b_bullet_layout.addStretch(1)

        b_btn = QPushButton("Continue as Business")
        b_btn.setMinimumHeight(36)
        b_btn.setStyleSheet("font-size: 12pt;")
        b_btn.clicked.connect(lambda: self.on_select_role("business"))

        b_layout.addWidget(b_title)
        b_layout.addWidget(b_bullet_container, 1)
        b_layout.addWidget(b_btn, alignment=Qt.AlignCenter)

        # Consumer card
        consumer_card = CardFrame(vertical_expanding=True)
        c_layout = QVBoxLayout(consumer_card)
        c_layout.setContentsMargins(24, 24, 24, 24)
        c_layout.setSpacing(12)

        c_title = QLabel("Consumer tier")
        c_title.setStyleSheet("font-size: 16pt; font-weight: bold;")
        c_title.setAlignment(Qt.AlignCenter)

        c_bullet_container = QWidget()
        c_bullet_layout = QVBoxLayout(c_bullet_container)
        c_bullet_layout.setContentsMargins(0, 0, 0, 0)
        c_bullet_layout.setSpacing(12)
        c_bullet_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        c_bullet_layout.addWidget(make_bullet("Check Waste Sustainability Index"))
        c_bullet_layout.addWidget(make_bullet("Read sustainability news"))
        c_bullet_layout.addWidget(make_bullet("Join community forums"))
        c_bullet_layout.addStretch(1)

        c_btn = QPushButton("Continue as Consumer")
        c_btn.setMinimumHeight(36)
        c_btn.setStyleSheet("font-size: 12pt;")
        c_btn.clicked.connect(lambda: self.on_select_role("consumer"))

        c_layout.addWidget(c_title)
        c_layout.addWidget(c_bullet_container, 1)
        c_layout.addWidget(c_btn, alignment=Qt.AlignCenter)

        main_area.addStretch(1)
        main_area.addWidget(business_card, 3)
        main_area.addWidget(consumer_card, 3)
        main_area.addStretch(1)

        root.addLayout(main_area)
        root.setStretchFactor(main_area, 1)


class AppFrame(QWidget):
    def __init__(self, app_state: AppState, on_switch_role, on_logout, parent=None):
        super().__init__(parent)
        self.app_state = app_state

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.inner_stack = QStackedWidget()

        def get_context_title():
            w = self.inner_stack.currentWidget()
            if not w:
                return ""
            name_map = {
                "dashboard": "Dashboard",
                "ai_usage": "AI Usage & ASI",
                "sustain_index": "Product / Waste Index",
                "news": "News",
                "forum": "Forum",
                "settings": "Settings",
            }
            key = w.objectName()
            return name_map.get(key, key.capitalize())

        self.topbar = SustainTopBar(self.app_state, get_context_title)
        root.addWidget(self.topbar)

        center = QHBoxLayout()
        center.setContentsMargins(0, 0, 0, 0)
        center.setSpacing(0)

        nav = SustainSideNav(
            on_nav_clicked=self.set_current_page,
            on_switch_role=on_switch_role,
            on_logout=on_logout,
        )
        nav.setFixedWidth(230)
        center.addWidget(nav)

        self.dashboard_screen = DashboardScreen(self.app_state)
        self.dashboard_screen.setObjectName("dashboard")

        self.ai_usage_screen = AIUsageScreen(
            self.app_state,
            on_simulate_use=self.simulate_prompt_use,
            on_reset=self.reset_prompt_usage,
        )
        self.ai_usage_screen.setObjectName("ai_usage")

        self.index_screen = SustainIndexScreen(
            self.app_state,
            on_pick_image=self.pick_image,
            on_compute_score=self.compute_sustainability_score,
        )
        self.index_screen.setObjectName("sustain_index")

        self.news_screen = NewsScreen(self.app_state)
        self.news_screen.setObjectName("news")

        self.forum_screen = ForumScreen(
            self.app_state,
            on_add_thread=self.add_forum_thread,
        )
        self.forum_screen.setObjectName("forum")

        self.settings_screen = SettingsScreen()
        self.settings_screen.setObjectName("settings")

        for w in [
            self.dashboard_screen,
            self.ai_usage_screen,
            self.index_screen,
            self.news_screen,
            self.forum_screen,
            self.settings_screen,
        ]:
            self.inner_stack.addWidget(w)

        center.addWidget(self.inner_stack)
        root.addLayout(center)
        root.setStretchFactor(center, 1)

        self.set_current_page("dashboard")

    def set_current_page(self, name: str):
        for i in range(self.inner_stack.count()):
            w = self.inner_stack.widget(i)
            if w.objectName() == name:
                self.inner_stack.setCurrentIndex(i)
                break
        self.refresh_all()

    def refresh_all(self):
        self.dashboard_screen.refresh()
        self.ai_usage_screen.refresh()
        self.index_screen.refresh()
        self.news_screen.refresh()
        self.forum_screen.refresh()
        self.topbar.refresh()

    def simulate_prompt_use(self):
        st = self.app_state
        if st.prompts_used_today >= st.max_prompts_per_day:
            st.prompt_limit_message = "Daily limit reached."
        else:
            st.prompts_used_today += 1
            st.prompt_limit_message = ""
        self._recompute_asi()
        self.refresh_all()

    def reset_prompt_usage(self):
        st = self.app_state
        st.prompts_used_today = 0
        st.prompt_limit_message = ""
        self._recompute_asi()
        self.refresh_all()

    def _recompute_asi(self):
        st = self.app_state
        ratio = st.prompts_used_today / float(st.max_prompts_per_day)
        st.current_asi = max(0, 100 * (1 - min(1, ratio)))
        if st.current_asi > 70:
            st.asi_interpretation = "Using AI sparingly today."
        elif st.current_asi > 40:
            st.asi_interpretation = "Moderate usage. Consider more offline thinking."
        else:
            st.asi_interpretation = "Heavy usage. Try solving more manually first."

    def pick_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Image",
            "",
            "Images (*.png *.jpg *.jpeg)",
        )
        if path:
            self.app_state.selected_image_path = path
            self.app_state.selected_image_name = path.split("/")[-1]
        self.refresh_all()

    def compute_sustainability_score(self, materials: str, tech: str):
        st = self.app_state
        if not st.selected_image_path:
            st.index_limit_message = "Please upload an image first."
            self.refresh_all()
            return

        score = 60  # placeholder
        st.last_index_score = score
        st.index_score_line = f"Sustainability Score: {score}/100"

        if score < 40:
            interpretation = "Low sustainability. Consider better disposal or materials."
        elif score < 70:
            interpretation = "Moderate sustainability. Some improvements possible."
        else:
            interpretation = "High sustainability. Good job!"
        st.index_score_interpretation = interpretation
        st.index_limit_message = ""

        self.refresh_all()

    def add_forum_thread(self, title: str, body: str):
        if not title.strip() or not body.strip():
            return
        st = self.app_state
        st.forum_threads.insert(
            0,
            {
                "title": title.strip(),
                "author": st.current_user_label,
                "body": body.strip(),
            },
        )
        st.forum_highlight = f"“{title.strip()}”"
        self.refresh_all()


# ============================================================
#  MAIN WINDOW
# ============================================================

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.app_state = AppState()
        self._update_role_text()
        self._update_index_text()

        self.setWindowTitle("sustAIn (PyQt5)")
        self.resize(1200, 750)

        self.root_stack = QStackedWidget()
        self.setCentralWidget(self.root_stack)

        self.login_screen = LoginScreen(self.app_state, on_login=self.handle_login)
        self.role_select_screen = RoleSelectScreen(self.app_state, on_select_role=self.handle_role_select)
        self.app_frame = AppFrame(
            self.app_state,
            on_switch_role=self.show_role_select,
            on_logout=self.show_login,
        )

        self.root_stack.addWidget(self.login_screen)        # 0
        self.root_stack.addWidget(self.role_select_screen)  # 1
        self.root_stack.addWidget(self.app_frame)           # 2

        self.show_login()

    def _update_role_text(self):
        st = self.app_state
        if st.current_role == "business":
            st.dashboard_subtitle = "Business tier: AI limits, ASI, PSI."
            st.sustain_box_title = "Product Sustainability Index (PSI)"
            st.sustain_box_description = "Evaluate product materials and components."
        else:
            st.dashboard_subtitle = "Consumer tier: waste index, news, forums."
            st.sustain_box_title = "Waste Sustainability Index"
            st.sustain_box_description = "Check how sustainable your waste disposal is."

    def _update_index_text(self):
        st = self.app_state
        if st.current_role == "business":
            st.index_title = "Product Sustainability Index (PSI)"
            st.index_subtitle = "Enter materials and components."
            st.index_form_label = "Product description"
            st.index_materials_hint = "Materials (plastic, aluminum, cardboard...)"
            st.index_tech_hint = "Tech parts (battery, PCB...)"
            st.index_usage_limit_description = "Limit: once per day"
        else:
            st.index_title = "Waste Sustainability Index"
            st.index_subtitle = "Describe the waste item."
            st.index_form_label = "Waste description"
            st.index_materials_hint = "Plastic bottle, cardboard box..."
            st.index_tech_hint = "Any electronics?"
            st.index_usage_limit_description = "Limit: once per day"

    def show_login(self):
        self.root_stack.setCurrentWidget(self.login_screen)

    def show_role_select(self):
        self.root_stack.setCurrentWidget(self.role_select_screen)

    def show_app_frame(self):
        self.root_stack.setCurrentWidget(self.app_frame)
        self.app_frame.refresh_all()

    def handle_login(self, username: str, company: str):
        st = self.app_state
        st.current_username = username.strip()
        st.current_company = company.strip()
        self.show_role_select()

    def handle_role_select(self, role: str):
        st = self.app_state
        st.current_role = role
        self._update_role_text()
        self._update_index_text()
        self.show_app_frame()


# ============================================================
#  GLOBAL THEME
# ============================================================

SUSTAIN_THEME_QSS = """
    QWidget {
        background-color: #F5F3E7;
        color: #333333;
        font-size: 11pt;
    }

    QPushButton {
        background-color: #4CAF50;
        color: white;
        border: none;
        padding: 6px 14px;
        border-radius: 6px;
    }

    QPushButton:hover {
        background-color: #2E7D32;
    }

    QPushButton:disabled {
        background-color: #A5D6A7;
        color: #EEEEEE;
    }

    QLineEdit, QTextEdit {
        background-color: white;
        border: 1px solid #CCCCCC;
        border-radius: 4px;
        padding: 4px;
    }

    QLineEdit:focus, QTextEdit:focus {
        border: 1px solid #4CAF50;
    }

    QProgressBar {
        border: 1px solid #CCCCCC;
        border-radius: 4px;
        background: white;
        text-align: center;
    }

    QProgressBar::chunk {
        background-color: #4CAF50;
        border-radius: 4px;
    }

    QScrollArea {
        border: none;
        background: transparent;
    }

    QFrame[card="true"] {
        background-color: white;
        border: 1px solid #E8E8E8;
        border-radius: 8px;
        padding: 10px;
    }
"""


# ============================================================
#  ENTRY POINT
# ============================================================

def main():
    QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)

    base_font = QFont()
    base_font.setPointSize(11)
    app.setFont(base_font)

    app.setStyleSheet(SUSTAIN_THEME_QSS)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()