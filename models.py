# models.py - Database Models and Pydantic Validators
from datetime import datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel, validator, Field
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import Config

# SQLAlchemy Setup (SQLite - completely free, no setup!)
engine = create_engine(Config.DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ============================================================================
# DATABASE MODELS (SQLAlchemy)
# ============================================================================

class DBSocialPost(Base):
    __tablename__ = "social_posts"
    
    id = Column(String, primary_key=True)
    username = Column(String, nullable=False)
    avatar = Column(String)
    image = Column(Text, nullable=False)  # Base64 or URL
    caption = Column(Text)
    likes = Column(Integer, default=0)
    liked = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.utcnow)


class DBAppointment(Base):
    __tablename__ = "appointments"
    
    id = Column(String, primary_key=True)
    client_name = Column(String, nullable=False)
    client_id = Column(String, nullable=False)
    barber_name = Column(String, nullable=False)
    barber_id = Column(String, nullable=False)
    date = Column(String, nullable=False)  # YYYY-MM-DD format
    time = Column(String, nullable=False)  # HH:MM format
    service = Column(String, nullable=False)
    price = Column(String)
    status = Column(String, default="pending")
    notes = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)


class DBPortfolioItem(Base):
    __tablename__ = "portfolio_items"
    
    id = Column(String, primary_key=True)
    barber_id = Column(String, nullable=False)
    style_name = Column(String, nullable=False)
    image = Column(Text, nullable=False)
    description = Column(Text)
    likes = Column(Integer, default=0)
    date = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)


class DBSubscriptionPackage(Base):
    __tablename__ = "subscription_packages"
    
    id = Column(String, primary_key=True)
    barber_id = Column(String, nullable=False)
    barber_name = Column(String)
    title = Column(String, nullable=False)
    description = Column(Text)
    price = Column(String)
    num_cuts = Column(Integer)
    duration_months = Column(Integer)
    discount = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)


class DBClientSubscription(Base):
    __tablename__ = "client_subscriptions"
    
    id = Column(String, primary_key=True)
    client_id = Column(String, nullable=False)
    client_name = Column(String)
    package_id = Column(String, nullable=False)
    package_title = Column(String)
    barber_id = Column(String)
    barber_name = Column(String)
    price = Column(String)
    num_cuts = Column(Integer)
    remaining_cuts = Column(Integer)
    purchase_date = Column(DateTime)
    expiry_date = Column(DateTime)
    status = Column(String, default="active")
    timestamp = Column(DateTime, default=datetime.utcnow)


# Create all tables
def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)


# ============================================================================
# PYDANTIC VALIDATION MODELS
# ============================================================================

class SocialPostCreate(BaseModel):
    """Validation for creating social posts"""
    username: str = Field(..., min_length=1, max_length=50)
    avatar: Optional[str] = Field(default="https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100&h=100&fit=crop&crop=face")
    image: str = Field(..., min_length=10)
    caption: str = Field(..., min_length=1, max_length=500)
    
    @validator('username')
    def validate_username(cls, v):
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username can only contain letters, numbers, underscores, and hyphens')
        return v


class AppointmentCreate(BaseModel):
    """Validation for creating appointments"""
    client_name: str = Field(..., min_length=1, max_length=100)
    client_id: str = Field(default="current-user")
    barber_name: str = Field(..., min_length=1, max_length=100)
    barber_id: str = Field(..., min_length=1)
    date: str = Field(..., pattern=r'^\d{4}-\d{2}-\d{2}$')
    time: str = Field(..., pattern=r'^\d{2}:\d{2}$')
    service: str = Field(..., min_length=1, max_length=200)
    price: Optional[str] = Field(default="$0")
    notes: Optional[str] = Field(default="", max_length=1000)
    
    @validator('date')
    def validate_date(cls, v):
        try:
            appointment_date = datetime.strptime(v, '%Y-%m-%d')
            if appointment_date.date() < datetime.now().date():
                raise ValueError('Appointment date cannot be in the past')
            # Limit to 6 months in advance
            if appointment_date > datetime.now() + timedelta(days=180):
                raise ValueError('Cannot book more than 6 months in advance')
            return v
        except ValueError as e:
            if "does not match format" in str(e):
                raise ValueError('Invalid date format. Use YYYY-MM-DD')
            raise e
    
    @validator('time')
    def validate_time(cls, v):
        try:
            hour, minute = map(int, v.split(':'))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError('Invalid time')
            # Business hours check
            if hour < 8 or hour > 20:
                raise ValueError('Bookings only available between 8 AM and 8 PM')
            return v
        except (ValueError, AttributeError):
            raise ValueError('Invalid time format. Use HH:MM')


class AppointmentStatusUpdate(BaseModel):
    """Validation for updating appointment status"""
    status: str = Field(..., pattern=r'^(pending|confirmed|cancelled|completed)$')


class PortfolioItemCreate(BaseModel):
    """Validation for portfolio items"""
    barber_id: str = Field(default="current-barber")
    style_name: str = Field(..., min_length=1, max_length=100)
    image: str = Field(..., min_length=10)
    description: str = Field(..., min_length=1, max_length=1000)


class SubscriptionPackageCreate(BaseModel):
    """Validation for subscription packages"""
    barber_id: str = Field(default="current-barber")
    barber_name: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=500)
    num_cuts: int = Field(..., ge=1, le=50)
    duration_months: int = Field(..., ge=1, le=12)
    price: str = Field(..., pattern=r'^\$?\d+(\.\d{2})?$')
    discount: Optional[str] = Field(default="", max_length=50)
    
    @validator('num_cuts')
    def validate_num_cuts(cls, v):
        if v <= 0:
            raise ValueError('Number of cuts must be positive')
        return v


class ImageAnalysisRequest(BaseModel):
    """Validation for AI image analysis"""
    payload: dict
    
    @validator('payload')
    def validate_payload(cls, v):
        if 'contents' not in v:
            raise ValueError('Missing contents in payload')
        if not isinstance(v['contents'], list) or len(v['contents']) == 0:
            raise ValueError('Contents must be a non-empty list')
        return v


class VirtualTryOnRequest(BaseModel):
    """Validation for virtual try-on requests"""
    userPhoto: str = Field(..., min_length=100)
    styleDescription: str = Field(..., min_length=1, max_length=200)
    
    @validator('userPhoto')
    def validate_photo(cls, v):
        # Basic validation that it looks like base64
        if not v or len(v) < 100:
            raise ValueError('Invalid image data')
        return v


class LocationQuery(BaseModel):
    """Validation for location-based queries"""
    location: str = Field(..., min_length=2, max_length=200)
    styles: Optional[str] = Field(default="")
    
    @validator('location')
    def validate_location(cls, v):
        # Basic sanitization
        if any(char in v for char in ['<', '>', '&', '"', "'"]):
            raise ValueError('Invalid characters in location')
        return v.strip()


# ============================================================================
# DATABASE HELPER FUNCTIONS
# ============================================================================

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def to_dict(db_object):
    """Convert SQLAlchemy object to dictionary"""
    return {c.name: getattr(db_object, c.name) for c in db_object.__table__.columns}

