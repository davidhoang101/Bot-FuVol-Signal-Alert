# 📊 Binance Futures Volume Alert Bot

Telegram bot để cảnh báo khi volume của token trên Binance Futures tăng đột biến trong 5 phút.

## 🎯 Tính năng

- ✅ Monitor real-time volume từ Binance Futures qua WebSocket
- ✅ Phát hiện volume spike (tăng đột biến) so với baseline
- ✅ Loại bỏ outliers để tính baseline chính xác
- ✅ Cooldown period để tránh spam alerts
- ✅ Rate limiting để tránh API limits
- ✅ Console logging với màu sắc
- 🔜 Telegram bot integration (sẽ thêm sau)

## 🏗️ Kiến trúc

Xem file `ARCHITECTURE.md` để biết chi tiết về kiến trúc hệ thống.

## 📋 Yêu cầu

- Python 3.11+
- Binance API key (optional - chỉ cần cho private data, public data không cần)

## 🚀 Cài đặt

1. **Clone repository và vào thư mục:**
```bash
cd futu_vol_alert
```

2. **Tạo virtual environment:**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Cài đặt dependencies:**
```bash
pip install -r requirements.txt
```

4. **Cấu hình environment variables:**
```bash
cp .env.example .env
# Chỉnh sửa .env nếu cần (API keys optional cho public data)
```

## ⚙️ Cấu hình

Chỉnh sửa file `.env` hoặc environment variables:

```env
# Detection Parameters
MIN_VOLUME_THRESHOLD=1000000      # Minimum volume để trigger alert (USDT)
SPIKE_RATIO_THRESHOLD=3.0         # Tỷ lệ tăng để coi là spike (3x = 300%)
BASELINE_WINDOW_MINUTES=60        # Thời gian tính baseline (phút)
COOLDOWN_PERIOD_MINUTES=15        # Thời gian chờ giữa các alerts cho cùng 1 symbol
UPDATE_INTERVAL_SECONDS=5         # Tần suất check spikes (giây)

# Logging
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR
LOG_FILE=logs/volume_alert.log
```

## 🏃 Chạy ứng dụng

```bash
python main.py
```

Hệ thống sẽ:
1. Kết nối với Binance Futures WebSocket
2. Load danh sách symbols (top 200 với volume cao nhất)
3. Monitor real-time trades
4. Tính toán volume mỗi 5 phút
5. So sánh với baseline và phát hiện spikes
6. In alerts ra console

## 🚂 Deploy lên Railway

### Cách 1: Deploy qua Railway CLI

1. **Cài đặt Railway CLI:**
```bash
npm i -g @railway/cli
railway login
```

2. **Khởi tạo project trên Railway:**
```bash
railway init
```

3. **Thiết lập environment variables:**
```bash
# Thiết lập các biến môi trường cần thiết
railway variables set MIN_VOLUME_THRESHOLD=1000000
railway variables set SPIKE_RATIO_THRESHOLD=3.0
railway variables set BASELINE_WINDOW_MINUTES=60
railway variables set COOLDOWN_PERIOD_MINUTES=15
railway variables set UPDATE_INTERVAL_SECONDS=5
railway variables set LOG_LEVEL=INFO

# Optional: Telegram Bot (nếu có)
railway variables set TELEGRAM_BOT_TOKEN=your_token_here
railway variables set TELEGRAM_CHAT_ID=your_chat_id_here

# Optional: Binance API (nếu cần)
railway variables set BINANCE_API_KEY=your_api_key
railway variables set BINANCE_API_SECRET=your_api_secret
```

4. **Deploy code:**
```bash
railway up
```

### Cách 2: Deploy qua GitHub Integration

1. **Push code lên GitHub:**
```bash
git add .
git commit -m "Prepare for Railway deployment"
git push origin main
```

2. **Tạo project trên Railway:**
   - Vào [railway.app](https://railway.app)
   - Click "New Project"
   - Chọn "Deploy from GitHub repo"
   - Chọn repository của bạn

3. **Thiết lập environment variables:**
   - Vào tab "Variables" trong Railway dashboard
   - Thêm các biến môi trường như ở trên

4. **Railway sẽ tự động deploy:**
   - Railway sẽ tự động detect Python project
   - Sử dụng `Procfile` hoặc `railway.json` để chạy app
   - App sẽ chạy và monitor volume spikes

### Lưu ý khi deploy lên Railway:

- ✅ Railway tự động detect Python và cài đặt dependencies từ `requirements.txt`
- ✅ Sử dụng `Procfile` hoặc `railway.json` để chạy app
- ✅ Logs sẽ hiển thị trong Railway dashboard
- ✅ App sẽ tự động restart nếu crash (theo cấu hình trong `railway.json`)
- ⚠️ Đảm bảo đã set đầy đủ environment variables trong Railway dashboard
- ⚠️ Railway có thể sleep nếu không có traffic, nhưng app này là long-running process nên sẽ luôn chạy

## 📊 Output mẫu

```
🚨 VOLUME SPIKE ALERT 🚨

Symbol: BTCUSDT
Current 5min Volume: 1.25B USDT
Baseline Volume: 250.00M USDT
Spike Ratio: 5.00x

Time: 2024-12-10 12:15:00 UTC
```

## 🔧 Best Practices đã áp dụng

1. **Rate Limiting**: Tự động giới hạn số requests để tránh Binance API limits
2. **Error Handling**: Comprehensive error handling với retry logic
3. **Async/Await**: Sử dụng async để xử lý concurrent
4. **Outlier Removal**: Loại bỏ outliers khi tính baseline (IQR method)
5. **Spike Confirmation**: Cần 2 intervals liên tiếp để confirm spike (tránh false positives)
6. **Cooldown Period**: Tránh spam alerts cho cùng 1 symbol
7. **Graceful Shutdown**: Xử lý signals để shutdown cleanly
8. **Structured Logging**: Logging với levels và file rotation
9. **Configuration Management**: Tất cả config qua environment variables
10. **Memory Management**: Cleanup old data để tránh memory leak

## 📁 Cấu trúc project

```
futu_vol_alert/
├── src/
│   ├── bot/           # Telegram bot (sẽ thêm sau)
│   ├── data/          # Binance client & volume calculator
│   ├── detector/      # Spike detection logic
│   ├── alert/         # Alert formatting
│   └── utils/         # Config, logger
├── tests/             # Unit tests
├── logs/              # Log files
├── main.py            # Entry point
├── requirements.txt
└── README.md
```

## 🧪 Testing

```bash
# Chạy tests (sẽ thêm sau)
pytest tests/
```

## 📝 TODO

- [ ] Thêm Telegram bot integration
- [ ] Thêm unit tests
- [ ] Thêm Redis caching (optional)
- [ ] Thêm Docker containerization
- [ ] Thêm monitoring dashboard

## ⚠️ Lưu ý

- Hệ thống chỉ monitor top 200 symbols với volume cao nhất để tránh quá tải
- WebSocket có thể disconnect, hệ thống sẽ tự động reconnect
- Cần đợi ít nhất 5-10 phút để có đủ data cho baseline calculation

## 📄 License

MIT
