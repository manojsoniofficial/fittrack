"""
FitTrack Pro - Login Window
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QMessageBox, QApplication, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from models.database import SessionLocal, User, init_db
from assets.styles import LOGIN_STYLESHEET


class LoginWindow(QWidget):
    login_successful = pyqtSignal(object)  # emits User object

    def __init__(self):
        super().__init__()
        self.setWindowTitle("FitTrack Pro — Login")
        self.setMinimumSize(500, 640)
        self.resize(500, 640)
        self.setStyleSheet(LOGIN_STYLESHEET)
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.setContentsMargins(32, 32, 32, 32)

        card = QFrame()
        card.setObjectName("loginCard")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(0)
        card_layout.setContentsMargins(44, 40, 44, 40)

        # ── Icon badge ──────────────────────────────────
        badge_row = QHBoxLayout()
        badge_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_badge = QFrame()
        icon_badge.setObjectName("iconBadge")
        icon_badge.setFixedSize(72, 72)
        badge_inner = QVBoxLayout(icon_badge)
        badge_inner.setContentsMargins(0, 0, 0, 0)
        badge_inner.setAlignment(Qt.AlignmentFlag.AlignCenter)

        emoji_lbl = QLabel("🏋️")
        emoji_lbl.setObjectName("appEmoji")
        emoji_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge_inner.addWidget(emoji_lbl)

        badge_row.addWidget(icon_badge)
        card_layout.addLayout(badge_row)
        card_layout.addSpacing(16)

        # ── Title ─────────────────────────────────────
        logo = QLabel("FitTrack Pro")
        logo.setObjectName("appTitle")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(logo)
        card_layout.addSpacing(6)

        tagline = QLabel("Smart Workout · Nutrition · Progress")
        tagline.setObjectName("appTagline")
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(tagline)
        card_layout.addSpacing(28)

        # ── Divider ────────────────────────────────────
        div = QFrame()
        div.setObjectName("divider")
        div.setFrameShape(QFrame.Shape.HLine)
        card_layout.addWidget(div)
        card_layout.addSpacing(24)

        # ── Username ───────────────────────────────────
        uname_label = QLabel("USERNAME")
        uname_label.setObjectName("fieldLabel")
        card_layout.addWidget(uname_label)
        card_layout.addSpacing(6)

        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Enter your username")
        self.username_edit.setText("john_doe")
        self.username_edit.setFixedHeight(44)
        card_layout.addWidget(self.username_edit)
        card_layout.addSpacing(16)

        # ── Password ───────────────────────────────────
        pwd_label = QLabel("PASSWORD")
        pwd_label.setObjectName("fieldLabel")
        card_layout.addWidget(pwd_label)
        card_layout.addSpacing(6)

        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("Enter your password")
        self.password_edit.setText("user123")
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setFixedHeight(44)
        card_layout.addWidget(self.password_edit)
        card_layout.addSpacing(6)

        # ── Error label ────────────────────────────────
        self.error_label = QLabel("")
        self.error_label.setObjectName("errorLabel")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setFixedHeight(20)
        card_layout.addWidget(self.error_label)
        card_layout.addSpacing(10)

        # ── Sign In button ─────────────────────────────
        login_btn = QPushButton("Sign In")
        login_btn.setObjectName("loginBtn")
        login_btn.setFixedHeight(46)
        login_btn.clicked.connect(self._attempt_login)
        login_btn.setDefault(True)
        card_layout.addWidget(login_btn)
        card_layout.addSpacing(20)

        # ── Hint ───────────────────────────────────────
        hint = QLabel("Demo: john_doe / user123  ·  coach_sarah / coach123")
        hint.setObjectName("hintLabel")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setWordWrap(True)
        card_layout.addWidget(hint)

        # Key bindings
        self.password_edit.returnPressed.connect(self._attempt_login)
        self.username_edit.returnPressed.connect(self._attempt_login)

        outer.addWidget(card)

    def _attempt_login(self):
        username = self.username_edit.text().strip()
        password = self.password_edit.text()

        if not username or not password:
            self.error_label.setText("Please enter username and password.")
            return

        session = SessionLocal()
        try:
            user = session.query(User).filter_by(username=username, is_active=True).first()
            if user and user.check_password(password):
                self.error_label.setText("")
                self.login_successful.emit(user)
            else:
                self.error_label.setText("Invalid username or password.")
        finally:
            session.close()
