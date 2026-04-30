"""
FitTrack Pro - Goals, Measurements, Coach Dashboard, Notifications Views
"""

import csv
import io
from datetime import date, timedelta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QDialog, QFormLayout,
    QLineEdit, QDoubleSpinBox, QComboBox, QDateEdit, QFrame,
    QHeaderView, QMessageBox, QProgressBar, QTextEdit,
    QScrollArea, QSizePolicy, QFileDialog
)
from PyQt6.QtCore import Qt, QDate, QMargins
from PyQt6.QtGui import QPainter, QColor, QBrush, QFont
from PyQt6.QtCharts import (
    QChart, QChartView, QLineSeries, QDateTimeAxis, QValueAxis,
    QSplineSeries
)

from models.database import (
    SessionLocal, User, FitnessGoal, BodyMeasurement,
    Notification, WorkoutSession, MealEntry
)
from models.services import ProgressAnalyser, BadgeService

GOAL_TYPES = [
    "Lose Weight", "Gain Muscle", "Improve Endurance",
    "Maintain Weight", "General Fitness"
]


# ══════════════════════════════════════════════════════════════════════════════
#  GOALS VIEW
# ══════════════════════════════════════════════════════════════════════════════

class GoalDialog(QDialog):
    def __init__(self, user: User, goal: FitnessGoal = None, parent=None):
        super().__init__(parent)
        self.user = user
        self.goal = goal
        self.setWindowTitle("Edit Goal" if goal else "Add Fitness Goal")
        self.setMinimumWidth(420)
        self.setModal(True)
        self._build_ui()
        if goal:
            self._populate()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("Edit Goal" if self.goal else "Set a New Fitness Goal")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)

        self.type_combo = QComboBox()
        self.type_combo.addItems(GOAL_TYPES)
        form.addRow("Goal Type *", self.type_combo)

        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText('e.g., "Lose 5kg in 3 months"')
        form.addRow("Description *", self.desc_edit)

        self.target_spin = QDoubleSpinBox()
        self.target_spin.setRange(0, 9999)
        self.target_spin.setDecimals(1)
        form.addRow("Target Value", self.target_spin)

        self.current_spin = QDoubleSpinBox()
        self.current_spin.setRange(0, 9999)
        self.current_spin.setDecimals(1)
        form.addRow("Current Value", self.current_spin)

        self.unit_edit = QLineEdit()
        self.unit_edit.setPlaceholderText("kg, km, minutes, ...")
        form.addRow("Unit", self.unit_edit)

        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate())
        self.start_date.setCalendarPopup(True)
        form.addRow("Start Date", self.start_date)

        self.target_date = QDateEdit()
        self.target_date.setDate(QDate.currentDate().addMonths(3))
        self.target_date.setCalendarPopup(True)
        form.addRow("Target Date", self.target_date)

        self.completed_combo = QComboBox()
        self.completed_combo.addItems(["In Progress", "Completed"])
        form.addRow("Status", self.completed_combo)

        layout.addLayout(form)

        btn_row = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("secondaryButton")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()
        save_btn = QPushButton("Save Goal")
        save_btn.setObjectName("successButton")
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def _populate(self):
        g = self.goal
        idx = GOAL_TYPES.index(g.goal_type) if g.goal_type in GOAL_TYPES else 0
        self.type_combo.setCurrentIndex(idx)
        self.desc_edit.setText(g.description or "")
        self.target_spin.setValue(g.target_value or 0)
        self.current_spin.setValue(g.current_value or 0)
        self.unit_edit.setText(g.unit or "")
        if g.start_date:
            self.start_date.setDate(QDate(g.start_date.year, g.start_date.month, g.start_date.day))
        if g.target_date:
            self.target_date.setDate(QDate(g.target_date.year, g.target_date.month, g.target_date.day))
        self.completed_combo.setCurrentIndex(1 if g.is_completed else 0)

    def _save(self):
        desc = self.desc_edit.text().strip()
        if not desc:
            QMessageBox.warning(self, "Validation", "Description is required.")
            return

        sd = self.start_date.date()
        td = self.target_date.date()

        session = SessionLocal()
        try:
            if self.goal:
                g = session.merge(self.goal)
            else:
                g = FitnessGoal(user_id=self.user.id)
                session.add(g)

            g.goal_type = self.type_combo.currentText()
            g.description = desc
            g.target_value = self.target_spin.value()
            g.current_value = self.current_spin.value()
            g.unit = self.unit_edit.text().strip()
            g.start_date = date(sd.year(), sd.month(), sd.day())
            g.target_date = date(td.year(), td.month(), td.day())
            g.is_completed = self.completed_combo.currentIndex() == 1

            session.commit()
            if g.is_completed:
                BadgeService(session).check_and_award_badges(self.user.id)
            self.accept()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", str(e))
        finally:
            session.close()


class GoalsView(QWidget):
    def __init__(self, user: User):
        super().__init__()
        self.user = user
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header = QHBoxLayout()
        title = QLabel("Fitness Goals")
        title.setObjectName("pageTitle")
        header.addWidget(title)
        header.addStretch()
        add_btn = QPushButton("+ Add Goal")
        add_btn.setObjectName("successButton")
        add_btn.clicked.connect(self._add_goal)
        header.addWidget(add_btn)
        layout.addLayout(header)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Goal Type", "Description", "Progress", "Current", "Target", "Due Date", "Actions"]
        )
        ghdr = self.table.horizontalHeader()
        ghdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        ghdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        ghdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        ghdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        ghdr.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        ghdr.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        ghdr.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 140)   # Goal Type
        self.table.setColumnWidth(6, 184)   # Actions
        self.table.setColumnWidth(2, 120)   # Progress bar
        self.table.setColumnWidth(3, 100)   # Current
        self.table.setColumnWidth(4, 100)   # Target
        self.table.setColumnWidth(5, 110)   # Due Date
        self.table.verticalHeader().setDefaultSectionSize(48)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

    def _load_data(self):
        session = SessionLocal()
        try:
            goals = session.query(FitnessGoal).filter_by(user_id=self.user.id).order_by(
                FitnessGoal.is_completed, FitnessGoal.target_date
            ).all()
            self.table.setRowCount(0)
            for g in goals:
                row = self.table.rowCount()
                self.table.insertRow(row)
                goal_label = f"{g.goal_type}  ✓" if g.is_completed else g.goal_type
                self.table.setItem(row, 0, QTableWidgetItem(goal_label))
                self.table.setItem(row, 1, QTableWidgetItem(g.description or ""))

                pbar = QProgressBar()
                pbar.setMaximum(100)
                val = min(100, int((g.current_value or 0) / (g.target_value or 1) * 100))
                pbar.setValue(val)
                pbar.setFixedHeight(12)
                pbar.setTextVisible(False)
                if g.is_completed:
                    pbar.setStyleSheet(
                        "QProgressBar {"
                        "background-color: #1b2237;"
                        "border: none;"
                        "border-radius: 6px;"
                        "}" 
                        "QProgressBar::chunk {"
                        "background-color: #22c55e;"
                        "border-radius: 6px;"
                        "}"
                    )
                self.table.setCellWidget(row, 2, pbar)

                self.table.setItem(row, 3, QTableWidgetItem(
                    f"{g.current_value or 0:.1f} {g.unit or ''}"
                ))
                self.table.setItem(row, 4, QTableWidgetItem(
                    f"{g.target_value or 0:.1f} {g.unit or ''}"
                ))
                due = g.target_date.strftime("%b %d, %Y") if g.target_date else "—"
                self.table.setItem(row, 5, QTableWidgetItem(due))

                status = "Completed" if g.is_completed else "Active"
                for col in range(0, 6):
                    item = self.table.item(row, col)
                    if item:
                        item.setToolTip(status)
                        if g.is_completed:
                            item.setBackground(QColor("#10261f"))
                            item.setForeground(QColor("#bbf7d0"))

                action_w = QWidget()
                action_w.setObjectName("tableActionCell")
                action_w.setMinimumHeight(34)
                al = QHBoxLayout(action_w)
                al.setContentsMargins(6, 4, 6, 4)
                al.setSpacing(8)
                al.setAlignment(Qt.AlignmentFlag.AlignCenter)

                edit_btn = QPushButton("Edit")
                edit_btn.setObjectName("tableEditBtn")
                edit_btn.setFixedSize(62, 30)
                edit_btn.clicked.connect(lambda c, gid=g.id: self._edit_goal(gid))
                al.addWidget(edit_btn)

                del_btn = QPushButton("Delete")
                del_btn.setObjectName("tableDeleteBtn")
                del_btn.setFixedSize(76, 30)
                del_btn.clicked.connect(lambda c, gid=g.id: self._delete_goal(gid))
                al.addWidget(del_btn)

                self.table.setCellWidget(row, 6, action_w)
                self.table.setRowHeight(row, 48)
        finally:
            session.close()

    def _add_goal(self):
        dlg = GoalDialog(self.user, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._load_data()

    def _edit_goal(self, goal_id):
        session = SessionLocal()
        try:
            g = session.query(FitnessGoal).get(goal_id)
            if g:
                dlg = GoalDialog(self.user, g, parent=self)
                if dlg.exec() == QDialog.DialogCode.Accepted:
                    self._load_data()
        finally:
            session.close()

    def _delete_goal(self, goal_id):
        reply = QMessageBox.question(self, "Delete", "Delete this goal?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            session = SessionLocal()
            try:
                g = session.query(FitnessGoal).get(goal_id)
                if g:
                    session.delete(g)
                    session.commit()
                    self._load_data()
            finally:
                session.close()


# ══════════════════════════════════════════════════════════════════════════════
#  MEASUREMENTS VIEW
# ══════════════════════════════════════════════════════════════════════════════

class MeasurementDialog(QDialog):
    def __init__(self, user: User, meas: BodyMeasurement = None, parent=None):
        super().__init__(parent)
        self.user = user
        self.meas = meas
        self.setWindowTitle("Edit Measurement" if meas else "Log Measurement")
        self.setMinimumWidth(380)
        self.setModal(True)
        self._build_ui()
        if meas:
            self._populate()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("Body Measurements")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)

        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        form.addRow("Date *", self.date_edit)

        def make_spin(suffix=""):
            s = QDoubleSpinBox()
            s.setRange(0, 999)
            s.setDecimals(1)
            if suffix:
                s.setSuffix(f" {suffix}")
            return s

        self.weight_spin = make_spin("kg")
        form.addRow("Weight", self.weight_spin)

        self.bodyfat_spin = make_spin("%")
        self.bodyfat_spin.setRange(0, 60)
        form.addRow("Body Fat %", self.bodyfat_spin)

        self.muscle_spin = make_spin("kg")
        form.addRow("Muscle Mass", self.muscle_spin)

        self.chest_spin = make_spin("cm")
        form.addRow("Chest", self.chest_spin)

        self.waist_spin = make_spin("cm")
        form.addRow("Waist", self.waist_spin)

        self.hips_spin = make_spin("cm")
        form.addRow("Hips", self.hips_spin)

        self.notes_edit = QLineEdit()
        self.notes_edit.setPlaceholderText("Optional notes...")
        form.addRow("Notes", self.notes_edit)

        layout.addLayout(form)

        btn_row = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("secondaryButton")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()
        save_btn = QPushButton("Save")
        save_btn.setObjectName("successButton")
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def _populate(self):
        m = self.meas
        self.date_edit.setDate(QDate(m.date.year, m.date.month, m.date.day))
        self.weight_spin.setValue(m.weight_kg or 0)
        self.bodyfat_spin.setValue(m.body_fat_percent or 0)
        self.muscle_spin.setValue(m.muscle_mass_kg or 0)
        self.chest_spin.setValue(m.chest_cm or 0)
        self.waist_spin.setValue(m.waist_cm or 0)
        self.hips_spin.setValue(m.hips_cm or 0)
        self.notes_edit.setText(m.notes or "")

    def _save(self):
        qd = self.date_edit.date()
        meas_date = date(qd.year(), qd.month(), qd.day())
        session = SessionLocal()
        try:
            if self.meas:
                m = session.merge(self.meas)
            else:
                m = BodyMeasurement(user_id=self.user.id)
                session.add(m)

            m.date = meas_date
            m.weight_kg = self.weight_spin.value() or None
            m.body_fat_percent = self.bodyfat_spin.value() or None
            m.muscle_mass_kg = self.muscle_spin.value() or None
            m.chest_cm = self.chest_spin.value() or None
            m.waist_cm = self.waist_spin.value() or None
            m.hips_cm = self.hips_spin.value() or None
            m.notes = self.notes_edit.text().strip() or None

            session.commit()

            # Update current_value of relevant goals
            goals = session.query(FitnessGoal).filter_by(
                user_id=self.user.id, is_completed=False
            ).all()
            for g in goals:
                if g.goal_type in ("Lose Weight", "Maintain Weight") and m.weight_kg:
                    g.current_value = m.weight_kg
            session.commit()
            self.accept()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", str(e))
        finally:
            session.close()


class MeasurementsView(QWidget):
    def __init__(self, user: User):
        super().__init__()
        self.user = user
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header = QHBoxLayout()
        title = QLabel("Body Measurements")
        title.setObjectName("pageTitle")
        header.addWidget(title)
        header.addStretch()
        add_btn = QPushButton("+ Log Measurement")
        add_btn.setObjectName("successButton")
        add_btn.clicked.connect(self._add_meas)
        header.addWidget(add_btn)
        layout.addLayout(header)

        # Weight trend chart placeholder
        self.chart_frame = QFrame()
        self.chart_frame.setObjectName("card")
        self.chart_frame.setMinimumHeight(200)
        self.chart_layout = QVBoxLayout(self.chart_frame)
        self.chart_layout.setContentsMargins(10, 10, 10, 10)
        self.chart_layout.setSpacing(0)
        layout.addWidget(self.chart_frame)

        # Table
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Date", "Weight (kg)", "Body Fat %", "Muscle (kg)", "Waist (cm)", "Notes", "Actions"]
        )
        mhdr = self.table.horizontalHeader()
        mhdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        mhdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        mhdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        mhdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        mhdr.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        mhdr.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        mhdr.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 110)   # Date
        self.table.setColumnWidth(1, 100)   # Weight
        self.table.setColumnWidth(2, 100)   # Body Fat
        self.table.setColumnWidth(3, 100)   # Muscle
        self.table.setColumnWidth(4, 100)   # Waist
        self.table.setColumnWidth(6, 184)   # Actions
        self.table.verticalHeader().setDefaultSectionSize(48)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

    def _load_data(self):
        session = SessionLocal()
        try:
            measurements = session.query(BodyMeasurement).filter_by(
                user_id=self.user.id
            ).order_by(BodyMeasurement.date.desc()).all()

            # Update chart
            self._build_weight_chart(measurements)

            self.table.setRowCount(0)
            for m in measurements:
                row = self.table.rowCount()
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(m.date.strftime("%b %d, %Y")))
                self.table.setItem(row, 1, QTableWidgetItem(f"{m.weight_kg:.1f}" if m.weight_kg else "—"))
                self.table.setItem(row, 2, QTableWidgetItem(f"{m.body_fat_percent:.1f}%" if m.body_fat_percent else "—"))
                self.table.setItem(row, 3, QTableWidgetItem(f"{m.muscle_mass_kg:.1f}" if m.muscle_mass_kg else "—"))
                self.table.setItem(row, 4, QTableWidgetItem(f"{m.waist_cm:.1f}" if m.waist_cm else "—"))
                self.table.setItem(row, 5, QTableWidgetItem(m.notes or ""))

                action_w = QWidget()
                action_w.setObjectName("tableActionCell")
                action_w.setMinimumHeight(34)
                al = QHBoxLayout(action_w)
                al.setContentsMargins(6, 4, 6, 4)
                al.setSpacing(8)
                al.setAlignment(Qt.AlignmentFlag.AlignCenter)
                edit_btn = QPushButton("Edit")
                edit_btn.setObjectName("tableEditBtn")
                edit_btn.setFixedSize(62, 30)
                edit_btn.clicked.connect(lambda c, mid=m.id: self._edit_meas(mid))
                al.addWidget(edit_btn)
                del_btn = QPushButton("Delete")
                del_btn.setObjectName("tableDeleteBtn")
                del_btn.setFixedSize(76, 30)
                del_btn.clicked.connect(lambda c, mid=m.id: self._delete_meas(mid))
                al.addWidget(del_btn)
                self.table.setCellWidget(row, 6, action_w)
                self.table.setRowHeight(row, 48)
        finally:
            session.close()

    def _build_weight_chart(self, measurements):
        for i in reversed(range(self.chart_layout.count())):
            w = self.chart_layout.itemAt(i).widget()
            if w:
                w.deleteLater()

        data = [(m.date, m.weight_kg) for m in reversed(measurements) if m.weight_kg]
        if len(data) < 2:
            lbl = QLabel("Log at least 2 weight measurements to see the trend chart.")
            lbl.setStyleSheet("color: #64748b; text-align: center;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.chart_layout.addWidget(lbl)
            return

        series = QSplineSeries()
        series.setColor(QColor("#6366f1"))

        from PyQt6.QtCore import QDateTime
        for idx, (d, w) in enumerate(data):
            # Offset each point by a minute so same-day measurements are still visible.
            qdt = QDateTime(d.year, d.month, d.day, 0, 0, 0).addSecs(idx * 60)
            series.append(qdt.toMSecsSinceEpoch(), w)

        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("Weight Trend (kg)")
        chart.setTitleFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        chart.setBackgroundVisible(False)
        chart.setMargins(QMargins(10, 8, 10, 8))
        chart.setPlotAreaBackgroundVisible(True)
        chart.setPlotAreaBackgroundBrush(QBrush(QColor("#141828")))
        chart.setTitleBrush(QBrush(QColor("#e2e8f0")))

        axis_x = QDateTimeAxis()
        axis_x.setFormat("MMM dd")
        axis_x.setLabelsColor(QColor("#94a3b8"))
        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(axis_x)

        axis_y = QValueAxis()
        axis_y.setLabelsColor(QColor("#94a3b8"))
        axis_y.setGridLineColor(QColor("#2d3748"))
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_y)

        chart.legend().setVisible(False)

        view = QChartView(chart)
        view.setRenderHint(QPainter.RenderHint.Antialiasing)
        view.setStyleSheet("background: transparent; border: none;")
        self.chart_layout.addWidget(view)

    def _add_meas(self):
        dlg = MeasurementDialog(self.user, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._load_data()

    def _edit_meas(self, mid):
        session = SessionLocal()
        try:
            m = session.query(BodyMeasurement).get(mid)
            if m:
                dlg = MeasurementDialog(self.user, m, parent=self)
                if dlg.exec() == QDialog.DialogCode.Accepted:
                    self._load_data()
        finally:
            session.close()

    def _delete_meas(self, mid):
        reply = QMessageBox.question(self, "Delete", "Delete this measurement?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            session = SessionLocal()
            try:
                m = session.query(BodyMeasurement).get(mid)
                if m:
                    session.delete(m)
                    session.commit()
                    self._load_data()
            finally:
                session.close()


# ══════════════════════════════════════════════════════════════════════════════
#  NOTIFICATIONS VIEW
# ══════════════════════════════════════════════════════════════════════════════

class NotificationsView(QWidget):
    def __init__(self, user: User):
        super().__init__()
        self.user = user
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header = QHBoxLayout()
        title = QLabel("Notifications & Reminders")
        title.setObjectName("pageTitle")
        header.addWidget(title)
        header.addStretch()
        add_btn = QPushButton("+ Add Reminder")
        add_btn.setObjectName("successButton")
        add_btn.clicked.connect(self._add_notif)
        header.addWidget(add_btn)
        mark_all_btn = QPushButton("Mark All Read")
        mark_all_btn.setObjectName("secondaryButton")
        mark_all_btn.clicked.connect(self._mark_all_read)
        header.addWidget(mark_all_btn)
        layout.addLayout(header)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Type", "Title", "Message", "Scheduled", "Status"])
        nhdr = self.table.horizontalHeader()
        nhdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        nhdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        nhdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        nhdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        nhdr.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 100)   # Type
        self.table.setColumnWidth(1, 230)   # Title
        self.table.setColumnWidth(3, 140)   # Scheduled
        self.table.setColumnWidth(4, 100)   # Status
        self.table.setWordWrap(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

    def _load_data(self):
        session = SessionLocal()
        try:
            notifs = session.query(Notification).filter_by(
                user_id=self.user.id
            ).order_by(Notification.created_at.desc()).limit(50).all()

            self.table.setRowCount(0)
            for n in notifs:
                row = self.table.rowCount()
                self.table.insertRow(row)

                type_icons = {"Workout": "🏋️", "Meal": "🍽️", "Measurement": "📏", "General": "🔔"}
                self.table.setItem(row, 0, QTableWidgetItem(
                    f"{type_icons.get(n.reminder_type, '🔔')} {n.reminder_type}"
                ))
                self.table.setItem(row, 1, QTableWidgetItem(n.title))
                self.table.setItem(row, 2, QTableWidgetItem(n.message))
                sched = n.scheduled_at.strftime("%b %d %H:%M") if n.scheduled_at else "—"
                self.table.setItem(row, 3, QTableWidgetItem(sched))

                status = "✅ Read" if n.is_read else "🔔 Unread"
                status_item = QTableWidgetItem(status)
                if not n.is_read:
                    status_item.setForeground(QColor("#6366f1"))
                self.table.setItem(row, 4, status_item)
                for col in range(0, 5):
                    item = self.table.item(row, col)
                    if item:
                        item.setToolTip(item.text())
                self.table.setRowHeight(row, 46)
        finally:
            session.close()

    def _add_notif(self):
        dlg = _NotifDialog(self.user, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._load_data()

    def _mark_all_read(self):
        session = SessionLocal()
        try:
            session.query(Notification).filter_by(
                user_id=self.user.id, is_read=False
            ).update({"is_read": True})
            session.commit()
            self._load_data()
        finally:
            session.close()


class _NotifDialog(QDialog):
    def __init__(self, user: User, parent=None):
        super().__init__(parent)
        self.user = user
        self.setWindowTitle("Add Reminder")
        self.setMinimumWidth(380)
        self.setModal(True)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("Add Reminder / Notification")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        form = QFormLayout()
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Workout", "Meal", "Measurement", "General"])
        form.addRow("Type", self.type_combo)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("e.g., Evening Run")
        form.addRow("Title *", self.title_edit)

        self.msg_edit = QTextEdit()
        self.msg_edit.setMaximumHeight(80)
        self.msg_edit.setPlaceholderText("Reminder message...")
        form.addRow("Message *", self.msg_edit)

        from PyQt6.QtWidgets import QDateTimeEdit
        from PyQt6.QtCore import QDateTime
        self.dt_edit = QDateTimeEdit()
        self.dt_edit.setDateTime(QDateTime.currentDateTime())
        self.dt_edit.setCalendarPopup(True)
        form.addRow("Scheduled At", self.dt_edit)

        layout.addLayout(form)

        btn_row = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("secondaryButton")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()
        save_btn = QPushButton("Save Reminder")
        save_btn.setObjectName("successButton")
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def _save(self):
        title = self.title_edit.text().strip()
        msg = self.msg_edit.toPlainText().strip()
        if not title or not msg:
            QMessageBox.warning(self, "Validation", "Title and message are required.")
            return
        session = SessionLocal()
        try:
            from datetime import datetime
            qdt = self.dt_edit.dateTime()
            scheduled = datetime(
                qdt.date().year(), qdt.date().month(), qdt.date().day(),
                qdt.time().hour(), qdt.time().minute()
            )
            notif = Notification(
                user_id=self.user.id,
                title=title,
                message=msg,
                reminder_type=self.type_combo.currentText(),
                scheduled_at=scheduled,
            )
            session.add(notif)
            session.commit()
            self.accept()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", str(e))
        finally:
            session.close()


# ══════════════════════════════════════════════════════════════════════════════
#  COACH DASHBOARD VIEW
# ══════════════════════════════════════════════════════════════════════════════

class CoachDashboardView(QWidget):
    def __init__(self, user: User):
        super().__init__()
        self.user = user
        self._selected_client_id = None
        self._build_ui()
        self._load_clients()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("Coach Dashboard")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        subtitle = QLabel("Monitor client activity, review trends, and export progress reports.")
        subtitle.setStyleSheet("color: #64748b;")
        layout.addWidget(subtitle)

        content = QHBoxLayout()
        content.setSpacing(16)

        # Client list
        left_panel = QFrame()
        left_panel.setObjectName("card")
        left_panel.setFixedWidth(220)
        left_layout = QVBoxLayout(left_panel)

        clients_title = QLabel("MY CLIENTS")
        clients_title.setObjectName("cardTitle")
        left_layout.addWidget(clients_title)

        self.clients_table = QTableWidget(0, 1)
        self.clients_table.setHorizontalHeaderLabels(["Name"])
        self.clients_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.clients_table.verticalHeader().setVisible(False)
        self.clients_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.clients_table.cellClicked.connect(self._on_client_selected)
        left_layout.addWidget(self.clients_table)
        content.addWidget(left_panel)

        # Client detail
        right_panel = QVBoxLayout()
        right_panel.setSpacing(12)

        self.client_name_lbl = QLabel("Select a client")
        self.client_name_lbl.setObjectName("pageTitle")
        right_panel.addWidget(self.client_name_lbl)

        # Summary cards
        cards_row = QHBoxLayout()
        cards_row.setSpacing(12)
        self.c_workouts = _MiniCard("Workouts This Month", "—", "#6366f1")
        self.c_calories = _MiniCard("Avg Calories/Day", "—", "#ef4444")
        self.c_weight = _MiniCard("Weight Change", "—", "#10b981")
        self.c_streak = _MiniCard("Streak", "—", "#f59e0b")
        cards_row.addWidget(self.c_workouts)
        cards_row.addWidget(self.c_calories)
        cards_row.addWidget(self.c_weight)
        cards_row.addWidget(self.c_streak)
        right_panel.addLayout(cards_row)

        # Recent workouts of client
        recent_lbl = QLabel("Recent Workouts")
        recent_lbl.setObjectName("sectionHeader")
        right_panel.addWidget(recent_lbl)

        self.client_workouts_table = QTableWidget(0, 4)
        self.client_workouts_table.setHorizontalHeaderLabels(["Date", "Workout", "Type", "Duration"])
        self.client_workouts_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.client_workouts_table.verticalHeader().setVisible(False)
        self.client_workouts_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.client_workouts_table.setMaximumHeight(200)
        right_panel.addWidget(self.client_workouts_table)

        # Export button
        export_row = QHBoxLayout()
        export_row.addStretch()

        export_csv_btn = QPushButton("📤 Export Progress CSV")
        export_csv_btn.setObjectName("secondaryButton")
        export_csv_btn.clicked.connect(lambda: self._export_report("csv"))
        export_row.addWidget(export_csv_btn)

        export_pdf_btn = QPushButton("📄 Export Progress PDF")
        export_pdf_btn.clicked.connect(lambda: self._export_report("pdf"))
        export_row.addWidget(export_pdf_btn)

        right_panel.addLayout(export_row)

        content.addLayout(right_panel, 1)
        layout.addLayout(content)

    def _load_clients(self):
        session = SessionLocal()
        try:
            clients = session.query(User).filter_by(coach_id=self.user.id, is_active=True).all()
            self.clients_table.setRowCount(0)
            self._client_ids = []
            for c in clients:
                row = self.clients_table.rowCount()
                self.clients_table.insertRow(row)
                self.clients_table.setItem(row, 0, QTableWidgetItem(c.full_name or c.username))
                self._client_ids.append(c.id)
                self.clients_table.setRowHeight(row, 38)
        finally:
            session.close()

    def _on_client_selected(self, row, col):
        if row < len(self._client_ids):
            self._selected_client_id = self._client_ids[row]
            self._load_client_data(self._selected_client_id)

    def _load_client_data(self, client_id: int):
        session = SessionLocal()
        try:
            client = session.query(User).get(client_id)
            if not client:
                return

            self.client_name_lbl.setText(f"{client.full_name or client.username}")

            analyser = ProgressAnalyser(session)
            today = date.today()
            month_start = today.replace(day=1)

            # Workouts this month
            monthly = session.query(WorkoutSession).filter(
                WorkoutSession.user_id == client_id,
                WorkoutSession.date >= month_start
            ).count()
            self.c_workouts.set_value(str(monthly))

            # Avg calories
            summary = analyser.get_weekly_summary(client_id)
            self.c_calories.set_value(f"{summary['avg_daily_calories_in']:.0f}")

            # Weight change
            wc = analyser.compare_weight_change(client_id, month_start, today)
            change = wc.get("change_kg", 0)
            color = "#10b981" if change <= 0 else "#ef4444"
            sign = "+" if change > 0 else ""
            self.c_weight.set_value(f"{sign}{change:.1f} kg", color)

            # Streak
            streak = analyser.get_workout_streak(client_id)
            self.c_streak.set_value(f"{streak} 🔥")

            # Recent workouts
            recent = session.query(WorkoutSession).filter_by(
                user_id=client_id
            ).order_by(WorkoutSession.date.desc()).limit(8).all()

            self.client_workouts_table.setRowCount(0)
            for w in recent:
                row = self.client_workouts_table.rowCount()
                self.client_workouts_table.insertRow(row)
                self.client_workouts_table.setItem(row, 0, QTableWidgetItem(w.date.strftime("%b %d")))
                self.client_workouts_table.setItem(row, 1, QTableWidgetItem(w.name))
                self.client_workouts_table.setItem(row, 2, QTableWidgetItem(w.activity_type))
                self.client_workouts_table.setItem(row, 3, QTableWidgetItem(f"{w.duration_minutes} min"))
                self.client_workouts_table.setRowHeight(row, 36)
        finally:
            session.close()

    def _export_report(self, fmt: str):
        if not self._selected_client_id:
            QMessageBox.information(self, "Export", "Please select a client first.")
            return

        session = SessionLocal()
        try:
            analyser = ProgressAnalyser(session)
            today = date.today()
            month_start = today.replace(day=1)

            report = analyser.generate_progress_report(
                self._selected_client_id, month_start, today, self.user.id
            )
            client = session.query(User).get(self._selected_client_id)

            if fmt == "csv":
                path, _ = QFileDialog.getSaveFileName(
                    self, "Save CSV", f"{client.username}_progress.csv", "CSV Files (*.csv)"
                )
                if path:
                    with open(path, "w", newline="") as f:
                        writer = csv.writer(f)
                        writer.writerow(["FitTrack Pro — Progress Report"])
                        writer.writerow(["Client", client.full_name or client.username])
                        writer.writerow(["Period", f"{report.period_start} to {report.period_end}"])
                        writer.writerow([])
                        writer.writerow(["Metric", "Value"])
                        writer.writerow(["Total Workouts", report.total_workouts])
                        writer.writerow(["Total Workout Minutes", report.total_workout_minutes])
                        writer.writerow(["Total Calories Burned", f"{report.total_calories_burned:.0f}"])
                        writer.writerow(["Avg Daily Calories In", f"{report.avg_daily_calories_in:.0f}"])
                        writer.writerow(["Weight Change (kg)", f"{report.weight_change_kg:+.2f}"])
                    QMessageBox.information(self, "Exported", f"Report saved to:\n{path}")

            elif fmt == "pdf":
                path, _ = QFileDialog.getSaveFileName(
                    self, "Save PDF", f"{client.username}_progress.pdf", "PDF Files (*.pdf)"
                )
                if path:
                    self._write_pdf(path, client, report)
                    QMessageBox.information(self, "Exported", f"PDF report saved to:\n{path}")

        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))
        finally:
            session.close()

    def _write_pdf(self, path: str, client, report):
        """Write a simple HTML-based PDF using Qt printing."""
        from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
        from PyQt6.QtWidgets import QTextEdit
        from PyQt6.QtCore import QMarginsF

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(path)
        printer.setPageMargins(QMarginsF(15, 15, 15, 15), __import__("PyQt6.QtGui", fromlist=["QPageLayout"]).QPageLayout.Unit.Millimeter)

        doc = QTextEdit()
        html = f"""
        <html><body style="font-family: Arial; color: #1a1d2e;">
        <h1 style="color: #6366f1;">FitTrack Pro — Progress Report</h1>
        <h2>{client.full_name or client.username}</h2>
        <p><b>Period:</b> {report.period_start} to {report.period_end}</p>
        <hr>
        <table border="1" cellpadding="8" width="100%">
        <tr style="background: #6366f1; color: white;"><th>Metric</th><th>Value</th></tr>
        <tr><td>Total Workouts</td><td>{report.total_workouts}</td></tr>
        <tr><td>Total Workout Minutes</td><td>{report.total_workout_minutes}</td></tr>
        <tr><td>Total Calories Burned</td><td>{report.total_calories_burned:.0f} kcal</td></tr>
        <tr><td>Avg Daily Calories In</td><td>{report.avg_daily_calories_in:.0f} kcal</td></tr>
        <tr><td>Weight Change</td><td>{report.weight_change_kg:+.2f} kg</td></tr>
        </table>
        <br><p style="color: gray; font-size: 10pt;">Generated by FitTrack Pro</p>
        </body></html>
        """
        doc.setHtml(html)
        doc.print(printer)


class _MiniCard(QFrame):
    def __init__(self, title: str, value: str, color: str = "#6366f1"):
        super().__init__()
        self.setObjectName("card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        self.value_lbl = QLabel(value)
        self.value_lbl.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {color};")
        layout.addWidget(self.value_lbl)
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color: #64748b; font-size: 11px;")
        title_lbl.setWordWrap(True)
        layout.addWidget(title_lbl)

    def set_value(self, value: str, color: str = None):
        self.value_lbl.setText(value)
        if color:
            self.value_lbl.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {color};")
