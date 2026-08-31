# RecoverIQ — Troubleshooting Guide

## 1. Common Issues & Solutions

### A. Dashboard Shows ₹0.00 / Empty Data
- **Cause**: Database has not been seeded yet.
- **Solution**:
  ```bash
  cd backend
  python scripts/seed_demo_data.py --reset
  ```

### B. UI Elements Look Unstyled or Raw HTML
- **Cause**: Tailwind CSS compilation error or outdated syntax in `globals.css`.
- **Solution**: Ensure `frontend/src/app/globals.css` begins with `@import "tailwindcss";` and restart Next.js dev server:
  ```bash
  cd frontend
  npm run dev
  ```

### C. Port 8000 or 3000 Already in Use
- **Cause**: Existing process running on target port.
- **Solution**:
  ```powershell
  # Windows PowerShell
  Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess | Stop-Process
  Get-Process -Id (Get-NetTCPConnection -LocalPort 3000).OwningProcess | Stop-Process
  ```

### D. Alembic Migration Fails with "No script_location key found"
- **Cause**: Alembic was invoked without specifying the absolute path to `backend/alembic.ini`.
- **Solution**: Run migrations from the `backend/` directory or ensure `alembic.ini` path is provided to `Config()`.
