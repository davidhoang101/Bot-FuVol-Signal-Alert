# 🏗️ Volume Alert Bot - System Architecture

## System Flow Diagram

```mermaid
graph TB
    subgraph "Data Collection Layer"
        A[Binance Futures<br/>WebSocket Stream] --> B[Volume Collector]
        B --> C[5-Minute Aggregator]
        C --> D[Redis Cache<br/>Volume History]
    end
    
    subgraph "Detection Engine"
        D --> E[Baseline Calculator<br/>30-60min rolling window]
        C --> F[Current Volume<br/>Last 5 minutes]
        E --> G[Spike Detector]
        F --> G
        G --> H{Spike Ratio<br/>>= Threshold?}
    end
    
    subgraph "Alert Processing"
        H -->|Yes| I[Alert Filter<br/>Cooldown Check]
        I --> J[Rate Limiter]
        J --> K[Message Formatter]
    end
    
    subgraph "Telegram Layer"
        K --> L[Telegram Bot API]
        L --> M[Users/Channels]
        M --> N[Bot Commands<br/>/start, /status, /config]
    end
    
    style A fill:#f9f,stroke:#333,stroke-width:2px
    style G fill:#bbf,stroke:#333,stroke-width:2px
    style L fill:#9f9,stroke:#333,stroke-width:2px
    style M fill:#ff9,stroke:#333,stroke-width:2px
```

## Component Architecture

```mermaid
graph LR
    subgraph "Application Core"
        A[main.py<br/>Entry Point] --> B[Bot Manager]
        B --> C[Volume Monitor]
        B --> D[Alert Manager]
    end
    
    subgraph "Data Layer"
        C --> E[Binance Client<br/>WebSocket + REST]
        C --> F[Volume Calculator]
        F --> G[Redis Cache]
    end
    
    subgraph "Detection Layer"
        F --> H[Baseline Engine]
        H --> I[Spike Detector]
        I --> D
    end
    
    subgraph "Communication Layer"
        D --> J[Telegram Handler]
        J --> K[Message Queue]
        K --> L[Rate Limiter]
    end
    
    subgraph "Configuration"
        M[Config Manager<br/>.env files] --> B
        M --> E
        M --> J
    end
    
    style A fill:#f96,stroke:#333,stroke-width:3px
    style I fill:#6bf,stroke:#333,stroke-width:2px
    style J fill:#6f9,stroke:#333,stroke-width:2px
```

## Data Flow Sequence

```mermaid
sequenceDiagram
    participant B as Binance API
    participant VC as Volume Collector
    participant BC as Baseline Calculator
    participant SD as Spike Detector
    participant AM as Alert Manager
    participant TB as Telegram Bot
    
    loop Every 5 seconds
        B->>VC: Stream trade data
        VC->>VC: Aggregate 5-min volume
    end
    
    loop Every 5 minutes
        VC->>BC: Get current 5-min volume
        BC->>BC: Calculate baseline (30-60min)
        BC->>SD: Volume + Baseline
        SD->>SD: Calculate spike ratio
        
        alt Spike Ratio >= Threshold
            SD->>AM: Trigger alert
            AM->>AM: Check cooldown
            AM->>AM: Apply filters
            AM->>TB: Format message
            TB->>TB: Send to users
        end
    end
```

## Volume Detection Logic

```mermaid
flowchart TD
    Start[New 5-min Interval] --> GetCurrent[Get Current Volume]
    GetCurrent --> GetBaseline[Calculate Baseline<br/>Last 30-60 minutes]
    GetBaseline --> RemoveOutliers[Remove Outliers<br/>IQR Method]
    RemoveOutliers --> CalcMedian[Calculate Median Volume]
    CalcMedian --> CalcRatio[Spike Ratio =<br/>Current / Baseline]
    
    CalcRatio --> CheckThreshold{Spike Ratio<br/>>= 3.0?}
    CheckThreshold -->|No| End1[No Alert]
    CheckThreshold -->|Yes| CheckMinVol{Current Volume<br/>>= Min Threshold?}
    
    CheckMinVol -->|No| End1
    CheckMinVol -->|Yes| CheckCooldown{Cooldown<br/>Expired?}
    
    CheckCooldown -->|No| End1
    CheckCooldown -->|Yes| ConfirmSpike[Confirm Spike<br/>Check 2-3 intervals]
    
    ConfirmSpike --> IsConfirmed{Confirmed?}
    IsConfirmed -->|No| End1
    IsConfirmed -->|Yes| SendAlert[🚨 Send Alert]
    SendAlert --> UpdateCooldown[Update Cooldown Timer]
    UpdateCooldown --> End2[End]
    
    style SendAlert fill:#f66,stroke:#333,stroke-width:3px
    style CheckThreshold fill:#bbf,stroke:#333,stroke-width:2px
    style CheckMinVol fill:#bbf,stroke:#333,stroke-width:2px
```

## Technology Stack Visualization

```mermaid
graph TB
    subgraph "Runtime"
        A[Python 3.11+<br/>Async/Await]
    end
    
    subgraph "APIs & Libraries"
        B[python-telegram-bot<br/>v20+]
        C[ccxt / python-binance<br/>WebSocket]
        D[pandas<br/>Data Analysis]
        E[numpy<br/>Calculations]
    end
    
    subgraph "Infrastructure"
        F[Redis<br/>Caching & Rate Limit]
        G[Docker<br/>Containerization]
        H[Environment Config<br/>.env]
    end
    
    A --> B
    A --> C
    A --> D
    A --> E
    A --> F
    G --> A
    H --> A
    
    style A fill:#3776ab,color:#fff
    style B fill:#0088cc,color:#fff
    style C fill:#f0b90b,color:#000
    style F fill:#dc382d,color:#fff
    style G fill:#2496ed,color:#fff
```

## Alert Message Flow

```mermaid
graph LR
    A[Spike Detected] --> B[Alert Manager]
    B --> C{Filter Rules}
    C -->|Pass| D[Format Message]
    C -->|Fail| E[Discard]
    D --> F[Rate Limiter]
    F --> G[Telegram API]
    G --> H[User/Channel]
    
    style A fill:#f66,stroke:#333,stroke-width:2px
    style H fill:#6f9,stroke:#333,stroke-width:2px
```

## Project Structure Tree

```
futu_vol_alert/
│
├── 📁 src/
│   ├── 📁 bot/
│   │   ├── telegram_bot.py      🤖 Bot handler
│   │   └── commands.py          📝 User commands
│   │
│   ├── 📁 data/
│   │   ├── binance_client.py    🔌 API wrapper
│   │   └── volume_calculator.py 📊 Volume math
│   │
│   ├── 📁 detector/
│   │   ├── spike_detector.py     🔍 Spike logic
│   │   └── baseline.py          📈 Baseline calc
│   │
│   ├── 📁 alert/
│   │   ├── alert_manager.py     🚨 Alert engine
│   │   └── formatter.py         ✉️ Message format
│   │
│   └── 📁 utils/
│       ├── config.py            ⚙️ Config loader
│       ├── logger.py            📋 Logging
│       └── cache.py             💾 Redis cache
│
├── 📁 tests/
│   ├── test_detector.py
│   ├── test_volume.py
│   └── test_alerts.py
│
├── 📁 docker/
│   └── Dockerfile
│
├── .env.example
├── requirements.txt
├── README.md
└── main.py                      🚀 Entry point
```

