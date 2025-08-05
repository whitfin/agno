"""Unit tests for Google Calendar Tools."""

import json
import os
import tempfile
from unittest.mock import Mock, mock_open, patch

import pytest

from agno.tools.googlecalendar import GoogleCalendarTools


class TestGoogleCalendarToolsInitialization:
    """Test initialization and configuration of Google Calendar tools."""

    def test_init_with_access_token(self):
        """Test initialization with access token."""
        tools = GoogleCalendarTools(access_token="test_token")
        assert tools.access_token == "test_token"
        assert tools.calendar_id == "primary"
        assert tools.creds is not None
        assert tools.service is None

    def test_init_with_credentials_path(self):
        """Test initialization with credentials file path."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"installed": {"client_id": "test"}}, f)
            temp_file = f.name

        try:
            tools = GoogleCalendarTools(credentials_path=temp_file)
            assert tools.credentials_path == temp_file
            assert tools.calendar_id == "primary"
            assert tools.creds is None
            assert tools.service is None
        finally:
            os.unlink(temp_file)

    def test_init_missing_credentials(self):
        """Test initialization without any credentials raises error."""
        with pytest.raises(ValueError, match="Token Path is invalid"):
            GoogleCalendarTools()

    def test_init_invalid_credentials_path(self):
        """Test initialization with invalid credentials path raises error."""
        with pytest.raises(ValueError, match="Credentials Path is invalid"):
            GoogleCalendarTools(credentials_path="./nonexistent.json")

    def test_init_with_existing_token_path(self):
        """Test initialization with existing token file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as token_file:
            json.dump({"token": "test_token"}, token_file)
            token_file_path = token_file.name

        try:
            tools = GoogleCalendarTools(token_path=token_file_path)
            assert tools.token_path == token_file_path
            assert tools.calendar_id == "primary"
        finally:
            os.unlink(token_file_path)

    def test_init_with_custom_calendar_id(self):
        """Test initialization with custom calendar ID."""
        tools = GoogleCalendarTools(access_token="test_token", calendar_id="custom@example.com")
        assert tools.calendar_id == "custom@example.com"
        assert tools.access_token == "test_token"

    def test_init_with_all_tools_registered(self):
        """Test that all tools are properly registered during initialization."""
        tools = GoogleCalendarTools(access_token="test_token")

        # Check that all expected tools are registered
        tool_names = [func.name for func in tools.functions.values()]
        expected_tools = [
            "list_events",
            "create_event",
            "update_event",
            "delete_event",
            "fetch_all_events",
            "find_available_slots",
            "list_calendars",
        ]

        for tool_name in expected_tools:
            assert tool_name in tool_names, f"Tool {tool_name} should be registered"

        # Verify we have the expected number of tools
        assert len(tool_names) == len(expected_tools)


class TestAuthentication:
    """Test authentication methods."""

    @patch("agno.tools.googlecalendar.Credentials")
    @patch("agno.tools.googlecalendar.build")
    def test_auth_with_token(self, mock_build, mock_credentials):
        """Test authentication with access token."""
        mock_service = Mock()
        mock_build.return_value = mock_service

        tools = GoogleCalendarTools(access_token="test_token")
        tools._auth()

        # Token-based auth should return early
        assert tools.service is None

    @patch("agno.tools.googlecalendar.Credentials.from_authorized_user_file")
    @patch("agno.tools.googlecalendar.build")
    def test_auth_with_existing_token_file(self, mock_build, mock_from_file):
        """Test authentication with existing token file."""
        mock_creds = Mock()
        mock_creds.valid = True
        mock_from_file.return_value = mock_creds
        mock_service = Mock()
        mock_build.return_value = mock_service

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as token_file:
            json.dump({"token": "test_token"}, token_file)
            token_file_path = token_file.name

        try:
            tools = GoogleCalendarTools(token_path=token_file_path)
            tools._auth()

            mock_from_file.assert_called_once_with(token_file_path, ["https://www.googleapis.com/auth/calendar"])
            assert tools.creds == mock_creds
        finally:
            os.unlink(token_file_path)

    @patch("agno.tools.googlecalendar.InstalledAppFlow.from_client_secrets_file")
    @patch("builtins.open", new_callable=mock_open)
    def test_auth_with_oauth_flow(self, mock_file, mock_flow):
        """Test authentication with OAuth flow."""
        mock_flow_instance = Mock()
        mock_creds = Mock()
        mock_creds.valid = True
        mock_creds.to_json.return_value = '{"token": "test"}'
        mock_flow_instance.run_local_server.return_value = mock_creds
        mock_flow.return_value = mock_flow_instance

        # Create proper Google OAuth client secrets format
        client_secrets = {
            "installed": {
                "client_id": "test_client_id.apps.googleusercontent.com",
                "client_secret": "test_client_secret",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(client_secrets, f)
            temp_file = f.name

        try:
            tools = GoogleCalendarTools(credentials_path=temp_file)
            # Create a fake token path for saving
            tools.token_path = "test_token.json"
            tools.creds = None  # Simulate no existing credentials
            tools._auth()

            mock_flow.assert_called_once()
            mock_flow_instance.run_local_server.assert_called_once()
            assert tools.creds == mock_creds
        finally:
            os.unlink(temp_file)


class TestListEvents:
    """Test list_events method."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch("agno.tools.googlecalendar.build"):
            self.tools = GoogleCalendarTools(access_token="test_token")
            self.mock_service = Mock()
            self.tools.service = self.mock_service

    def test_list_events_success(self):
        """Test successful event listing."""
        mock_events = [{"id": "1", "summary": "Test Event 1"}, {"id": "2", "summary": "Test Event 2"}]
        self.mock_service.events().list().execute.return_value = {"items": mock_events}

        result = self.tools.list_events(limit=2)
        result_data = json.loads(result)

        assert result_data == mock_events
        # Check that the service was called (may be called multiple times due to chaining)
        assert self.mock_service.events().list.call_count >= 1

    def test_list_events_no_events(self):
        """Test listing events when none exist."""
        self.mock_service.events().list().execute.return_value = {"items": []}

        result = self.tools.list_events()
        result_data = json.loads(result)

        assert result_data["message"] == "No upcoming events found."

    def test_list_events_with_start_date(self):
        """Test listing events with specific start date."""
        mock_events = [{"id": "1", "summary": "Test Event"}]
        self.mock_service.events().list().execute.return_value = {"items": mock_events}

        result = self.tools.list_events(start_date="2025-07-19T10:00:00")
        result_data = json.loads(result)

        assert result_data == mock_events

    def test_list_events_invalid_date_format(self):
        """Test listing events with invalid date format."""
        result = self.tools.list_events(start_date="invalid-date")
        result_data = json.loads(result)

        assert "error" in result_data
        assert "Invalid date format" in result_data["error"]

    def test_list_events_http_error(self):
        """Test handling of HTTP errors."""
        from googleapiclient.errors import HttpError

        # Create a mock HttpError
        mock_response = Mock()
        mock_response.status = 403
        mock_response.reason = "Forbidden"

        http_error = HttpError(mock_response, b'{"error": {"message": "Forbidden"}}')
        self.mock_service.events().list().execute.side_effect = http_error

        result = self.tools.list_events()
        result_data = json.loads(result)

        assert "error" in result_data
        assert "An error occurred" in result_data["error"]

    def test_list_events_no_service(self):
        """Test list_events when service is not initialized."""
        # Create tools instance and mock the build to return None
        with patch("agno.tools.googlecalendar.build", return_value=None):
            tools = GoogleCalendarTools(access_token="test_token")

            # Make sure service stays None
            tools.service = None

            result = tools.list_events()
            result_data = json.loads(result)

            assert result_data["error"] == "Google Calendar service not initialized"


class TestCreateEvent:
    """Test create_event method."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch("agno.tools.googlecalendar.build"):
            self.tools = GoogleCalendarTools(access_token="test_token")
            self.mock_service = Mock()
            self.tools.service = self.mock_service

    def test_create_event_success(self):
        """Test successful event creation."""
        mock_event = {"id": "test_id", "summary": "Test Event"}
        self.mock_service.events().insert().execute.return_value = mock_event

        result = self.tools.create_event(
            start_date="2025-07-19T10:00:00",
            end_date="2025-07-19T11:00:00",
            title="Test Event",
            description="Test Description",
        )
        result_data = json.loads(result)

        assert result_data == mock_event

    def test_create_event_with_attendees(self):
        """Test event creation with attendees."""
        mock_event = {"id": "test_id", "summary": "Test Event"}
        self.mock_service.events().insert().execute.return_value = mock_event

        result = self.tools.create_event(
            start_date="2025-07-19T10:00:00",
            end_date="2025-07-19T11:00:00",
            title="Test Event",
            attendees=["test1@example.com", "test2@example.com"],
        )
        result_data = json.loads(result)

        assert result_data == mock_event

    def test_create_event_with_google_meet(self):
        """Test event creation with Google Meet link."""
        mock_event = {"id": "test_id", "summary": "Test Event"}
        self.mock_service.events().insert().execute.return_value = mock_event

        result = self.tools.create_event(
            start_date="2025-07-19T10:00:00",
            end_date="2025-07-19T11:00:00",
            title="Test Event",
            add_google_meet_link=True,
        )
        result_data = json.loads(result)

        assert result_data == mock_event
        # Verify conferenceDataVersion was set
        call_args = self.mock_service.events().insert.call_args
        assert call_args[1]["conferenceDataVersion"] == 1

    def test_create_event_invalid_datetime(self):
        """Test event creation with invalid datetime format."""
        result = self.tools.create_event(start_date="invalid-date", end_date="2025-07-19T11:00:00", title="Test Event")
        result_data = json.loads(result)

        assert "error" in result_data
        assert "Invalid datetime format" in result_data["error"]


class TestUpdateEvent:
    """Test update_event method."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch("agno.tools.googlecalendar.build"):
            self.tools = GoogleCalendarTools(access_token="test_token")
            self.mock_service = Mock()
            self.tools.service = self.mock_service

    def test_update_event_success(self):
        """Test successful event update."""
        existing_event = {
            "id": "test_id",
            "summary": "Old Title",
            "start": {"dateTime": "2025-07-19T10:00:00", "timeZone": "UTC"},
            "end": {"dateTime": "2025-07-19T11:00:00", "timeZone": "UTC"},
        }
        updated_event = existing_event.copy()
        updated_event["summary"] = "New Title"

        self.mock_service.events().get().execute.return_value = existing_event
        self.mock_service.events().update().execute.return_value = updated_event

        result = self.tools.update_event(event_id="test_id", title="New Title")
        result_data = json.loads(result)

        assert result_data["summary"] == "New Title"

    def test_update_event_datetime(self):
        """Test updating event datetime."""
        existing_event = {
            "id": "test_id",
            "summary": "Test Event",
            "start": {"dateTime": "2025-07-19T10:00:00", "timeZone": "UTC"},
            "end": {"dateTime": "2025-07-19T11:00:00", "timeZone": "UTC"},
        }

        self.mock_service.events().get().execute.return_value = existing_event
        self.mock_service.events().update().execute.return_value = existing_event

        result = self.tools.update_event(
            event_id="test_id", start_date="2025-07-19T14:00:00", end_date="2025-07-19T15:00:00"
        )
        result_data = json.loads(result)

        assert "error" not in result_data


class TestDeleteEvent:
    """Test delete_event method."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch("agno.tools.googlecalendar.build"):
            self.tools = GoogleCalendarTools(access_token="test_token")
            self.mock_service = Mock()
            self.tools.service = self.mock_service

    def test_delete_event_success(self):
        """Test successful event deletion."""
        self.mock_service.events().delete().execute.return_value = None

        result = self.tools.delete_event(event_id="test_id")
        result_data = json.loads(result)

        assert result_data["success"] is True
        assert "deleted successfully" in result_data["message"]


class TestFetchAllEvents:
    """Test fetch_all_events method."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch("agno.tools.googlecalendar.build"):
            self.tools = GoogleCalendarTools(access_token="test_token")
            self.mock_service = Mock()
            self.tools.service = self.mock_service

    def test_fetch_all_events_success(self):
        """Test successful fetching of all events."""
        mock_events = [{"id": "1", "summary": "Event 1"}, {"id": "2", "summary": "Event 2"}]
        self.mock_service.events().list().execute.return_value = {"items": mock_events, "nextPageToken": None}

        result = self.tools.fetch_all_events()
        result_data = json.loads(result)

        assert result_data == mock_events

    def test_fetch_all_events_with_pagination(self):
        """Test fetching events with pagination."""
        page1_events = [{"id": "1", "summary": "Event 1"}]
        page2_events = [{"id": "2", "summary": "Event 2"}]

        self.mock_service.events().list().execute.side_effect = [
            {"items": page1_events, "nextPageToken": "token2"},
            {"items": page2_events, "nextPageToken": None},
        ]

        result = self.tools.fetch_all_events()
        result_data = json.loads(result)

        assert len(result_data) == 2
        assert result_data == page1_events + page2_events


class TestFindAvailableSlots:
    """Test find_available_slots method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tools = GoogleCalendarTools(access_token="test_token")
        self.mock_service = Mock()
        self.tools.service = self.mock_service

    @patch.object(GoogleCalendarTools, "fetch_all_events")
    @patch.object(GoogleCalendarTools, "_get_working_hours")
    def test_find_available_slots_success(self, mock_working_hours, mock_fetch):
        """Test successful finding of available slots."""
        # Mock working hours response
        mock_working_hours.return_value = json.dumps(
            {"start_hour": 9, "end_hour": 17, "timezone": "UTC", "locale": "en"}
        )

        # Mock no existing events
        mock_fetch.return_value = json.dumps([])

        result = self.tools.find_available_slots(
            start_date="2025-07-21", end_date="2025-07-21", duration_minutes=30
        )  # Monday, 30 min
        result_data = json.loads(result)

        assert "available_slots" in result_data
        assert "working_hours" in result_data
        assert "events_analyzed" in result_data
        assert isinstance(result_data["available_slots"], list)

    @patch.object(GoogleCalendarTools, "fetch_all_events")
    @patch.object(GoogleCalendarTools, "_get_working_hours")
    def test_find_available_slots_with_busy_times(self, mock_working_hours, mock_fetch):
        """Test finding available slots with existing events."""
        # Mock working hours response
        mock_working_hours.return_value = json.dumps(
            {"start_hour": 9, "end_hour": 17, "timezone": "UTC", "locale": "en"}
        )

        # Mock existing event that blocks 10:30-11:30 AM (shorter busy period)
        existing_events = [
            {"start": {"dateTime": "2025-07-19T10:30:00+00:00"}, "end": {"dateTime": "2025-07-19T11:30:00+00:00"}}
        ]
        mock_fetch.return_value = json.dumps(existing_events)

        result = self.tools.find_available_slots(start_date="2025-07-19", end_date="2025-07-19", duration_minutes=30)
        result_data = json.loads(result)

        assert "available_slots" in result_data
        assert "working_hours" in result_data
        assert "events_analyzed" in result_data
        assert result_data["events_analyzed"] == 1
        # Check that the response structure is correct (may or may not have slots)
        assert isinstance(result_data["available_slots"], list)

    @patch.object(GoogleCalendarTools, "fetch_all_events")
    @patch.object(GoogleCalendarTools, "_get_working_hours")
    def test_find_available_slots_guarantees_slots(self, mock_working_hours, mock_fetch):
        """Test finding available slots when there should definitely be some."""
        # Mock working hours response
        mock_working_hours.return_value = json.dumps(
            {"start_hour": 9, "end_hour": 17, "timezone": "UTC", "locale": "en"}
        )

        # Mock no existing events (completely free day)
        mock_fetch.return_value = json.dumps([])

        result = self.tools.find_available_slots(
            start_date="2025-07-21",
            end_date="2025-07-21",
            duration_minutes=30,  # Monday
        )
        result_data = json.loads(result)

        assert "available_slots" in result_data
        assert "working_hours" in result_data
        assert "events_analyzed" in result_data
        assert result_data["events_analyzed"] == 0
        # With no events and a full working day, we should have multiple slots
        slots = result_data["available_slots"]
        assert isinstance(slots, list)
        # Should have many 30-minute slots between 9 AM and 5 PM
        assert len(slots) >= 10  # Conservative estimate

    def test_find_available_slots_invalid_date(self):
        """Test finding available slots with invalid date format."""
        result = self.tools.find_available_slots(start_date="invalid-date", end_date="2025-07-19", duration_minutes=60)
        result_data = json.loads(result)

        assert "error" in result_data
        assert "Invalid date format" in result_data["error"]


class TestListCalendars:
    """Test list_calendars method."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch("agno.tools.googlecalendar.build"):
            self.tools = GoogleCalendarTools(access_token="test_token")
            self.mock_service = Mock()
            self.tools.service = self.mock_service

    def test_list_calendars_success(self):
        """Test successful calendar listing."""
        mock_calendars = {
            "items": [
                {
                    "id": "primary",
                    "summary": "John Doe",
                    "description": "Personal calendar",
                    "primary": True,
                    "accessRole": "owner",
                    "backgroundColor": "#ffffff",
                },
                {
                    "id": "work@company.com",
                    "summary": "Work Calendar",
                    "description": "Company work calendar",
                    "primary": False,
                    "accessRole": "writer",
                    "backgroundColor": "#4285f4",
                },
            ]
        }
        self.mock_service.calendarList().list().execute.return_value = mock_calendars

        result = self.tools.list_calendars()
        result_data = json.loads(result)

        assert "calendars" in result_data
        assert len(result_data["calendars"]) == 2
        assert result_data["current_default"] == "primary"

        # Check calendar data structure
        primary_cal = result_data["calendars"][0]
        assert primary_cal["id"] == "primary"
        assert primary_cal["name"] == "John Doe"
        assert primary_cal["primary"] is True
        assert primary_cal["access_role"] == "owner"

    def test_list_calendars_no_service(self):
        """Test list_calendars when service is not initialized."""
        with patch("agno.tools.googlecalendar.build", return_value=None):
            tools = GoogleCalendarTools(access_token="test_token")
            tools.service = None

            result = tools.list_calendars()
            result_data = json.loads(result)

            assert result_data["error"] == "Google Calendar service not initialized"

    def test_list_calendars_http_error(self):
        """Test handling of HTTP errors in list_calendars."""
        from googleapiclient.errors import HttpError

        mock_response = Mock()
        mock_response.status = 403
        mock_response.reason = "Forbidden"

        http_error = HttpError(mock_response, b'{"error": {"message": "Forbidden"}}')
        self.mock_service.calendarList().list().execute.side_effect = http_error

        result = self.tools.list_calendars()
        result_data = json.loads(result)

        assert "error" in result_data
        assert "An error occurred" in result_data["error"]


class TestErrorHandling:
    """Test error handling across all methods."""

    def test_methods_without_service_initialization(self):
        """Test that all methods handle missing service gracefully."""
        # Mock build to return None so service stays None
        with patch("agno.tools.googlecalendar.build", return_value=None):
            tools = GoogleCalendarTools(access_token="test_token")
            tools.service = None

            methods_to_test = [
                ("list_events", []),
                ("create_event", ["2025-07-19T10:00:00", "2025-07-19T11:00:00"]),
                ("update_event", ["test_id"]),
                ("delete_event", ["test_id"]),
                ("fetch_all_events", []),
                ("list_calendars", []),
            ]

            for method_name, args in methods_to_test:
                method = getattr(tools, method_name)
                result = method(*args)
                result_data = json.loads(result)

                assert "error" in result_data
                assert "not initialized" in result_data["error"]
