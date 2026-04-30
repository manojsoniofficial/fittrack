"""
FitTrack Pro - Main Application Window
Sidebar navigation + stacked views
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QStackedWidget, QFrame,
    QSizePolicy, QApplication, QStatusBar
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

from models.database import User
from assets.styles import MAIN_STYLESHEET


NAV_ITEMS = [
    ("🏠", "Dashboard", "dashboard"),
    ("🏋️", "Workouts", "workouts"),
    ("🥗", "Nutrition", "nutrition"),
    ("📏", "Measurements", "measurements"),
    ("🎯", "Goals", "goals"),
    ("🔔", "Notifications", "notifications"),
]

COACH_NAV = [
    ("👥", "Coach Dashboard", "coach"),
]


class NavButton(QPushButton):
    def __init__(self, icon: str, label: str, page_id: str):
        super().__init__(f" {icon}  {label}")
        self.page_id = page_id
        self.setObjectName("navButton")
        self.setProperty("active", "false")
        self.setFixedHeight(44)
        self.setCheckable(False)
        self.setToolTip(label)

    def set_active(self, active: bool):
        self.setProperty("active", "true" if active else "false")
        self.style().unpolish(self)
        self.style().polish(self)


class MainWindow(QMainWindow):
    def __init__(self, user: User):
        super().__init__()
        self.user = user
        self.setWindowTitle(f"FitTrack Pro — {user.full_name or user.username}")
        self.setMinimumSize(1100, 700)
        self.resize(1280, 800)
        self.setStyleSheet(MAIN_STYLESHEET)
        self._nav_buttons: list[NavButton] = []
        self._build_ui()
        self._navigate("dashboard")

        # Notification check timer
        self._notif_timer = QTimer(self)
        self._notif_timer.timeout.connect(self._check_notifications)
        self._notif_timer.start(30000)  # every 30s

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Sidebar ──
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(240)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # Logo
        logo_widget = QWidget()
        logo_layout = QVBoxLayout(logo_widget)
        logo_layout.setContentsMargins(16, 20, 16, 10)

        logo_lbl = QLabel("🏋️ FitTrack Pro")
        logo_lbl.setObjectName("sidebarLogo")
        logo_layout.addWidget(logo_lbl)

        sub_lbl = QLabel("HealthHub Platform")
        sub_lbl.setObjectName("sidebarSubtitle")
        logo_layout.addWidget(sub_lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #2d3748;")
        logo_layout.addWidget(sep)

        sidebar_layout.addWidget(logo_widget)

        # Navigation buttons
        nav_items = NAV_ITEMS[:]
        if self.user.role == "coach":
            nav_items += COACH_NAV

        for icon, label, page_id in nav_items:
            btn = NavButton(icon, label, page_id)
            btn.clicked.connect(lambda checked, pid=page_id: self._navigate(pid))
            sidebar_layout.addWidget(btn)
            self._nav_buttons.append(btn)

        sidebar_layout.addStretch()

        # User info at bottom
        user_info = QWidget()
        user_info.setObjectName("userInfoWidget")
        ui_layout = QVBoxLayout(user_info)
        ui_layout.setContentsMargins(0, 0, 0, 0)
        ui_layout.setSpacing(2)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet("color: #2d3748;")
        ui_layout.addWidget(sep2)

        uname = QLabel(self.user.full_name or self.user.username)
        uname.setObjectName("userNameLabel")
        uname.setContentsMargins(16, 8, 16, 0)
        ui_layout.addWidget(uname)

        urole = QLabel(f"{'Coach' if self.user.role == 'coach' else 'Member'} · {self.user.email}")
        urole.setObjectName("userRoleLabel")
        urole.setContentsMargins(16, 0, 16, 4)
        urole.setWordWrap(True)
        ui_layout.addWidget(urole)

        logout_btn = QPushButton("Sign Out")
        logout_btn.setObjectName("secondaryButton")
        logout_btn.setContentsMargins(16, 0, 16, 0)
        logout_btn.clicked.connect(self._logout)
        logout_btn_container = QWidget()
        ll = QHBoxLayout(logout_btn_container)
        ll.setContentsMargins(12, 4, 12, 8)
        ll.addWidget(logout_btn)
        ui_layout.addWidget(logout_btn_container)

        sidebar_layout.addWidget(user_info)
        main_layout.addWidget(sidebar)

        # ── Content Area ──
        self.stack = QStackedWidget()
        self.stack.setObjectName("contentArea")
        main_layout.addWidget(self.stack)

        # Status bar
        self.statusBar().setObjectName("QStatusBar")
        self.statusBar().showMessage(f"Welcome, {self.user.full_name or self.user.username}!")

        # Pre-build all views
        self._views = {}
        self._init_views()

    def _init_views(self):
        from views.dashboard_view import DashboardView
        from views.workout_view import WorkoutView
        from views.nutrition_view import NutritionView
        from views.other_views import (
            MeasurementsView, GoalsView, NotificationsView, CoachDashboardView
        )

        view_map = {
            "dashboard": DashboardView,
            "workouts": WorkoutView,
            "nutrition": NutritionView,
            "measurements": MeasurementsView,
            "goals": GoalsView,
            "notifications": NotificationsView,
        }

        for page_id, ViewClass in view_map.items():
            view = ViewClass(self.user)
            self._views[page_id] = view
            self.stack.addWidget(view)

        if self.user.role == "coach":
            coach_view = CoachDashboardView(self.user)
            self._views["coach"] = coach_view
            self.stack.addWidget(coach_view)

    def _navigate(self, page_id: str):
        if page_id not in self._views:
            return

        self.stack.setCurrentWidget(self._views[page_id])

        # Update nav button styles
        for btn in self._nav_buttons:
            btn.set_active(btn.page_id == page_id)

        # Refresh data on navigation
        view = self._views[page_id]
        if hasattr(view, "_load_data"):
            view._load_data()

        self.statusBar().showMessage(f"Viewing: {page_id.replace('_', ' ').title()}", 3000)

    def _check_notifications(self):
        """Check for pending notifications."""
        from datetime import datetime
        from models.database import SessionLocal, Notification

        session = SessionLocal()
        try:
            pending_candidates = session.query(Notification).filter(
                Notification.user_id == self.user.id,
                Notification.is_read == False,
                Notification.is_sent == False,
            ).all()

            now = datetime.now()
            due_now = [
                n for n in pending_candidates
                if n.scheduled_at is None or n.scheduled_at <= now
            ]

            pending = len(due_now)
            if pending > 0:
                self.statusBar().showMessage(f"🔔 You have {pending} unread notification(s)!")

                from PyQt6.QtWidgets import QMessageBox
                titles = "\n".join(f"• {n.title}" for n in due_now[:3])
                more = f"\n+ {pending - 3} more" if pending > 3 else ""
                QMessageBox.information(
                    self,
                    "Reminder",
                    f"You have {pending} reminder(s) due now.\n\n{titles}{more}"
                )

                # Mark only due reminders as sent so future reminders still trigger later.
                for n in due_now:
                    n.is_sent = True
                session.commit()

                notif_view = self._views.get("notifications") if hasattr(self, "_views") else None
                if notif_view and hasattr(notif_view, "_load_data"):
                    notif_view._load_data()
        finally:
            session.close()

    def _logout(self):
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "Sign Out", "Are you sure you want to sign out?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            from views.login_view import LoginWindow
            self.login_window = LoginWindow()
            self.login_window.login_successful.connect(self._on_relogin)
            self.login_window.show()
            self.close()

    def _on_relogin(self, user: User):
        self.login_window.hide()
        new_window = MainWindow(user)
        new_window.show()
        self.login_window.close()
