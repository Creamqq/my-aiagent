from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.dialects.postgresql import TEXT as PG_TEXT
from sqlalchemy.dialects.mysql import LONGTEXT
from datetime import datetime
from config import settings

Base = declarative_base()

def get_content_column_type():
    if settings.DB_TYPE == "mysql":
        return LONGTEXT
    else:
        return PG_TEXT

class Chat(Base):
    __tablename__ = 'chats'
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(100), nullable=False, default='global')
    title = Column(String(200), nullable=False)
    type = Column(Integer, default=1)  # 1=主界面对话, 2=金融助手对话
    status = Column(Integer, default=1)  # 0=已删除(软删除), 1=正常
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = 'messages'
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    chat_id = Column(Integer, ForeignKey('chats.id'), nullable=False)
    user_id = Column(String(100), nullable=False, default='global')
    role = Column(String(50), nullable=False)
    content = Column(get_content_column_type(), nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    chat = relationship("Chat", back_populates="messages")

class ModelConfig(Base):
    __tablename__ = 'model_configs'
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(100), nullable=False, default='global')  # 用户ID，'global'表示全局配置
    name = Column(String(100), nullable=False)
    api_key = Column(String(500), nullable=False)
    api_url = Column(String(500), nullable=False)
    status = Column(Integer, default=1)  # 0=已删除(软删除), 1=正常
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_user_name', 'user_id', 'name'),  # 确保同一用户下模型名称唯一
    )

class FeatureModelMapping(Base):
    __tablename__ = 'feature_model_mappings'
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    feature_name = Column(String(100), nullable=False, unique=True)  # 功能名称，如'chat_title'
    model_name = Column(String(100), nullable=False)  # 使用的模型名称
    user_id = Column(String(100), nullable=False, default='global')  # 用户ID，'global'表示全局配置
    status = Column(Integer, default=1)  # 0=已删除(软删除), 1=正常
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_feature_user', 'feature_name', 'user_id'),  # 确保同一用户下功能名称唯一
    )

class SysUser(Base):
    __tablename__ = 'sys_user'
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(100), nullable=False, unique=True, index=True)
    username = Column(String(100), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    default_model_id = Column(Integer, ForeignKey('model_configs.id'), nullable=True)
    system_prompt = Column(Text, nullable=True)
    status = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class FinanceConfig(Base):
    __tablename__ = 'finance_config'
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(100), nullable=False, unique=True, index=True)
    default_model_id = Column(Integer, ForeignKey('model_configs.id'), nullable=True)
    system_prompt = Column(Text, nullable=True)
    kuaiqi_account = Column(String(100), nullable=True)
    kuaiqi_password = Column(String(255), nullable=True)
    status = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ChartImage(Base):
    __tablename__ = 'chart_images'
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(100), nullable=False, index=True)
    chat_id = Column(Integer, ForeignKey('chats.id'), nullable=True)
    message_id = Column(Integer, ForeignKey('messages.id'), nullable=True)
    symbol = Column(String(100), nullable=False)
    chart_type = Column(String(50), nullable=False)
    duration_seconds = Column(Integer, nullable=True)
    image_base64 = Column(get_content_column_type(), nullable=False)
    image_format = Column(String(10), default='png')
    data_count = Column(Integer, default=0)
    status = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_chart_user_chat', 'user_id', 'chat_id'),
    )

DATABASE_URL = str(settings.DATABASE_URL)

engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=30,
    pool_timeout=60,
    pool_recycle=1800,
    pool_pre_ping=True,
    echo=False
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
