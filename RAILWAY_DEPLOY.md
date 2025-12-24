# Railway Deployment Guide

## Cấu hình hiện tại

Railway sẽ tự động:
1. **Build frontend**: Chạy `build.sh` để build React app → `frontend/dist/`
2. **Install backend dependencies**: `pip install -r backend/requirements.txt`
3. **Start backend**: `cd backend && python -m app.main`
4. **Serve frontend**: FastAPI sẽ serve static files từ `frontend/dist/`

## Các bước deploy

### 1. Trên Railway Dashboard

1. Vào project của bạn trên Railway
2. Settings → Build & Deploy
3. Đảm bảo:
   - **Build Command**: `bash build.sh && pip install -r backend/requirements.txt`
   - **Start Command**: `cd backend && python -m app.main`

### 2. Environment Variables

Thêm vào Railway Environment Variables:
```
BINANCE_API_KEY=your_key
BINANCE_API_SECRET=your_secret
BINANCE_ENABLE_TESTNET=false
DEBUG=false
LOG_LEVEL=INFO
PORT=8000
```

### 3. Buildpacks

Railway sẽ tự detect:
- **Node.js** (từ `frontend/package.json`) → Build frontend
- **Python** (từ `runtime.txt` hoặc `requirements.txt`) → Install backend deps

## Cấu trúc sau khi build

```
frontend/dist/          # Built React app (static files)
backend/                # Python backend
  app/
    main.py            # FastAPI app (serves API + static files)
```

## API Endpoints

- **API**: `https://your-app.railway.app/api/*`
- **Frontend**: `https://your-app.railway.app/` (served by FastAPI)

## Troubleshooting

### Frontend không build
- Kiểm tra `frontend/package.json` có đúng không
- Xem build logs trên Railway

### Backend không start
- Kiểm tra `backend/requirements.txt`
- Xem logs: Railway → Deployments → View Logs

### Static files không load
- Kiểm tra `frontend/dist/` có được tạo không
- Kiểm tra path trong `backend/app/main.py`

## Alternative: Deploy riêng Frontend + Backend

Nếu muốn deploy riêng:

### Service 1: Backend
- Root: `backend/`
- Start: `python -m app.main`
- Port: 8000

### Service 2: Frontend (Static)
- Root: `frontend/`
- Build: `npm run build`
- Serve: Static files từ `dist/`
- Hoặc dùng Vercel/Netlify cho frontend

## Notes

- Railway sẽ tự detect Node.js và Python
- Build script (`build.sh`) chạy trước khi start
- Frontend được serve như static files từ FastAPI
- CORS đã được cấu hình cho production
