"""
FitTrack Pro - Workout Sessions View
Full CRUD for workout sessions with exercise tracking
"""

from datetime import date
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QDialog, QFormLayout,
    QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QDateEdit,
    QTextEdit, QFrame, QHeaderView, QMessageBox, QScrollArea,
    QGroupBox
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont

from models.database import SessionLocal, User, WorkoutSession, Exercise
from models.services import CalorieCalculator


ACTIVITY_TYPES = ["Cardio", "Strength Training", "HIIT", "Yoga", "Sports", "Other"]


# ─── Add/Edit Workout Dialog ──────────────────────────────────────────────────

class WorkoutDialog(QDialog):
    def __init__(self, user: User, workout: WorkoutSession = None, parent=None):
        super().__init__(parent)
        self.user = user
        self.workout = workout
        self.setWindowTitle("Edit Workout" if workout else "Log New Workout")
        self.setMinimumWidth(480)
        self.setModal(True)
        self._build_ui()
        if workout:
            self._populate()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("Edit Workout" if self.workout else "Log New Workout")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(12)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., Morning Run, Upper Body Strength")
        form.addRow("Workout Name *", self.name_edit)

        self.type_combo = QComboBox()
        self.type_combo.addItems(ACTIVITY_TYPES)
        self.type_combo.currentTextChanged.connect(self._auto_calories)
        form.addRow("Activity Type *", self.type_combo)

        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        form.addRow("Date *", self.date_edit)

        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(1, 600)
        self.duration_spin.setValue(30)
        self.duration_spin.setSuffix(" minutes")
        self.duration_spin.valueChanged.connect(self._auto_calories)
        form.addRow("Duration *", self.duration_spin)

        self.calories_spin = QDoubleSpinBox()
        self.calories_spin.setRange(0, 5000)
        self.calories_spin.setDecimals(0)
        self.calories_spin.setSuffix(" kcal")
        form.addRow("Calories Burned", self.calories_spin)

        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(80)
        self.notes_edit.setPlaceholderText("Optional notes about this session...")
        form.addRow("Notes", self.notes_edit)

        layout.addLayout(form)

        # Exercises section
        ex_group = QGroupBox("Exercises (Optional)")
        ex_layout = QVBoxLayout(ex_group)

        self.exercise_table = QTableWidget(0, 5)
        self.exercise_table.setHorizontalHeaderLabels(["Exercise", "Sets", "Reps", "Weight (kg)", "Duration (s)"])
        self.exercise_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.exercise_table.setMinimumHeight(120)
        ex_layout.addWidget(self.exercise_table)

        add_ex_btn = QPushButton("+ Add Exercise")
        add_ex_btn.setObjectName("secondaryButton")
        add_ex_btn.clicked.connect(self._add_exercise_row)
        ex_layout.addWidget(add_ex_btn)

        layout.addWidget(ex_group)

        # Buttons
        btn_row = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("secondaryButton")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()

        save_btn = QPushButton("Save Workout")
        save_btn.setObjectName("successButton")
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

        self._auto_calories()

    def _auto_calories(self):
        activity = self.type_combo.currentText()
        duration = self.duration_spin.value()
        # Use average weight of 75kg for estimate
        estimated = CalorieCalculator.calculate_calories_burned(activity, duration, 75.0)
        self.calories_spin.setValue(estimated)

    def _add_exercise_row(self):
        row = self.exercise_table.rowCount()
        self.exercise_table.insertRow(row)
        self.exercise_table.setItem(row, 0, QTableWidgetItem(""))
        for col in range(1, 5):
            item = QTableWidgetItem("0")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.exercise_table.setItem(row, col, item)

    def _populate(self):
        w = self.workout
        self.name_edit.setText(w.name)
        idx = ACTIVITY_TYPES.index(w.activity_type) if w.activity_type in ACTIVITY_TYPES else 0
        self.type_combo.setCurrentIndex(idx)
        self.date_edit.setDate(QDate(w.date.year, w.date.month, w.date.day))
        self.duration_spin.setValue(w.duration_minutes or 30)
        self.calories_spin.setValue(w.calories_burned or 0)
        if w.notes:
            self.notes_edit.setText(w.notes)

        for ex in w.exercises:
            row = self.exercise_table.rowCount()
            self.exercise_table.insertRow(row)
            self.exercise_table.setItem(row, 0, QTableWidgetItem(ex.name))
            self.exercise_table.setItem(row, 1, QTableWidgetItem(str(ex.sets or 0)))
            self.exercise_table.setItem(row, 2, QTableWidgetItem(str(ex.reps or 0)))
            self.exercise_table.setItem(row, 3, QTableWidgetItem(str(ex.weight_kg or 0)))
            self.exercise_table.setItem(row, 4, QTableWidgetItem(str(ex.duration_seconds or 0)))

    def _save(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation", "Workout name is required.")
            return

        qdate = self.date_edit.date()
        workout_date = date(qdate.year(), qdate.month(), qdate.day())

        session = SessionLocal()
        try:
            if self.workout:
                w = session.merge(self.workout)
            else:
                w = WorkoutSession(user_id=self.user.id)
                session.add(w)

            w.name = name
            w.activity_type = self.type_combo.currentText()
            w.date = workout_date
            w.duration_minutes = self.duration_spin.value()
            w.calories_burned = self.calories_spin.value()
            w.notes = self.notes_edit.toPlainText().strip() or None
            session.flush()

            # Save exercises
            if self.workout:
                session.query(Exercise).filter_by(workout_session_id=w.id).delete()

            for row in range(self.exercise_table.rowCount()):
                ex_name = self.exercise_table.item(row, 0)
                if ex_name and ex_name.text().strip():
                    ex = Exercise(
                        workout_session_id=w.id,
                        name=ex_name.text().strip(),
                        sets=int(self.exercise_table.item(row, 1).text() or 0),
                        reps=int(self.exercise_table.item(row, 2).text() or 0),
                        weight_kg=float(self.exercise_table.item(row, 3).text() or 0),
                        duration_seconds=int(self.exercise_table.item(row, 4).text() or 0),
                    )
                    session.add(ex)

            session.commit()

            # Check for badges
            from models.services import BadgeService
            BadgeService(session).check_and_award_badges(self.user.id)

            self.accept()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", str(e))
        finally:
            session.close()


# ─── Workout View ─────────────────────────────────────────────────────────────

class WorkoutView(QWidget):
    def __init__(self, user: User):
        super().__init__()
        self.user = user
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        header = QHBoxLayout()
        title = QLabel("Workout Sessions")
        title.setObjectName("pageTitle")
        header.addWidget(title)
        header.addStretch()

        add_btn = QPushButton("+ Log Workout")
        add_btn.setObjectName("successButton")
        add_btn.clicked.connect(self._add_workout)
        header.addWidget(add_btn)
        layout.addLayout(header)

        # Filter row
        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)

        self.filter_type = QComboBox()
        self.filter_type.addItems(["All Types"] + ACTIVITY_TYPES)
        self.filter_type.currentIndexChanged.connect(self._load_data)
        filter_row.addWidget(QLabel("Type:"))
        filter_row.addWidget(self.filter_type)

        filter_row.addSpacing(16)

        self.filter_month = QComboBox()
        self.filter_month.addItems(["All Time", "This Month", "Last 7 Days", "Last 30 Days"])
        self.filter_month.currentIndexChanged.connect(self._load_data)
        filter_row.addWidget(QLabel("Period:"))
        filter_row.addWidget(self.filter_month)

        filter_row.addStretch()
        layout.addLayout(filter_row)

        # Summary cards
        summary_row = QHBoxLayout()
        summary_row.setSpacing(12)

        self.total_sessions_card = QFrame()
        self.total_sessions_card.setObjectName("card")
        tl = QVBoxLayout(self.total_sessions_card)
        self.total_sessions_lbl = QLabel("0")
        self.total_sessions_lbl.setStyleSheet("font-size: 24px; font-weight: bold; color: #6366f1;")
        tl.addWidget(self.total_sessions_lbl)
        tl.addWidget(QLabel("Total Sessions"))
        summary_row.addWidget(self.total_sessions_card)

        self.total_mins_card = QFrame()
        self.total_mins_card.setObjectName("card")
        ml = QVBoxLayout(self.total_mins_card)
        self.total_mins_lbl = QLabel("0")
        self.total_mins_lbl.setStyleSheet("font-size: 24px; font-weight: bold; color: #10b981;")
        ml.addWidget(self.total_mins_lbl)
        ml.addWidget(QLabel("Total Minutes"))
        summary_row.addWidget(self.total_mins_card)

        self.total_cal_card = QFrame()
        self.total_cal_card.setObjectName("card")
        cl = QVBoxLayout(self.total_cal_card)
        self.total_cal_lbl = QLabel("0")
        self.total_cal_lbl.setStyleSheet("font-size: 24px; font-weight: bold; color: #ef4444;")
        cl.addWidget(self.total_cal_lbl)
        cl.addWidget(QLabel("Total kcal Burned"))
        summary_row.addWidget(self.total_cal_card)

        layout.addLayout(summary_row)

        # Table
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Date", "Workout", "Type", "Duration", "Calories", "Actions"])
        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 110)   # Date
        self.table.setColumnWidth(2, 130)   # Type
        self.table.setColumnWidth(3, 100)   # Duration
        self.table.setColumnWidth(4, 110)   # Calories
        self.table.setColumnWidth(5, 184)   # Actions
        self.table.verticalHeader().setDefaultSectionSize(48)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(False)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

    def _get_filter_date(self):
        idx = self.filter_month.currentIndex()
        today = date.today()
        if idx == 1:
            return today.replace(day=1)
        elif idx == 2:
            return today - __import__("datetime").timedelta(days=7)
        elif idx == 3:
            return today - __import__("datetime").timedelta(days=30)
        return None

    def _load_data(self):
        session = SessionLocal()
        try:
            query = session.query(WorkoutSession).filter_by(user_id=self.user.id)

            ftype = self.filter_type.currentText()
            if ftype != "All Types":
                query = query.filter(WorkoutSession.activity_type == ftype)

            fdate = self._get_filter_date()
            if fdate:
                query = query.filter(WorkoutSession.date >= fdate)

            workouts = query.order_by(WorkoutSession.date.desc()).all()

            # Update summary
            total_mins = sum(w.duration_minutes or 0 for w in workouts)
            total_cal = sum(w.calories_burned or 0 for w in workouts)
            self.total_sessions_lbl.setText(str(len(workouts)))
            self.total_mins_lbl.setText(str(total_mins))
            self.total_cal_lbl.setText(f"{total_cal:.0f}")

            # Populate table
            self.table.setRowCount(0)
            for w in workouts:
                row = self.table.rowCount()
                self.table.insertRow(row)

                self.table.setItem(row, 0, QTableWidgetItem(w.date.strftime("%b %d, %Y")))
                self.table.setItem(row, 1, QTableWidgetItem(w.name))
                self.table.setItem(row, 2, QTableWidgetItem(w.activity_type))
                self.table.setItem(row, 3, QTableWidgetItem(f"{w.duration_minutes} min"))
                self.table.setItem(row, 4, QTableWidgetItem(f"{w.calories_burned or 0:.0f} kcal"))

                # Action buttons
                action_widget = QWidget()
                action_widget.setObjectName("tableActionCell")
                action_widget.setMinimumHeight(34)
                action_layout = QHBoxLayout(action_widget)
                action_layout.setContentsMargins(6, 4, 6, 4)
                action_layout.setSpacing(8)
                action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

                edit_btn = QPushButton("Edit")
                edit_btn.setObjectName("tableEditBtn")
                edit_btn.setFixedSize(62, 30)
                edit_btn.clicked.connect(lambda checked, wid=w.id: self._edit_workout(wid))
                action_layout.addWidget(edit_btn)

                del_btn = QPushButton("Delete")
                del_btn.setObjectName("tableDeleteBtn")
                del_btn.setFixedSize(76, 30)
                del_btn.clicked.connect(lambda checked, wid=w.id: self._delete_workout(wid))
                action_layout.addWidget(del_btn)

                self.table.setCellWidget(row, 5, action_widget)
                self.table.setRowHeight(row, 48)

        finally:
            session.close()

    def _add_workout(self):
        dlg = WorkoutDialog(self.user, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._load_data()

    def _edit_workout(self, workout_id: int):
        session = SessionLocal()
        try:
            w = session.query(WorkoutSession).get(workout_id)
            if w:
                dlg = WorkoutDialog(self.user, w, parent=self)
                if dlg.exec() == QDialog.DialogCode.Accepted:
                    self._load_data()
        finally:
            session.close()

    def _delete_workout(self, workout_id: int):
        reply = QMessageBox.question(
            self, "Delete Workout",
            "Are you sure you want to delete this workout?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            session = SessionLocal()
            try:
                w = session.query(WorkoutSession).get(workout_id)
                if w:
                    session.delete(w)
                    session.commit()
                    self._load_data()
            finally:
                session.close()
