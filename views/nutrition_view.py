"""
FitTrack Pro - Nutrition / Meal Tracking View
"""

from datetime import date
from PyQt6.QtWidgets import (
    QWidget, QScrollArea, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QDialog, QFormLayout,
    QLineEdit, QDoubleSpinBox, QComboBox, QDateEdit, QFrame,
    QHeaderView, QMessageBox, QProgressBar, QSizePolicy
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QPainter, QColor, QBrush
from PyQt6.QtCharts import QChart, QChartView, QPieSeries, QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis

from models.database import SessionLocal, User, MealEntry
from models.services import CalorieCalculator, ProgressAnalyser

MEAL_TYPES = ["Breakfast", "Lunch", "Dinner", "Snack"]

FOOD_PRESETS = {
    "Oatmeal with Berries": (350, 12, 58, 7),
    "Grilled Chicken Breast": (165, 31, 0, 3.6),
    "Grilled Chicken Salad": (480, 42, 22, 18),
    "Salmon with Vegetables": (520, 38, 30, 22),
    "Greek Yogurt": (130, 17, 9, 0.7),
    "Protein Bar": (220, 20, 25, 6),
    "Brown Rice (1 cup)": (215, 5, 45, 2),
    "Eggs (2 large)": (156, 12, 1, 11),
    "Banana": (105, 1, 27, 0),
    "Almonds (30g)": (174, 6, 6, 15),
    "Whole Wheat Bread (2 slices)": (160, 8, 30, 2),
    "Milk (250ml)": (149, 8, 12, 8),
    "Apple": (80, 0.4, 21, 0.3),
    "Lentil Soup": (310, 18, 48, 5),
    "Custom": (0, 0, 0, 0),
}


class MealDialog(QDialog):
    def __init__(self, user: User, meal: MealEntry = None, parent=None):
        super().__init__(parent)
        self.user = user
        self.meal = meal
        self.setWindowTitle("Edit Meal" if meal else "Log Meal")
        self.setMinimumWidth(440)
        self.setModal(True)
        self._build_ui()
        if meal:
            self._populate()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("Edit Meal" if self.meal else "Log Meal Entry")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)

        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        form.addRow("Date *", self.date_edit)

        self.type_combo = QComboBox()
        self.type_combo.addItems(MEAL_TYPES)
        form.addRow("Meal Type *", self.type_combo)

        # Food name with quick-fill presets
        food_row = QHBoxLayout()
        self.food_edit = QLineEdit()
        self.food_edit.setPlaceholderText("Food name...")
        food_row.addWidget(self.food_edit)

        self.preset_combo = QComboBox()
        self.preset_combo.addItem("Quick fill...")
        self.preset_combo.addItems(FOOD_PRESETS.keys())
        self.preset_combo.currentTextChanged.connect(self._apply_preset)
        food_row.addWidget(self.preset_combo)
        form.addRow("Food *", food_row)

        self.quantity_spin = QDoubleSpinBox()
        self.quantity_spin.setRange(0.1, 100)
        self.quantity_spin.setValue(1.0)
        self.quantity_spin.setSingleStep(0.5)
        form.addRow("Quantity", self.quantity_spin)

        self.unit_edit = QLineEdit()
        self.unit_edit.setText("serving")
        self.unit_edit.setPlaceholderText("e.g., g, ml, cup, serving")
        form.addRow("Unit", self.unit_edit)

        # Macros
        self.calories_spin = QDoubleSpinBox()
        self.calories_spin.setRange(0, 5000)
        self.calories_spin.setDecimals(0)
        self.calories_spin.setSuffix(" kcal")
        form.addRow("Calories *", self.calories_spin)

        self.protein_spin = QDoubleSpinBox()
        self.protein_spin.setRange(0, 500)
        self.protein_spin.setSuffix(" g")
        form.addRow("Protein", self.protein_spin)

        self.carbs_spin = QDoubleSpinBox()
        self.carbs_spin.setRange(0, 500)
        self.carbs_spin.setSuffix(" g")
        form.addRow("Carbs", self.carbs_spin)

        self.fat_spin = QDoubleSpinBox()
        self.fat_spin.setRange(0, 500)
        self.fat_spin.setSuffix(" g")
        form.addRow("Fat", self.fat_spin)

        layout.addLayout(form)

        btn_row = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("secondaryButton")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()

        save_btn = QPushButton("Save Meal")
        save_btn.setObjectName("successButton")
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def _apply_preset(self, name: str):
        if name == "Quick fill..." or name not in FOOD_PRESETS:
            return
        cals, prot, carbs, fat = FOOD_PRESETS[name]
        if name != "Custom":
            self.food_edit.setText(name)
            self.calories_spin.setValue(cals)
            self.protein_spin.setValue(prot)
            self.carbs_spin.setValue(carbs)
            self.fat_spin.setValue(fat)

    def _populate(self):
        m = self.meal
        self.date_edit.setDate(QDate(m.date.year, m.date.month, m.date.day))
        idx = MEAL_TYPES.index(m.meal_type) if m.meal_type in MEAL_TYPES else 0
        self.type_combo.setCurrentIndex(idx)
        self.food_edit.setText(m.food_name)
        self.quantity_spin.setValue(m.quantity)
        self.unit_edit.setText(m.unit or "serving")
        self.calories_spin.setValue(m.calories)
        self.protein_spin.setValue(m.protein_g or 0)
        self.carbs_spin.setValue(m.carbs_g or 0)
        self.fat_spin.setValue(m.fat_g or 0)

    def _save(self):
        food = self.food_edit.text().strip()
        if not food:
            QMessageBox.warning(self, "Validation", "Food name is required.")
            return

        qdate = self.date_edit.date()
        meal_date = date(qdate.year(), qdate.month(), qdate.day())

        session = SessionLocal()
        try:
            if self.meal:
                m = session.merge(self.meal)
            else:
                m = MealEntry(user_id=self.user.id)
                session.add(m)

            m.date = meal_date
            m.meal_type = self.type_combo.currentText()
            m.food_name = food
            m.quantity = self.quantity_spin.value()
            m.unit = self.unit_edit.text().strip() or "serving"
            m.calories = self.calories_spin.value()
            m.protein_g = self.protein_spin.value()
            m.carbs_g = self.carbs_spin.value()
            m.fat_g = self.fat_spin.value()

            session.commit()
            self.accept()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", str(e))
        finally:
            session.close()


class NutritionView(QWidget):
    def __init__(self, user: User):
        super().__init__()
        self.user = user
        self._selected_date = date.today()
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        header = QHBoxLayout()
        title = QLabel("Nutrition Tracker")
        title.setObjectName("pageTitle")
        header.addWidget(title)
        header.addStretch()

        add_btn = QPushButton("+ Log Meal")
        add_btn.setObjectName("successButton")
        add_btn.clicked.connect(self._add_meal)
        header.addWidget(add_btn)
        layout.addLayout(header)

        # Date selector
        date_row = QHBoxLayout()
        date_row.setSpacing(8)
        date_row.addWidget(QLabel("Date:"))
        self.date_selector = QDateEdit()
        self.date_selector.setDate(QDate.currentDate())
        self.date_selector.setCalendarPopup(True)
        self.date_selector.dateChanged.connect(self._on_date_changed)
        date_row.addWidget(self.date_selector)
        date_row.addStretch()
        layout.addLayout(date_row)

        # Top summary row
        summary_row = QHBoxLayout()
        summary_row.setSpacing(12)
        summary_row.setContentsMargins(0, 4, 0, 4)

        self.calorie_frame = QFrame()
        self.calorie_frame.setObjectName("card")
        self.calorie_frame.setMinimumHeight(164)
        self.calorie_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        cf = QVBoxLayout(self.calorie_frame)
        cf.setContentsMargins(18, 16, 18, 14)
        cf.setSpacing(6)
        self.calorie_lbl = QLabel("0")
        self.calorie_lbl.setStyleSheet("font-size: 28px; font-weight: 800; color: #6366f1;")
        self.calorie_lbl.setFixedHeight(46)
        self.calorie_lbl.setWordWrap(False)
        self.calorie_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        cf.addWidget(self.calorie_lbl)
        cal_sub = QLabel("Total Calories")
        cal_sub.setStyleSheet("color: #64748b;")
        cal_sub.setFixedHeight(16)
        cf.addWidget(cal_sub)

        # Progress bar for target
        self.cal_progress = QProgressBar()
        self.cal_progress.setMaximum(2000)
        self.cal_progress.setTextVisible(False)
        self.cal_progress.setFixedHeight(10)
        cf.addWidget(self.cal_progress)
        self.cal_goal_lbl = QLabel("Goal: 2000 kcal")
        self.cal_goal_lbl.setStyleSheet("color: #64748b; font-size: 11px;")
        self.cal_goal_lbl.setFixedHeight(16)
        cf.addWidget(self.cal_goal_lbl)
        summary_row.addWidget(self.calorie_frame, 1)

        for label, attr, color in [
            ("Protein", "protein_lbl", "#6366f1"),
            ("Carbs", "carbs_lbl", "#10b981"),
            ("Fat", "fat_lbl", "#f59e0b"),
        ]:
            frame = QFrame()
            frame.setObjectName("card")
            frame.setMinimumHeight(142)
            frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            fl = QVBoxLayout(frame)
            fl.setContentsMargins(18, 16, 18, 14)
            fl.setSpacing(8)
            lbl = QLabel("0g")
            lbl.setStyleSheet(f"font-size: 30px; font-weight: 800; color: {color};")
            lbl.setFixedHeight(48)
            lbl.setWordWrap(False)
            lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            fl.addWidget(lbl)
            macro_label = QLabel(label)
            macro_label.setFixedHeight(18)
            fl.addWidget(macro_label)
            setattr(self, attr, lbl)
            summary_row.addWidget(frame, 1)

        layout.addLayout(summary_row)

        # Meals by type
        for meal_type in MEAL_TYPES:
            section = QLabel(meal_type)
            section.setObjectName("sectionHeader")
            layout.addWidget(section)

            table = QTableWidget(0, 5)
            table.setHorizontalHeaderLabels(["Food", "Qty", "Calories", "Protein", "Actions"])
            th = table.horizontalHeader()
            th.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            th.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
            th.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
            th.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
            th.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
            table.setColumnWidth(1, 90)
            table.setColumnWidth(2, 100)
            table.setColumnWidth(3, 90)
            table.setColumnWidth(4, 172)
            table.setMinimumHeight(100)
            table.setMaximumHeight(240)
            table.verticalHeader().setDefaultSectionSize(46)
            table.verticalHeader().setVisible(False)
            table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            setattr(self, f"table_{meal_type.lower()}", table)
            layout.addWidget(table)

    def _on_date_changed(self, qdate):
        self._selected_date = date(qdate.year(), qdate.month(), qdate.day())
        self._load_data()

    def _load_data(self):
        session = SessionLocal()
        try:
            meals = session.query(MealEntry).filter(
                MealEntry.user_id == self.user.id,
                MealEntry.date == self._selected_date
            ).order_by(MealEntry.meal_type).all()

            total_cal = sum(m.calories for m in meals)
            total_prot = sum(m.protein_g or 0 for m in meals)
            total_carbs = sum(m.carbs_g or 0 for m in meals)
            total_fat = sum(m.fat_g or 0 for m in meals)

            self.calorie_lbl.setText(f"{total_cal:.0f}")
            self.protein_lbl.setText(f"{total_prot:.0f}g")
            self.carbs_lbl.setText(f"{total_carbs:.0f}g")
            self.fat_lbl.setText(f"{total_fat:.0f}g")
            self.cal_progress.setValue(min(int(total_cal), 2000))

            # Populate each meal type table
            for meal_type in MEAL_TYPES:
                table = getattr(self, f"table_{meal_type.lower()}", None)
                if table is None:
                    continue
                table.setRowCount(0)
                type_meals = [m for m in meals if m.meal_type == meal_type]
                for m in type_meals:
                    row = table.rowCount()
                    table.insertRow(row)
                    table.setItem(row, 0, QTableWidgetItem(m.food_name))
                    table.setItem(row, 1, QTableWidgetItem(f"{m.quantity} {m.unit}"))
                    table.setItem(row, 2, QTableWidgetItem(f"{m.calories:.0f} kcal"))
                    table.setItem(row, 3, QTableWidgetItem(f"{m.protein_g:.0f}g"))

                    action_widget = QWidget()
                    action_widget.setObjectName("tableActionCell")
                    action_widget.setMinimumHeight(34)
                    al = QHBoxLayout(action_widget)
                    al.setContentsMargins(6, 4, 6, 4)
                    al.setSpacing(8)
                    al.setAlignment(Qt.AlignmentFlag.AlignCenter)

                    edit_btn = QPushButton("Edit")
                    edit_btn.setObjectName("tableEditBtn")
                    edit_btn.setFixedSize(62, 30)
                    edit_btn.clicked.connect(lambda checked, mid=m.id: self._edit_meal(mid))
                    al.addWidget(edit_btn)

                    del_btn = QPushButton("Delete")
                    del_btn.setObjectName("tableDeleteBtn")
                    del_btn.setFixedSize(76, 30)
                    del_btn.clicked.connect(lambda checked, mid=m.id: self._delete_meal(mid))
                    al.addWidget(del_btn)

                    table.setCellWidget(row, 4, action_widget)
                    table.setRowHeight(row, 46)

                self._fit_meal_table_height(table)

        finally:
            session.close()

    def _fit_meal_table_height(self, table: QTableWidget):
        # Keep enough room for header + at least one full data row + borders.
        header_h = max(36, table.horizontalHeader().height())
        visible_rows = max(1, table.rowCount())
        target = header_h + (visible_rows * 46) + 10
        table.setMinimumHeight(min(target, 240))

    def _add_meal(self):
        dlg = MealDialog(self.user, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._load_data()

    def _edit_meal(self, meal_id: int):
        session = SessionLocal()
        try:
            m = session.query(MealEntry).get(meal_id)
            if m:
                dlg = MealDialog(self.user, m, parent=self)
                if dlg.exec() == QDialog.DialogCode.Accepted:
                    self._load_data()
        finally:
            session.close()

    def _delete_meal(self, meal_id: int):
        reply = QMessageBox.question(self, "Delete", "Delete this meal entry?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            session = SessionLocal()
            try:
                m = session.query(MealEntry).get(meal_id)
                if m:
                    session.delete(m)
                    session.commit()
                    self._load_data()
            finally:
                session.close()
