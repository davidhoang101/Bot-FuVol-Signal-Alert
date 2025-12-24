# 🚀 Hướng dẫn chạy Bot trên Localhost

## Cách 1: Sử dụng script tự động (Khuyến nghị)

```bash
./run_local.sh
```

Script này sẽ:
- ✅ Tự động kiểm tra và tạo virtual environment nếu chưa có
- ✅ Tự động tạo file `.env` nếu chưa có
- ✅ Kích hoạt virtual environment
- ✅ Dừng bot cũ nếu đang chạy
- ✅ Khởi động bot mới

## Cách 2: Chạy thủ công

### Bước 1: Setup môi trường (chỉ cần làm 1 lần)

```bash
# Tạo virtual environment
python3 -m venv venv

# Kích hoạt virtual environment
source venv/bin/activate  # macOS/Linux
# hoặc
venv\Scripts\activate     # Windows

# Cài đặt dependencies
pip install -r requirements.txt
```

### Bước 2: Cấu hình

Tạo file `.env` trong thư mục gốc:

```env
# Binance API (optional - chỉ cần cho private data)
BINANCE_API_KEY=
BINANCE_API_SECRET=
BINANCE_TESTNET=false

# Detection Parameters
MIN_VOLUME_THRESHOLD=1000000
SPIKE_RATIO_THRESHOLD=2.0
BASELINE_WINDOW_MINUTES=60
COOLDOWN_PERIOD_MINUTES=15
UPDATE_INTERVAL_SECONDS=5

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/volume_alert.log

# Telegram Bot (optional - để nhận alerts qua Telegram)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id
TELEGRAM_AUTO_TOP10_INTERVAL_MINUTES=0

# Funding Scanner
ENABLE_FUNDING_SCANNER=true
FUNDING_SCAN_INTERVAL_SECONDS=300
HIGH_FUNDING_RATE_THRESHOLD=0.001
LOW_FUNDING_RATE_THRESHOLD=-0.001
FUNDING_RATE_CHANGE_THRESHOLD=0.0005
FUNDING_ALERT_COOLDOWN_MINUTES=60
```

**Lưu ý:**
- Binance API keys là **optional** - không cần thiết cho public data (volume, funding rates)
- Telegram Bot Token là **optional** - nếu không có, bot sẽ chỉ in alerts ra console
- Nếu không có `TELEGRAM_CHAT_ID`, bot sẽ tự động lấy từ tin nhắn gần nhất

### Bước 3: Chạy bot

```bash
# Đảm bảo đã kích hoạt virtual environment
source venv/bin/activate

# Chạy bot
python main.py
```

## Cách 3: Sử dụng script restart (nếu bot đã được setup)

```bash
./restart_local_bot.sh
```

## 📋 Kiểm tra Bot đang chạy

### Xem process đang chạy:
```bash
ps aux | grep "python.*main.py" | grep -v grep
```

### Xem logs:
```bash
tail -f logs/volume_alert.log
```

### Dừng bot:
```bash
# Tìm PID
ps aux | grep "python.*main.py" | grep -v grep

# Dừng bot (thay PID bằng số thực tế)
kill <PID>
```

Hoặc nhấn `Ctrl+C` trong terminal đang chạy bot.

## 🔧 Troubleshooting

### Lỗi: "Module not found"
```bash
# Đảm bảo đã kích hoạt virtual environment
source venv/bin/activate

# Cài đặt lại dependencies
pip install -r requirements.txt
```

### Lỗi: "Telegram bot conflict"
- Đảm bảo không có bot instance khác đang chạy (trên Railway hoặc server khác)
- Xóa webhook nếu có: `python delete_webhook.py`

### Lỗi: "SSL verification failed"
- Đây là warning bình thường trong môi trường development
- Bot sẽ tự động sử dụng custom SSL context

### Bot không nhận được Telegram messages
1. Kiểm tra `TELEGRAM_BOT_TOKEN` trong `.env`
2. Gửi `/start` cho bot trên Telegram
3. Kiểm tra logs để xem chat ID được detect

## 📱 Telegram Bot Commands

Sau khi bot chạy, bạn có thể dùng các lệnh sau trên Telegram:

- `/start` - Khởi động bot và hiển thị menu
- `/top10` - Top 10 pairs với volume spike cao nhất
- `/topgainers` - Top 15 tokens tăng giá 24h
- `/funding` - Scan funding rates (top positive & negative)
- `/topfunding` - Top 10 highest và lowest funding rates

## 🎯 Tính năng

Bot sẽ tự động:
- ✅ Monitor real-time volume từ Binance Futures
- ✅ Phát hiện volume spikes và gửi alerts
- ✅ Scan funding rates mỗi 5 phút (nếu enabled)
- ✅ Gửi alerts qua Telegram (nếu configured)
- ✅ In alerts ra console

## 📊 Logs

Logs được lưu tại: `logs/volume_alert.log`

Xem logs real-time:
```bash
tail -f logs/volume_alert.log
```
