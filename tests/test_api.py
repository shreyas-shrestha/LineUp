# tests/test_api.py - API Tests
import pytest
import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app_refactored import app
from models import init_db, SessionLocal, DBSocialPost, DBAppointment, DBPortfolioItem
from config import Config


@pytest.fixture
def client():
    """Create test client"""
    Config.DATABASE_URL = "sqlite:///:memory:"  # Use in-memory database for tests
    app.config['TESTING'] = True
    
    with app.test_client() as client:
        with app.app_context():
            init_db()
        yield client


@pytest.fixture
def db_session():
    """Create database session for tests"""
    session = SessionLocal()
    yield session
    session.close()


# ============================================================================
# ROOT & HEALTH TESTS
# ============================================================================

def test_index(client):
    """Test index endpoint"""
    response = client.get('/')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['service'] == 'LineUp AI Backend'
    assert 'endpoints' in data


def test_health(client):
    """Test health endpoint"""
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'


def test_config(client):
    """Test config endpoint"""
    response = client.get('/config')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'hasGemini' in data
    assert 'backendVersion' in data


# ============================================================================
# SOCIAL FEED TESTS
# ============================================================================

def test_get_social_posts_empty(client):
    """Test getting social posts when empty"""
    response = client.get('/social')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'posts' in data
    assert isinstance(data['posts'], list)


def test_create_social_post(client):
    """Test creating a social post"""
    post_data = {
        'username': 'test_user',
        'avatar': 'https://example.com/avatar.jpg',
        'image': 'data:image/jpeg;base64,/9j/4AAQSkZJRg...',
        'caption': 'Test caption for social post'
    }
    
    response = client.post('/social',
                          data=json.dumps(post_data),
                          content_type='application/json')
    
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['success'] == True
    assert 'post' in data
    assert data['post']['username'] == 'test_user'


def test_create_social_post_validation_error(client):
    """Test creating post with invalid data"""
    post_data = {
        'username': '',  # Invalid - empty username
        'image': 'short',  # Invalid - too short
        'caption': 'Test'
    }
    
    response = client.post('/social',
                          data=json.dumps(post_data),
                          content_type='application/json')
    
    assert response.status_code == 400


# ============================================================================
# APPOINTMENT TESTS
# ============================================================================

def test_get_appointments_empty(client):
    """Test getting appointments when empty"""
    response = client.get('/appointments')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'appointments' in data
    assert isinstance(data['appointments'], list)


def test_create_appointment(client):
    """Test creating an appointment"""
    appointment_data = {
        'client_name': 'John Doe',
        'client_id': 'client_123',
        'barber_name': 'Best Barber Shop',
        'barber_id': 'barber_456',
        'date': '2025-12-31',
        'time': '14:00',
        'service': 'Haircut + Beard',
        'price': '$65',
        'notes': 'Please use scissors only'
    }
    
    response = client.post('/appointments',
                          data=json.dumps(appointment_data),
                          content_type='application/json')
    
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['success'] == True
    assert data['appointment']['client_name'] == 'John Doe'
    assert data['appointment']['status'] == 'pending'


def test_create_appointment_past_date(client):
    """Test creating appointment with past date"""
    appointment_data = {
        'client_name': 'John Doe',
        'barber_name': 'Best Barber Shop',
        'barber_id': 'barber_456',
        'date': '2020-01-01',  # Past date
        'time': '14:00',
        'service': 'Haircut'
    }
    
    response = client.post('/appointments',
                          data=json.dumps(appointment_data),
                          content_type='application/json')
    
    assert response.status_code == 400


def test_create_appointment_invalid_time(client):
    """Test creating appointment with invalid time"""
    appointment_data = {
        'client_name': 'John Doe',
        'barber_name': 'Best Barber Shop',
        'barber_id': 'barber_456',
        'date': '2025-12-31',
        'time': '25:99',  # Invalid time
        'service': 'Haircut'
    }
    
    response = client.post('/appointments',
                          data=json.dumps(appointment_data),
                          content_type='application/json')
    
    assert response.status_code == 400


# ============================================================================
# PORTFOLIO TESTS
# ============================================================================

def test_get_portfolio_empty(client):
    """Test getting portfolio when empty"""
    response = client.get('/portfolio')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'portfolio' in data
    assert isinstance(data['portfolio'], list)


def test_add_portfolio_item(client):
    """Test adding portfolio item"""
    portfolio_data = {
        'barber_id': 'barber_123',
        'style_name': 'Modern Fade',
        'image': 'data:image/jpeg;base64,/9j/4AAQSkZJRg...',
        'description': 'Clean fade with textured top'
    }
    
    response = client.post('/portfolio',
                          data=json.dumps(portfolio_data),
                          content_type='application/json')
    
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['success'] == True
    assert data['work']['style_name'] == 'Modern Fade'


# ============================================================================
# BARBER DISCOVERY TESTS
# ============================================================================

def test_get_barbers(client):
    """Test finding barbers"""
    response = client.get('/barbers?location=Atlanta,GA')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'barbers' in data
    assert 'location' in data
    assert isinstance(data['barbers'], list)


def test_get_barbers_with_styles(client):
    """Test finding barbers with style filters"""
    response = client.get('/barbers?location=NewYork,NY&styles=fade,undercut')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'barbers' in data


# ============================================================================
# ANALYSIS TESTS
# ============================================================================

def test_analyze_endpoint_no_image(client):
    """Test analyze endpoint without image"""
    response = client.post('/analyze',
                          data=json.dumps({'payload': {'contents': []}}),
                          content_type='application/json')
    
    # Should return 400 or return mock data
    assert response.status_code in [200, 400]


def test_analyze_endpoint_with_mock_data(client):
    """Test analyze endpoint returns mock data when API unavailable"""
    # This will use mock data since we don't have a real Gemini API key in tests
    payload = {
        'payload': {
            'contents': [
                {
                    'parts': [
                        {'text': 'Analyze this'},
                        {
                            'inlineData': {
                                'mimeType': 'image/jpeg',
                                'data': '/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDA...'  # Truncated valid base64
                            }
                        }
                    ]
                }
            ]
        }
    }
    
    response = client.post('/analyze',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'analysis' in data
    assert 'recommendations' in data


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

def test_404_error(client):
    """Test 404 error handling"""
    response = client.get('/nonexistent-endpoint')
    assert response.status_code == 404
    data = json.loads(response.data)
    assert 'error' in data


def test_cors_headers(client):
    """Test CORS headers are present"""
    response = client.get('/')
    assert 'Access-Control-Allow-Origin' in response.headers


# ============================================================================
# RATE LIMITING TESTS
# ============================================================================

def test_rate_limiting():
    """Test that rate limiting is configured"""
    # Note: Actual rate limit testing would require making many requests
    # This just checks the limiter is configured
    from app_refactored import limiter
    assert limiter is not None


# ============================================================================
# VALIDATION TESTS
# ============================================================================

def test_appointment_validation():
    """Test Pydantic appointment validation"""
    from models import AppointmentCreate
    from pydantic import ValidationError
    
    # Valid appointment
    valid_data = {
        'client_name': 'John Doe',
        'barber_name': 'Barber Shop',
        'barber_id': 'barber_1',
        'date': '2025-12-31',
        'time': '14:00',
        'service': 'Haircut'
    }
    
    appointment = AppointmentCreate(**valid_data)
    assert appointment.client_name == 'John Doe'
    
    # Invalid appointment - past date
    invalid_data = valid_data.copy()
    invalid_data['date'] = '2020-01-01'
    
    with pytest.raises(ValidationError):
        AppointmentCreate(**invalid_data)


def test_social_post_validation():
    """Test Pydantic social post validation"""
    from models import SocialPostCreate
    from pydantic import ValidationError
    
    # Valid post
    valid_data = {
        'username': 'test_user',
        'image': 'data:image/jpeg;base64,validbase64data',
        'caption': 'Test caption'
    }
    
    post = SocialPostCreate(**valid_data)
    assert post.username == 'test_user'
    
    # Invalid post - empty username
    invalid_data = valid_data.copy()
    invalid_data['username'] = ''
    
    with pytest.raises(ValidationError):
        SocialPostCreate(**invalid_data)


# ============================================================================
# DATABASE TESTS
# ============================================================================

def test_database_initialization():
    """Test database tables are created"""
    from models import Base, engine
    
    # Check tables exist
    assert DBSocialPost.__tablename__ in Base.metadata.tables
    assert DBAppointment.__tablename__ in Base.metadata.tables
    assert DBPortfolioItem.__tablename__ in Base.metadata.tables


# ============================================================================
# SERVICE TESTS
# ============================================================================

def test_cache_service():
    """Test cache service"""
    from services import CacheService
    
    # Test set and get
    CacheService.set('test_key', {'data': 'test'}, ttl=60)
    result = CacheService.get('test_key')
    assert result is not None
    assert result['data'] == 'test'
    
    # Test delete
    CacheService.delete('test_key')
    result = CacheService.get('test_key')
    assert result is None


def test_gemini_service_mock():
    """Test Gemini service returns mock data"""
    from services import GeminiService
    
    result = GeminiService._get_mock_analysis()
    assert 'analysis' in result
    assert 'recommendations' in result
    assert len(result['recommendations']) == 6


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=.', '--cov-report=html'])

