"""
FitTrack Pro - Application Stylesheet
Modern dark theme with accent colors
"""

MAIN_STYLESHEET = """
/* ── Global ── */
QWidget {
    background-color: #0f1117;
    color: #e2e8f0;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}

QLabel {
    background-color: transparent;
}

QMainWindow {
    background-color: #0f1117;
}

/* ── Sidebar ── */
#sidebar {
    background-color: #0a0d14;
    border-right: 1px solid #1e2235;
    min-width: 240px;
    max-width: 240px;
}

#sidebarLogo {
    font-size: 20px;
    font-weight: bold;
    color: #818cf8;
    padding: 20px 16px 6px 20px;
}

#sidebarSubtitle {
    font-size: 10px;
    color: #3d4a63;
    padding: 0 16px 16px 20px;
    letter-spacing: 0.5px;
}

#navButton {
    background: transparent;
    color: #64748b;
    border: none;
    border-left: 3px solid transparent;
    text-align: left;
    padding: 11px 16px 11px 17px;
    font-size: 13px;
    font-weight: 500;
    border-radius: 0;
}

#navButton:hover {
    background-color: #131824;
    color: #c7d2fe;
    border-left: 3px solid #4f46e5;
}

#navButton[active="true"] {
    background-color: #1a1f33;
    color: #818cf8;
    border-left: 3px solid #6366f1;
    font-weight: 600;
}

#userInfoWidget {
    background-color: #0a0d14;
    border-top: 1px solid #1e2235;
    padding: 8px 0;
}

#userNameLabel {
    font-weight: 700;
    color: #e2e8f0;
    font-size: 13px;
}

#userRoleLabel {
    color: #3d4a63;
    font-size: 10px;
}

/* ── Main Content Area ── */
#contentArea {
    background-color: #0f1117;
}

#pageTitle {
    font-size: 22px;
    font-weight: 700;
    color: #f1f5f9;
    padding: 4px 0;
}

#pageSubtitle {
    font-size: 12px;
    color: #475569;
}

/* ── Cards ── */
#card {
    background-color: #141828;
    border: 1px solid #1e2540;
    border-radius: 14px;
    padding: 18px;
}

#card:hover {
    border: 1px solid #312e81;
}

#cardTitle {
    font-size: 11px;
    color: #475569;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1.2px;
}

#cardValue {
    font-size: 30px;
    font-weight: 800;
    color: #f1f5f9;
}

#cardSubValue {
    font-size: 11px;
    color: #475569;
}

/* ── Buttons ── */
QPushButton {
    background-color: #4f46e5;
    color: #f8fafc;
    border: none;
    border-radius: 8px;
    padding: 8px 18px;
    font-size: 13px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #6366f1;
}

QPushButton:pressed {
    background-color: #3730a3;
}

QPushButton:disabled {
    background-color: #1e2235;
    color: #374151;
}

#dangerButton {
    background-color: #7f1d1d;
    color: #fca5a5;
    border: 1px solid #991b1b;
}
#dangerButton:hover {
    background-color: #991b1b;
    color: #fff;
}

#secondaryButton {
    background-color: #1e2235;
    color: #94a3b8;
    border: 1px solid #2d3748;
}
#secondaryButton:hover {
    background-color: #242840;
    color: #e2e8f0;
}

#successButton {
    background-color: #064e3b;
    color: #6ee7b7;
    border: 1px solid #065f46;
}
#successButton:hover {
    background-color: #065f46;
    color: #fff;
}

/* ── Table action buttons (smaller padding so text fits in narrow cells) ── */
#tableEditBtn {
    background-color: #1e2235;
    color: #94a3b8;
    border: 1px solid #2d3748;
    border-radius: 6px;
    padding: 3px 10px;
    font-size: 12px;
    font-weight: 600;
}
#tableEditBtn:hover {
    background-color: #242840;
    color: #e2e8f0;
}
#tableDeleteBtn {
    background-color: #7f1d1d;
    color: #fca5a5;
    border: 1px solid #991b1b;
    border-radius: 6px;
    padding: 3px 10px;
    font-size: 12px;
    font-weight: 600;
}
#tableDeleteBtn:hover {
    background-color: #991b1b;
    color: #fff;
}

#tableActionCell {
    background-color: transparent;
    border: none;
}

/* ── Nav sidebar buttons override (no fill) ── */
#navButton:hover, #navButton[active="true"] {
    border-radius: 0;
}

/* ── Input Fields ── */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #141828;
    border: 1px solid #1e2540;
    border-radius: 8px;
    padding: 8px 12px;
    color: #e2e8f0;
    font-size: 13px;
    selection-background-color: #4f46e5;
}

QLineEdit:focus, QTextEdit:focus {
    border: 1px solid #6366f1;
    background-color: #171d30;
}

QLineEdit:hover {
    border: 1px solid #374151;
}

QComboBox {
    background-color: #141828;
    border: 1px solid #1e2540;
    border-radius: 8px;
    padding: 8px 12px;
    color: #e2e8f0;
    font-size: 13px;
    min-width: 120px;
}

QComboBox:focus {
    border: 1px solid #6366f1;
}

QComboBox:hover {
    border: 1px solid #374151;
}

QComboBox::drop-down {
    border: none;
    padding-right: 10px;
}

QComboBox QAbstractItemView {
    background-color: #141828;
    border: 1px solid #1e2540;
    color: #e2e8f0;
    selection-background-color: #4f46e5;
    outline: none;
}

QSpinBox, QDoubleSpinBox {
    background-color: #141828;
    border: 1px solid #1e2540;
    border-radius: 8px;
    padding: 8px 12px;
    color: #e2e8f0;
}

QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid #6366f1;
}

QDateEdit {
    background-color: #141828;
    border: 1px solid #1e2540;
    border-radius: 8px;
    padding: 8px 12px;
    color: #e2e8f0;
}

QDateEdit:focus {
    border: 1px solid #6366f1;
}

QDateEdit::drop-down {
    border: none;
}

/* ── Tables ── */
QTableWidget {
    background-color: #141828;
    border: 1px solid #1e2540;
    border-radius: 10px;
    gridline-color: #1e2235;
    color: #cbd5e1;
    alternate-background-color: #111526;
}

QTableWidget::item {
    padding: 10px 14px;
    border-bottom: 1px solid #1a1f35;
}

QTableWidget::item:selected {
    background-color: #312e81;
    color: #e0e7ff;
}

QHeaderView::section {
    background-color: #0d1020;
    color: #475569;
    padding: 10px 14px;
    border: none;
    border-bottom: 1px solid #1e2235;
    font-weight: 700;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.8px;
}

QHeaderView::section:hover {
    background-color: #141828;
    color: #94a3b8;
}

QHeaderView::section:pressed,
QHeaderView::section:checked {
    background-color: #1a1f35;
    color: #94a3b8;
}

/* ── Progress Bar ── */
QProgressBar {
    background-color: #1e2235;
    border: none;
    border-radius: 6px;
    height: 8px;
    text-align: center;
    color: transparent;
}

QProgressBar::chunk {
    background-color: #6366f1;
    border-radius: 6px;
}

/* ── Scroll Bar ── */
QScrollBar:vertical {
    background: #0a0d14;
    width: 6px;
    border-radius: 3px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: #1e2540;
    border-radius: 3px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background: #4f46e5;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background: #0a0d14;
    height: 6px;
    border-radius: 3px;
}

QScrollBar::handle:horizontal {
    background: #1e2540;
    border-radius: 3px;
}

QScrollBar::handle:horizontal:hover {
    background: #4f46e5;
}

/* ── Labels ── */
QLabel#sectionHeader {
    font-size: 15px;
    font-weight: 700;
    color: #e2e8f0;
}

QLabel#metricValue {
    font-size: 30px;
    font-weight: 800;
    color: #818cf8;
}

QLabel#greenMetric {
    color: #34d399;
    font-weight: 700;
}

QLabel#redMetric {
    color: #f87171;
    font-weight: 700;
}

/* ── Tab Widget ── */
QTabWidget::pane {
    background-color: #141828;
    border: 1px solid #1e2540;
    border-radius: 10px;
}

QTabBar::tab {
    background-color: transparent;
    color: #475569;
    padding: 10px 20px;
    border: none;
    border-bottom: 2px solid transparent;
    font-size: 13px;
    font-weight: 500;
}

QTabBar::tab:selected {
    color: #818cf8;
    border-bottom: 2px solid #6366f1;
    font-weight: 700;
}

QTabBar::tab:hover {
    color: #c7d2fe;
    border-bottom: 2px solid #312e81;
}

/* ── Group Box ── */
QGroupBox {
    border: 1px solid #1e2540;
    border-radius: 10px;
    margin-top: 14px;
    padding: 14px;
    font-size: 12px;
    color: #64748b;
    font-weight: 600;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 6px;
    color: #6366f1;
}

/* ── Check Box ── */
QCheckBox {
    color: #cbd5e1;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #1e2540;
    border-radius: 4px;
    background-color: #141828;
}

QCheckBox::indicator:checked {
    background-color: #6366f1;
    border-color: #6366f1;
}

/* ── Splitter ── */
QSplitter::handle {
    background-color: #1e2235;
    width: 1px;
}

/* ── Status Bar ── */
QStatusBar {
    background-color: #0a0d14;
    color: #3d4a63;
    border-top: 1px solid #1e2235;
    padding: 4px 16px;
    font-size: 12px;
}

/* ── Dialog ── */
QDialog {
    background-color: #0f1117;
}

/* ── MessageBox ── */
QMessageBox {
    background-color: #0f1117;
    color: #e2e8f0;
}

/* ── Separator ── */
QFrame[frameShape="4"], QFrame[frameShape="5"] {
    color: #1e2235;
    background-color: #1e2235;
}

/* ── Tooltip ── */
QToolTip {
    background-color: #141828;
    color: #c7d2fe;
    border: 1px solid #312e81;
    padding: 6px 10px;
    border-radius: 6px;
    font-size: 12px;
}
"""

LOGIN_STYLESHEET = """
/* ── Login root background ── */
QWidget {
    background-color: #0f1117;
    color: #e2e8f0;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}

/* ── Card ── */
#loginCard {
    background-color: #1a1d2e;
    border: 1px solid #3730a3;
    border-radius: 20px;
}

/* ── All plain labels inside card must be transparent ── */
QLabel {
    background-color: transparent;
    color: #e2e8f0;
}

/* ── Accent badge around emoji ── */
#iconBadge {
    background-color: #312e81;
    border-radius: 36px;
    min-width: 72px;
    max-width: 72px;
    min-height: 72px;
    max-height: 72px;
}

#appEmoji {
    font-size: 34px;
    background-color: transparent;
}

#appTitle {
    font-size: 28px;
    font-weight: bold;
    color: #818cf8;
    letter-spacing: 1px;
    background-color: transparent;
}

#appTagline {
    font-size: 12px;
    color: #64748b;
    background-color: transparent;
}

/* ── Divider ── */
#divider {
    background-color: #2d3748;
    max-height: 1px;
    min-height: 1px;
}

/* ── Field labels ── */
QLabel#fieldLabel {
    color: #94a3b8;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.8px;
    background-color: transparent;
}

/* ── Inputs ── */
QLineEdit {
    background-color: #242840;
    border: 1px solid #374151;
    border-radius: 10px;
    padding: 11px 14px;
    color: #f1f5f9;
    font-size: 14px;
    selection-background-color: #6366f1;
}

QLineEdit:focus {
    border: 1px solid #6366f1;
    background-color: #272b45;
}

QLineEdit:hover {
    border: 1px solid #4f46e5;
}

/* ── Sign In button ── */
QPushButton#loginBtn {
    background-color: #6366f1;
    color: white;
    border: none;
    border-radius: 10px;
    padding: 13px;
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 0.5px;
}

QPushButton#loginBtn:hover {
    background-color: #818cf8;
}

QPushButton#loginBtn:pressed {
    background-color: #4f46e5;
}

/* ── Error / hint ── */
QLabel#errorLabel {
    color: #f87171;
    font-size: 12px;
    font-weight: 600;
    background-color: transparent;
}

QLabel#hintLabel {
    color: #475569;
    font-size: 11px;
    background-color: transparent;
}
"""
