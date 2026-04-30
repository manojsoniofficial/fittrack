@echo off
setlocal

set "ROOT_DIR=%~dp0.."
pushd "%ROOT_DIR%"

if not exist "coverage_reports" mkdir "coverage_reports"
if not exist "coverage_reports\html" mkdir "coverage_reports\html"

echo Running combined test coverage...
python -m pytest tests\test_suite.py tests\test_api.py -v --tb=short ^
  --cov=api --cov=models ^
  --cov-report=term-missing ^
  --cov-report=xml:coverage_reports\coverage.xml ^
  --cov-report=html:coverage_reports\html ^
  --cov-fail-under=80
if errorlevel 1 goto :error

echo Generating coverage badge SVG...
python coverage_reports\generate_coverage_badge.py coverage_reports\coverage.xml coverage_reports\coverage-badge.svg
if errorlevel 1 goto :error

echo Coverage batch completed successfully.
popd
exit /b 0

:error
echo Coverage batch failed.
popd
exit /b 1
