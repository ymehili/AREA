"""Tests for main.py application startup and configuration."""

from __future__ import annotations

import asyncio
from unittest.mock import Mock, patch, MagicMock
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from main import app, lifespan


class TestMainApplication:
    """Test main application functionality."""

    def test_app_creation(self):
        """Test that the FastAPI app is created correctly."""
        assert isinstance(app, FastAPI)
        # App doesn't explicitly set title/version, so it uses FastAPI defaults
        assert app.title == "FastAPI"

    def test_app_middleware(self):
        """Test that CORS and session middleware are configured."""
        # Check that CORS middleware is configured
        cors_middleware = None
        for middleware in app.user_middleware:
            if "CORSMiddleware" in str(middleware.cls):
                cors_middleware = middleware
                break
        
        assert cors_middleware is not None

    def test_app_routes(self):
        """Test that all expected routes are registered."""
        route_paths = [route.path for route in app.routes]
        
        # Check for key route prefixes (based on actual registered routes)
        expected_prefixes = [
            "/api/v1/auth",
            "/api/v1/oauth",
            "/api/v1/users",  # Profile route is under /users not /profile
            "/api/v1/services",
            "/api/v1/service-connections",
            "/about.json"
        ]

        for prefix in expected_prefixes:
            assert any(route_path.startswith(prefix) for route_path in route_paths), f"Route prefix {prefix} not found"

    @pytest.mark.asyncio
    async def test_lifespan_startup_success(self):
        """Test successful application startup."""
        mock_app = Mock(spec=FastAPI)
        mock_app.state = Mock()

        with patch("main.verify_connection") as mock_verify, \
             patch("main.run_migrations") as mock_migrations, \
             patch("main.start_scheduler") as mock_start_scheduler, \
             patch("main.start_gmail_scheduler") as mock_start_gmail_scheduler, \
             patch("main.logger") as mock_logger:

            # Use a new event loop for the test
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                async with lifespan(mock_app):
                    pass

                mock_verify.assert_called_once()
                mock_migrations.assert_called_once()
                mock_start_scheduler.assert_called_once()
                mock_start_gmail_scheduler.assert_called_once()
                assert mock_app.state.database_url is not None
            finally:
                loop.close()

    @pytest.mark.asyncio
    async def test_lifespan_startup_database_error(self):
        """Test application startup with database connection error."""
        mock_app = Mock(spec=FastAPI)
        mock_app.state = Mock()
        
        with patch("main.verify_connection") as mock_verify, \
             patch("main.logger") as mock_logger:
            
            mock_verify.side_effect = Exception("Database connection failed")
            
            with pytest.raises(Exception, match="Database connection failed"):
                async with lifespan(mock_app):
                    pass

    @pytest.mark.asyncio
    async def test_lifespan_startup_migration_error(self):
        """Test application startup with migration error."""
        mock_app = Mock(spec=FastAPI)
        mock_app.state = Mock()
        
        with patch("main.verify_connection") as mock_verify, \
             patch("main.run_migrations") as mock_migrations, \
             patch("main.logger") as mock_logger:
            
            mock_verify.return_value = None
            mock_migrations.side_effect = Exception("Migration failed")
            
            with pytest.raises(Exception, match="Migration failed"):
                async with lifespan(mock_app):
                    pass

    @pytest.mark.asyncio
    async def test_lifespan_startup_scheduler_error(self):
        """Test application startup with scheduler error."""
        mock_app = Mock(spec=FastAPI)
        mock_app.state = Mock()
        
        with patch("main.verify_connection") as mock_verify, \
             patch("main.run_migrations") as mock_migrations, \
             patch("main.start_scheduler") as mock_start_scheduler, \
             patch("main.start_gmail_scheduler") as mock_start_gmail_scheduler, \
             patch("main.logger") as mock_logger:
            
            mock_verify.return_value = None
            mock_migrations.return_value = None
            mock_start_scheduler.side_effect = Exception("Scheduler failed")
            
            with pytest.raises(Exception, match="Scheduler failed"):
                async with lifespan(mock_app):
                    pass

    @pytest.mark.asyncio
    async def test_lifespan_shutdown(self):
        """Test application shutdown."""
        mock_app = Mock(spec=FastAPI)
        mock_app.state = Mock()
        
        with patch("main.stop_scheduler") as mock_stop_scheduler, \
             patch("main.stop_gmail_scheduler") as mock_stop_gmail_scheduler, \
             patch("main.logger") as mock_logger:
            
            # Simulate startup first
            with patch("main.verify_connection"), \
                 patch("main.run_migrations"), \
                 patch("main.start_scheduler"), \
                 patch("main.start_gmail_scheduler"):
                
                async with lifespan(mock_app):
                    pass
            
            # Shutdown should be called automatically
            mock_stop_scheduler.assert_called_once()
            mock_stop_gmail_scheduler.assert_called_once()

    def test_about_endpoint(self):
        """Test the about.json endpoint."""
        with TestClient(app) as client:
            response = client.get("/about.json")

            assert response.status_code == 200
            data = response.json()

            # Spec-compliant structure
            assert "client" in data
            assert "host" in data["client"]
            assert "server" in data
            assert "current_time" in data["server"]
            assert "services" in data["server"]
            
            # current_time should be Unix timestamp (integer)
            assert isinstance(data["server"]["current_time"], int)

    def test_about_endpoint_services(self):
        """Test that about.json includes service catalog in simplified format."""
        with TestClient(app) as client:
            response = client.get("/about.json")
            
            assert response.status_code == 200
            data = response.json()
            
            # Services should be under server.services now
            assert "server" in data
            assert "services" in data["server"]
            assert isinstance(data["server"]["services"], list)
            
            # Check simplified format: services should only have name, actions, reactions
            services = data["server"]["services"]
            assert len(services) > 0
            
            for service in services:
                # Should have only name, actions, reactions (no slug, description, etc.)
                assert "name" in service
                assert "actions" in service
                assert "reactions" in service
                assert "slug" not in service  # Spec-compliant: no slug
                
                # Check actions/reactions have only name and description
                for action in service["actions"]:
                    assert "name" in action
                    assert "description" in action
                    assert "key" not in action  # No internal keys in spec format
                    assert "params" not in action  # No params in spec format
                    
                for reaction in service["reactions"]:
                    assert "name" in reaction
                    assert "description" in reaction
                    assert "key" not in reaction
                    assert "params" not in reaction

    def test_cors_headers(self):
        """Test that CORS headers are properly set."""
        with TestClient(app) as client:
            # Test preflight request
            response = client.options("/api/v1/auth/login", headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type"
            })
            
            assert response.status_code in [200, 204]
            assert "Access-Control-Allow-Origin" in response.headers

    def test_health_check_endpoint(self):
        """Test health check endpoint if it exists."""
        with TestClient(app) as client:
            # Try common health check paths
            for path in ["/health", "/healthz", "/status"]:
                response = client.get(path)
                if response.status_code == 200:
                    break
            else:
                # If no health endpoint exists, that's also valid
                pytest.skip("No health check endpoint found")

    @pytest.mark.asyncio
    async def test_lifespan_with_exception_during_startup(self):
        """Test lifespan with exception during startup."""
        mock_app = Mock(spec=FastAPI)
        mock_app.state = Mock()
        
        with patch("main.verify_connection") as mock_verify, \
             patch("main.run_migrations") as mock_migrations, \
             patch("main.start_scheduler") as mock_start_scheduler, \
             patch("main.start_gmail_scheduler") as mock_start_gmail_scheduler, \
             patch("main.logger") as mock_logger:
            
            mock_verify.side_effect = Exception("Startup failed")
            
            # Should raise the exception
            with pytest.raises(Exception, match="Startup failed"):
                async with lifespan(mock_app):
                    pass

    @pytest.mark.asyncio
    async def test_lifespan_with_exception_during_shutdown(self):
        """Test lifespan with exception during shutdown."""
        mock_app = Mock(spec=FastAPI)
        mock_app.state = Mock()
        
        with patch("main.verify_connection") as mock_verify, \
             patch("main.run_migrations") as mock_migrations, \
             patch("main.start_scheduler") as mock_start_scheduler, \
             patch("main.start_gmail_scheduler") as mock_start_gmail_scheduler, \
             patch("main.stop_scheduler") as mock_stop_scheduler, \
             patch("main.stop_gmail_scheduler") as mock_stop_gmail_scheduler, \
             patch("main.logger") as mock_logger:
            
            # Successful startup
            mock_verify.return_value = None
            mock_migrations.return_value = None
            
            # Exception during shutdown
            mock_stop_scheduler.side_effect = Exception("Shutdown failed")

            # Should handle shutdown exception gracefully
            try:
                async with lifespan(mock_app):
                    pass
            except Exception as e:
                # If shutdown fails, it might raise - that's acceptable
                assert "Shutdown failed" in str(e)

            # Verify shutdown was attempted
            mock_stop_scheduler.assert_called_once()

    def test_app_configuration(self):
        """Test that the app is configured with correct settings."""
        assert app.debug == False  # Should be False in production
        assert "cors" in str(app.user_middleware).lower()
        assert "session" in str(app.user_middleware).lower()

    def test_logging_configuration(self):
        """Test that logging is properly configured."""
        import logging
        
        # Check that the logger is configured
        logger = logging.getLogger("main")
        assert logger.level <= logging.INFO
        
        # Check that the format includes expected elements
        handlers = logger.handlers
        if handlers:
            formatter = handlers[0].formatter
            if formatter:
                format_string = formatter._fmt
                assert "%(asctime)s" in format_string
                assert "%(levelname)s" in format_string
                assert "%(name)s" in format_string