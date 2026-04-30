"""
FitTrack Pro - API Routes Package

All blueprints are registered in api/__init__.py create_app().

Endpoints:
  /api/auth/*          Authentication (register, login, refresh, me)
  /api/workouts/*      Workout CRUD + offline sync
  /api/nutrition/*     Meal CRUD + nutrition search + offline sync
  /api/goals/*         Fitness goal CRUD
  /api/measurements/*  Body measurement CRUD + auto-goal update
  /api/progress/*      Progress summaries and report generation
  /api/coach/*         Coach-only: client list, summaries, reports
  /api/notifications/* Notification CRUD + mark-read
  /api/health          Health check
"""
