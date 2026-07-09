@echo off
echo ===================================================
echo   Pushing InterviewIQ to GitHub
echo ===================================================
echo.

echo [1/4] Initializing Git repository...
git init
git branch -M main

echo [2/4] Configuring remote origin to:
echo https://github.com/Pranavkas/InterviewIQ-An-AI-Powered-Candidate-Screening-System.git
git remote remove origin >nul 2>&1
git remote add origin https://github.com/Pranavkas/InterviewIQ-An-AI-Powered-Candidate-Screening-System.git

echo [3/4] Staging and committing files...
git add .
git commit -m "Configure Docker multi-stage builds, Nginx reverse proxy, and GitHub Actions workflows"

echo [4/4] Pushing to GitHub main branch...
git push -u origin main

echo.
echo ===================================================
echo   Done! Check the Actions tab on GitHub.
echo ===================================================
pause
