import json
from sqlalchemy import create_engine, Column, Integer, String, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from config import DATABASE_URL, DEFAULT_SETTINGS

# Настройка SQLAlchemy
engine = create_engine(DATABASE_URL)
Base = declarative_base()
Session = sessionmaker(bind=engine)

class User(Base):
    """Модель пользователя для хранения настроек."""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True)
    settings = Column(JSON, default=lambda: DEFAULT_SETTINGS)
    
    def __repr__(self):
        return f"<User(id={self.user_id})>"

def init_db():
    """Инициализация базы данных."""
    Base.metadata.create_all(engine)

def get_user(user_id):
    """Получить пользователя по ID."""
    session = Session()
    user = session.query(User).filter_by(user_id=user_id).first()
    session.close()
    return user

def get_or_create_user(user_id):
    """Получить пользователя или создать нового."""
    session = Session()
    user = session.query(User).filter_by(user_id=user_id).first()
    
    if user is None:
        user = User(user_id=user_id, settings=DEFAULT_SETTINGS)
        session.add(user)
        session.commit()
    
    session.close()
    return user

def update_user_settings(user_id, settings):
    """Обновить настройки пользователя."""
    session = Session()
    user = session.query(User).filter_by(user_id=user_id).first()
    
    if user:
        user.settings.update(settings)
        session.commit()
    
    session.close()
    return user

def get_user_settings(user_id):
    """Получить настройки пользователя."""
    user = get_or_create_user(user_id)
    return user.settings
