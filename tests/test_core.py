import pytest
import json
from fastapi import HTTPException
from app.database import crud
from app.errors.exceptions import ValidationError, NotFoundError, BaseAPIException
from app.config.settings import Settings
from app.utils.logging_config import setup_logging
import logging

@pytest.mark.unit
class TestSettings:
    def test_settings_validation(self):
        """Test settings validation and defaults"""
        settings = Settings()
        assert settings.API_V1_STR == "/api/v1"
        assert settings.PORT == 8000  # Default port value
        assert settings.PROJECT_NAME == "Balance Up API"
        assert settings.VERSION == "1.0.0"

    def test_settings_override(self, settings):
        """Test settings override through environment variables"""
        assert settings.DATABASE_URL == "sqlite:///:memory:"
        assert settings.PORT == 8011

    def test_environment_specific_settings(self, monkeypatch):
        """Test environment-specific configuration"""
        # Test development settings
        monkeypatch.setenv("ENVIRONMENT", "development")
        dev_settings = Settings(DEBUG=True)
        assert dev_settings.DEBUG is True
        assert "sqlite" in dev_settings.DATABASE_URL

        # Test production settings
        monkeypatch.setenv("ENVIRONMENT", "production")
        prod_settings = Settings(DEBUG=False)
        assert prod_settings.DEBUG is False

    def test_rate_limit_settings(self, settings):
        """Test rate limiting configuration"""
        assert settings.RATE_LIMIT_MAX_REQUESTS == 50
        assert settings.RATE_LIMIT_WINDOW == 60
        assert hasattr(settings, 'RATE_LIMIT_MAX_REQUESTS')
        assert hasattr(settings, 'RATE_LIMIT_WINDOW')

    def test_invalid_settings(self):
        """Test handling of invalid settings"""
        with pytest.raises(ValueError):
            Settings(PORT=-1)
        with pytest.raises(ValueError):
            Settings(RATE_LIMIT_MAX_REQUESTS=0)
        with pytest.raises(ValueError):
            Settings(RATE_LIMIT_WINDOW=0)

@pytest.mark.unit
class TestLogging:
    def test_json_logging_setup(self, caplog):
        """Test JSON structured logging configuration"""
        setup_logging()
        with caplog.at_level(logging.INFO):
            logger = logging.getLogger(__name__)
            test_message = "Test log message"
            logger.info(test_message)

            # Verify log record structure
            assert len(caplog.records) == 1
            record = caplog.records[0]
            assert record.message == test_message
            assert record.levelname == "INFO"

@pytest.mark.unit
class TestErrorHandling:
    def test_validation_error(self):
        """Test validation error response format"""
        error = ValidationError("Invalid input")
        with pytest.raises(ValidationError) as exc_info:
            raise error
        assert "422: Invalid input" in str(exc_info.value)

    def test_not_found_error(self):
        """Test not found error response format"""
        error = NotFoundError("Resource not found")
        with pytest.raises(NotFoundError) as exc_info:
            raise error
        assert "404: Resource not found" in str(exc_info.value)
        
    def test_custom_error_response(self, client):
        """Test custom error response structure"""
        error = BaseAPIException(
            status_code=400,
            detail="Custom error",
            error_code="CUSTOM_ERROR"
        )
        assert error.status_code == 400
        assert error.detail == "Custom error"
        assert error.error_code == "CUSTOM_ERROR"
        assert "400: Custom error" in str(error)

@pytest.mark.unit
class TestDatabase:
    def test_crud_operations(self, db_session):
        """Test basic CRUD operations"""
        from app.database.models import User, Penalty
        from datetime import datetime

        # Create test user
        test_user = User(
            username="testuser",
            email="test@example.com",
            created_at=datetime.utcnow()
        )
        db_session.add(test_user)
        db_session.commit()
        db_session.refresh(test_user)

        # Read
        db_user = db_session.query(User).filter(User.email == "test@example.com").first()
        assert db_user is not None
        assert db_user.username == "testuser"

        # Update
        db_user.username = "updateduser"
        db_session.commit()
        db_session.refresh(db_user)
        assert db_user.username == "updateduser"

        # Create penalty for user
        test_penalty = Penalty(
            user_id=db_user.id,
            amount=50.0,
            reason="Test penalty",
            created_at=datetime.utcnow()
        )
        db_session.add(test_penalty)
        db_session.commit()

        # Query relationships
        penalties = db_session.query(Penalty).filter(Penalty.user_id == db_user.id).all()
        assert len(penalties) == 1
        assert penalties[0].amount == 50.0

        # Delete
        db_session.delete(db_user)
        db_session.commit()
        assert db_session.query(User).filter(User.email == "test@example.com").first() is None

    def test_cascade_delete(self, db_session):
        """Test cascade delete behavior"""
        from app.database.models import User, Penalty
        from datetime import datetime

        # Create user and associated penalties
        user = User(
            username="cascadetest",
            email="cascade@example.com",
            created_at=datetime.utcnow()
        )
        db_session.add(user)
        db_session.commit()

        penalties = [
            Penalty(
                user_id=user.id,
                amount=10.0 * i,
                reason=f"Test penalty {i}",
                created_at=datetime.utcnow()
            )
            for i in range(3)
        ]
        db_session.add_all(penalties)
        db_session.commit()

        # Verify penalties exist
        assert db_session.query(Penalty).filter(Penalty.user_id == user.id).count() == 3

        # Delete user and verify penalties are handled correctly
        db_session.delete(user)
        db_session.commit()
        assert db_session.query(Penalty).filter(Penalty.user_id == user.id).count() == 0

    def test_unique_constraints(self, db_session):
        """Test database unique constraints"""
        from app.database.models import User
        from sqlalchemy.exc import IntegrityError
        from datetime import datetime

        # Create initial user
        user1 = User(
            username="uniquetest",
            email="unique@example.com",
            created_at=datetime.utcnow()
        )
        db_session.add(user1)
        db_session.commit()

        # Try to create user with same email
        user2 = User(
            username="uniquetest2",
            email="unique@example.com",
            created_at=datetime.utcnow()
        )
        with pytest.raises(IntegrityError):
            db_session.add(user2)
            db_session.commit()
        db_session.rollback()

        # Try to create user with same username
        user3 = User(
            username="uniquetest",
            email="unique2@example.com",
            created_at=datetime.utcnow()
        )
        with pytest.raises(IntegrityError):
            db_session.add(user3)
            db_session.commit()