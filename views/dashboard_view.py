"""
FitTrack Pro - Dashboard View
Shows summary stats, recent activity, goals, and charts
"""

from datetime import date, timedelta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QGridLayout, QProgressBar, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QPainter, QColor, QPen, QBrush
from PyQt6.QtCharts import (
    QChart, QChartView, QBarSeries, QBarSet, QBarCategoryAxis,
    QValueAxis, QLineSeries, QSplineSeries, QPieSeries
)

from models.database import SessionLocal, User, WorkoutSession, MealEntry, BodyMeasurement
from models.services import ProgressAnalyser, CalorieCalculator


# ─── Stat Card ────────────────────────────────────────────────────────────────

class StatCard(QFrame):
    def __init__(self, title: str, value: str, subtitle: str = "", color: str = "#6366f1"):
        super().__init__()
        self.setObjectName("card")
        self.setMinimumHeight(110)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(16, 16, 16, 16)

        title_label = QLabel(title.upper())
        title_label.setObjectName("cardTitle")
        layout.addWidget(title_label)

        self.value_label = QLabel(value)
        self.value_label.setObjectName("cardValue")
        self.value_label.setStyleSheet(f"font-size: 28px; font-weight: bold; color: {color};")
        layout.addWidget(self.value_label)

        if subtitle:
            self.sub_label = QLabel(subtitle)
            self.sub_label.setObjectName("cardSubValue")
            layout.addWidget(self.sub_label)

    def update_value(self, value: str, subtitle: str = ""):
        self.value_label.setText(value)
        if hasattr(self, "sub_label") and subtitle:
            self.sub_label.setText(subtitle)


# ─── Mini Workout Bar Chart ────────────────────────────────────────────────────

def make_weekly_workout_chart(user_id: int, session) -> QChartView:
    """Bar chart showing workout minutes per day this week."""
    today = date.today()
    week_start = today - timedelta(days=today.weekday())

    days = [(week_start + timedelta(days=i)) for i in range(7)]
    day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    bar_set = QBarSet("Minutes")
    bar_set.setColor(QColor("#6366f1"))

    for d in days:
        total = sum(
            w.duration_minutes or 0
            for w in session.query(WorkoutSession).filter_by(user_id=user_id, date=d).all()
        )
        bar_set.append(total)

    series = QBarSeries()
    series.append(bar_set)

    chart = QChart()
    chart.addSeries(series)
    chart.setTitle("This Week's Workouts (minutes)")
    chart.setTitleFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
    chart.setBackgroundBrush(QBrush(QColor("#141828")))
    chart.setBackgroundPen(QPen(Qt.PenStyle.NoPen))
    chart.setTitleBrush(QBrush(QColor("#e2e8f0")))

    axis_x = QBarCategoryAxis()
    axis_x.append(day_labels)
    axis_x.setLabelsColor(QColor("#94a3b8"))
    chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
    series.attachAxis(axis_x)

    axis_y = QValueAxis()
    axis_y.setLabelsColor(QColor("#94a3b8"))
    axis_y.setGridLineColor(QColor("#2d3748"))
    axis_y.setLinePen(QPen(QColor("#2d3748")))
    # Ensure the Y axis always shows a sensible range even with no data
    vals = [bar_set.at(i) for i in range(bar_set.count())]
    top = max(vals) if vals else 0
    axis_y.setRange(0, max(top * 1.15, 30))
    chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
    series.attachAxis(axis_y)

    chart.setPlotAreaBackgroundBrush(QBrush(QColor("#0f1117")))
    chart.setPlotAreaBackgroundVisible(True)
    chart.legend().setVisible(False)

    view = QChartView(chart)
    view.setRenderHint(QPainter.RenderHint.Antialiasing)
    view.setMinimumHeight(232)
    view.setBackgroundBrush(QBrush(QColor("#141828")))
    return view


def make_calorie_pie_chart(protein: float, carbs: float, fat: float) -> QChartView:
    """Pie chart for today's macro split."""
    series = QPieSeries()
    has_data = protein + carbs + fat > 0
    if not has_data:
        s = series.append("No meals logged", 1)
        s.setColor(QColor("#2d3a52"))
        s.setBorderColor(QColor("#374151"))
        s.setLabelVisible(True)
        s.setLabelColor(QColor("#64748b"))
    else:
        s1 = series.append(f"Protein {protein:.0f}g", protein)
        s1.setColor(QColor("#6366f1"))
        s2 = series.append(f"Carbs {carbs:.0f}g", carbs)
        s2.setColor(QColor("#10b981"))
        s3 = series.append(f"Fat {fat:.0f}g", fat)
        s3.setColor(QColor("#f59e0b"))

    chart = QChart()
    chart.addSeries(series)
    chart.setTitle("Today's Macros")
    chart.setTitleFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
    chart.setBackgroundBrush(QBrush(QColor("#141828")))
    chart.setBackgroundPen(QPen(Qt.PenStyle.NoPen))
    chart.setTitleBrush(QBrush(QColor("#e2e8f0")))
    chart.legend().setLabelColor(QColor("#94a3b8"))
    chart.legend().setVisible(has_data)

    view = QChartView(chart)
    view.setRenderHint(QPainter.RenderHint.Antialiasing)
    view.setMinimumHeight(232)
    view.setBackgroundBrush(QBrush(QColor("#141828")))
    return view


# ─── Dashboard View ───────────────────────────────────────────────────────────

class DashboardView(QWidget):
    def __init__(self, user: User):
        super().__init__()
        self.user = user
        self._build_ui()
        self._load_data()

        # Refresh every 60s
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._load_data)
        self._timer.start(60000)

    def _build_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        self.main_layout = QVBoxLayout(container)
        self.main_layout.setSpacing(20)
        self.main_layout.setContentsMargins(24, 24, 24, 24)

        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        # ── Header ──
        header_row = QHBoxLayout()
        title = QLabel(f"Welcome back, {self.user.full_name or self.user.username}! 👋")
        title.setObjectName("pageTitle")
        header_row.addWidget(title)
        header_row.addStretch()
        today_label = QLabel(date.today().strftime("%A, %B %d %Y"))
        today_label.setStyleSheet("color: #64748b; font-size: 13px;")
        header_row.addWidget(today_label)
        self.main_layout.addLayout(header_row)

        # ── Stat Cards Row ──
        cards_layout = QGridLayout()
        cards_layout.setSpacing(16)

        self.card_workouts = StatCard("Total Workouts", "—", "this month", "#6366f1")
        self.card_calories_burned = StatCard("Calories Burned", "—", "today", "#ef4444")
        self.card_calories_in = StatCard("Calories In", "—", "today", "#10b981")
        self.card_streak = StatCard("Workout Streak", "—", "days", "#f59e0b")

        cards_layout.addWidget(self.card_workouts, 0, 0)
        cards_layout.addWidget(self.card_calories_burned, 0, 1)
        cards_layout.addWidget(self.card_calories_in, 0, 2)
        cards_layout.addWidget(self.card_streak, 0, 3)

        self.main_layout.addLayout(cards_layout)

        # ── Charts Row ──
        charts_row = QHBoxLayout()
        charts_row.setSpacing(16)

        self.workout_chart_placeholder = QFrame()
        self.workout_chart_placeholder.setObjectName("card")
        self.workout_chart_placeholder.setMinimumHeight(240)
        self.workout_chart_placeholder.setMaximumHeight(280)
        charts_row.addWidget(self.workout_chart_placeholder, 2)
        self._wc_layout = QVBoxLayout(self.workout_chart_placeholder)
        self._wc_layout.setContentsMargins(4, 4, 4, 4)

        self.macro_chart_placeholder = QFrame()
        self.macro_chart_placeholder.setObjectName("card")
        self.macro_chart_placeholder.setMinimumHeight(240)
        self.macro_chart_placeholder.setMaximumHeight(280)
        charts_row.addWidget(self.macro_chart_placeholder, 1)
        self._mc_layout = QVBoxLayout(self.macro_chart_placeholder)
        self._mc_layout.setContentsMargins(4, 4, 4, 4)

        self.main_layout.addLayout(charts_row)

        # ── Goals Row ──
        goals_label = QLabel("Active Goals")
        goals_label.setObjectName("sectionHeader")
        self.main_layout.addWidget(goals_label)

        self.goals_container = QVBoxLayout()
        self.goals_frame = QFrame()
        self.goals_frame.setObjectName("card")
        self.goals_frame.setLayout(self.goals_container)
        self.main_layout.addWidget(self.goals_frame)

        # ── Recent Workouts ──
        recent_label = QLabel("Recent Activity")
        recent_label.setObjectName("sectionHeader")
        self.main_layout.addWidget(recent_label)

        self.recent_container = QVBoxLayout()
        self.recent_frame = QFrame()
        self.recent_frame.setObjectName("card")
        self.recent_frame.setLayout(self.recent_container)
        self.main_layout.addWidget(self.recent_frame)

        # ── Badges ──
        badges_label = QLabel("Your Badges")
        badges_label.setObjectName("sectionHeader")
        self.main_layout.addWidget(badges_label)

        self.badges_row = QHBoxLayout()
        self.badges_frame = QFrame()
        self.badges_frame.setObjectName("card")
        self.badges_frame.setLayout(self.badges_row)
        self.main_layout.addWidget(self.badges_frame)

        self.main_layout.addStretch()

    def _load_data(self):
        session = SessionLocal()
        try:
            analyser = ProgressAnalyser(session)
            today = date.today()

            # Stat cards
            month_start = today.replace(day=1)
            monthly_count = session.query(WorkoutSession).filter(
                WorkoutSession.user_id == self.user.id,
                WorkoutSession.date >= month_start
            ).count()
            self.card_workouts.update_value(str(monthly_count), "this month")

            today_workouts = session.query(WorkoutSession).filter(
                WorkoutSession.user_id == self.user.id,
                WorkoutSession.date == today
            ).all()
            calories_burned = sum(w.calories_burned or 0 for w in today_workouts)
            self.card_calories_burned.update_value(f"{calories_burned:.0f}", "kcal today")

            cal_data = analyser.get_daily_calories(self.user.id, today)
            self.card_calories_in.update_value(f"{cal_data['total']:.0f}", "kcal today")

            streak = analyser.get_workout_streak(self.user.id)
            self.card_streak.update_value(str(streak), "days 🔥" if streak > 0 else "days")

            # Charts
            self._rebuild_charts(session, cal_data)

            # Goals
            self._load_goals(session)

            # Recent activity
            self._load_recent(session)

            # Badges
            self._load_badges(session)

        finally:
            session.close()

    def _rebuild_charts(self, session, cal_data):
        # Workout chart — clear old view and insert fresh one
        while self._wc_layout.count():
            item = self._wc_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._wc_layout.addWidget(make_weekly_workout_chart(self.user.id, session))

        # Macro chart — clear old view and insert fresh one
        while self._mc_layout.count():
            item = self._mc_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._mc_layout.addWidget(
            make_calorie_pie_chart(cal_data["protein"], cal_data["carbs"], cal_data["fat"])
        )

    def _load_goals(self, session):
        # Clear — must traverse child layouts to delete their widgets too
        while self.goals_container.count():
            item = self.goals_container.takeAt(0)
            if item.layout():
                while item.layout().count():
                    sub = item.layout().takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()
            elif item.widget():
                item.widget().deleteLater()

        from models.database import FitnessGoal
        goals = session.query(FitnessGoal).filter_by(
            user_id=self.user.id, is_completed=False
        ).limit(4).all()

        if not goals:
            lbl = QLabel("No active goals. Add one in the Goals section!")
            lbl.setStyleSheet("color: #64748b;")
            self.goals_container.addWidget(lbl)
            return

        for goal in goals:
            row = QHBoxLayout()
            desc = QLabel(f"{goal.goal_type} — {goal.description or ''}")
            desc.setStyleSheet("color: #e2e8f0;")
            row.addWidget(desc, 2)

            pbar = QProgressBar()
            pbar.setMaximum(100)
            target_val = goal.target_value or 1
            current_val = goal.current_value or 0
            progress = min(100, int(abs(current_val / target_val) * 100)) if target_val else 0
            pbar.setValue(progress)
            pbar.setFixedHeight(8)
            pbar.setTextVisible(False)
            row.addWidget(pbar, 3)

            pct_label = QLabel(f"{progress}%")
            pct_label.setStyleSheet("color: #6366f1; font-weight: bold; min-width: 35px;")
            row.addWidget(pct_label)

            self.goals_container.addLayout(row)

    def _load_recent(self, session):
        # Clear — must traverse child layouts to delete their widgets too
        while self.recent_container.count():
            item = self.recent_container.takeAt(0)
            if item.layout():
                while item.layout().count():
                    sub = item.layout().takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()
            elif item.widget():
                item.widget().deleteLater()

        recent = session.query(WorkoutSession).filter_by(
            user_id=self.user.id
        ).order_by(WorkoutSession.date.desc()).limit(5).all()

        if not recent:
            lbl = QLabel("No workouts logged yet. Start in the Workouts section!")
            lbl.setStyleSheet("color: #64748b;")
            self.recent_container.addWidget(lbl)
            return

        for w in recent:
            row = QHBoxLayout()
            row.setSpacing(8)
            icon_map = {
                "Cardio": "🏃", "Strength Training": "💪", "HIIT": "⚡",
                "Yoga": "🧘", "Sports": "⚽", "Other": "🏅"
            }
            icon = icon_map.get(w.activity_type, "🏅")
            name_lbl = QLabel(f"{icon}  {w.name}")
            name_lbl.setStyleSheet("color: #e2e8f0; font-weight: 600;")
            row.addWidget(name_lbl)
            row.addStretch()

            date_lbl = QLabel(w.date.strftime("%b %d"))
            date_lbl.setStyleSheet("color: #64748b;")
            date_lbl.setFixedWidth(48)
            date_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(date_lbl)

            dur_lbl = QLabel(f"{w.duration_minutes} min")
            dur_lbl.setStyleSheet("color: #94a3b8;")
            dur_lbl.setFixedWidth(62)
            dur_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(dur_lbl)

            cal_lbl = QLabel(f"{w.calories_burned or 0:.0f} kcal")
            cal_lbl.setStyleSheet("color: #ef4444;")
            cal_lbl.setFixedWidth(72)
            cal_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(cal_lbl)

            self.recent_container.addLayout(row)

    def _load_badges(self, session):
        while self.badges_row.count():
            item = self.badges_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        from models.database import Badge
        badges = session.query(Badge).filter_by(user_id=self.user.id).all()

        if not badges:
            lbl = QLabel("No badges yet. Keep training to earn them! 🏅")
            lbl.setStyleSheet("color: #64748b;")
            self.badges_row.addWidget(lbl)
            return

        for badge in badges:
            badge_widget = QFrame()
            badge_widget.setObjectName("card")
            badge_widget.setFixedWidth(140)
            badge_layout = QVBoxLayout(badge_widget)
            badge_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            icon_lbl = QLabel(badge.icon or "🏅")
            icon_lbl.setStyleSheet("font-size: 28px;")
            icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge_layout.addWidget(icon_lbl)

            name_lbl = QLabel(badge.name)
            name_lbl.setStyleSheet("color: #e2e8f0; font-weight: bold; font-size: 11px;")
            name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            name_lbl.setWordWrap(True)
            badge_layout.addWidget(name_lbl)

            badge_widget.setToolTip(badge.description or "")
            self.badges_row.addWidget(badge_widget)

        self.badges_row.addStretch()
