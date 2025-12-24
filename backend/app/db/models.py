"""Database models."""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import json

Base = declarative_base()


class Trade(Base):
    """Trade record for delta-neutral positions."""
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    client_request_id = Column(String, unique=True, index=True, nullable=True)  # For idempotency
    symbol = Column(String, index=True)
    strategy_type = Column(String)  # 'delta_neutral', 'single_order', etc.
    status = Column(String)  # 'pending', 'open', 'closed', 'failed', 'simulated'
    notional = Column(Float)
    spot_order_id = Column(String, nullable=True)
    perp_order_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    meta_data = Column(JSON, nullable=True)  # Additional data (renamed from 'metadata' to avoid SQLAlchemy reserved word)


class Order(Base):
    """Order record."""
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    market_type = Column(String)  # 'spot' or 'futures'
    side = Column(String)  # 'buy', 'sell', 'long', 'short'
    order_type = Column(String)  # 'market', 'limit'
    qty = Column(Float)
    price = Column(Float, nullable=True)  # None for market orders
    status = Column(String)  # 'pending', 'filled', 'cancelled', 'failed', 'simulated'
    exchange_order_id = Column(String, nullable=True)
    fill_price = Column(Float, nullable=True)
    fill_qty = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    meta_data = Column(JSON, nullable=True)  # Additional data (renamed from 'metadata' to avoid SQLAlchemy reserved word)


class EventLog(Base):
    """Event log for audit trail."""
    __tablename__ = "event_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    level = Column(String)  # 'info', 'warning', 'error'
    message = Column(Text)
    context_json = Column(JSON, nullable=True)
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "level": self.level,
            "message": self.message,
            "context": self.context_json
        }
