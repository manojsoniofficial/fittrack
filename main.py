"""
FitTrack Pro - Application Entry Point
HealthHub Smart Workout, Nutrition & Progress Manager

Usage:
    python main.py

Requirements:
    pip install PyQt6 sqlalchemy bcrypt pytest pytest-cov

Architecture: Layered + Ports-and-Adapters (Hexagonal)
    - Domain Layer:  models/database.py  (entities)
    - Services:      models/services.py  (CalorieCalculator, ProgressAnalyser, BadgeService)
    - UI Layer:      views/              (PyQt6 desktop client)
    - Tests:         tests/test_suite.py (pytest)

Sprint Plan:
    Sprint 1 (Week 1-2): Core models, auth, workout logging, nutrition tracking
    Sprint 2 (Week 3-4): Goals, measurements, coach dashboard, reporting, badges
"""

import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(__file__))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from models.database import init_db
from views.login_view import LoginWindow
from views.main_window import MainWindow
from assets.styles import MAIN_STYLESHEET


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("FitTrack Pro")
    app.setOrganizationName("HealthHub")
    app.setApplicationVersion("1.0.0")

    # Set application-wide font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # Initialize database & seed demo data
    print("Initializing FitTrack Pro database...")
    init_db()
    print("Database ready.")

    # Show login window
    login_window = LoginWindow()

    def on_login(user):
        login_window.hide()
        main_window = MainWindow(user)
        main_window.showMaximized()
        # Keep reference to avoid garbage collection
        app._main_window = main_window
        login_window.close()

    login_window.login_successful.connect(on_login)
    login_window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
