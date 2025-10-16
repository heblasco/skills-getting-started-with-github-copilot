"""
Test cases for the FastAPI endpoints
"""
import pytest
from fastapi import status


class TestRootEndpoint:
    """Test the root endpoint"""
    
    def test_root_redirects_to_static(self, client):
        """Test that root endpoint redirects to static/index.html"""
        response = client.get("/")
        assert response.status_code == status.HTTP_200_OK
        # Should redirect and serve the HTML content
        assert "Mergington High School" in response.text


class TestActivitiesEndpoint:
    """Test the activities endpoint"""
    
    def test_get_activities(self, client, reset_activities):
        """Test getting all activities"""
        response = client.get("/activities")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        
        # Check that we have activities
        assert len(data) > 0
        
        # Check specific activities exist
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Gym Class" in data
        
        # Check activity structure
        chess_club = data["Chess Club"]
        assert "description" in chess_club
        assert "schedule" in chess_club
        assert "max_participants" in chess_club
        assert "participants" in chess_club
        
        # Check specific values
        assert chess_club["max_participants"] == 12
        assert isinstance(chess_club["participants"], list)
    
    def test_activities_have_required_fields(self, client, reset_activities):
        """Test that all activities have required fields"""
        response = client.get("/activities")
        data = response.json()
        
        required_fields = ["description", "schedule", "max_participants", "participants"]
        
        for activity_name, activity_data in data.items():
            for field in required_fields:
                assert field in activity_data, f"Activity '{activity_name}' missing field '{field}'"
            
            # Check data types
            assert isinstance(activity_data["max_participants"], int)
            assert isinstance(activity_data["participants"], list)
            assert isinstance(activity_data["description"], str)
            assert isinstance(activity_data["schedule"], str)


class TestSignupEndpoint:
    """Test the signup endpoint"""
    
    def test_signup_success(self, client, reset_activities):
        """Test successful signup"""
        email = "test@mergington.edu"
        activity = "Chess Club"
        
        # Get initial participant count
        response = client.get("/activities")
        initial_count = len(response.json()[activity]["participants"])
        
        # Sign up
        response = client.post(f"/activities/{activity}/signup?email={email}")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        assert activity in data["message"]
        
        # Verify participant was added
        response = client.get("/activities")
        updated_activity = response.json()[activity]
        assert len(updated_activity["participants"]) == initial_count + 1
        assert email in updated_activity["participants"]
    
    def test_signup_nonexistent_activity(self, client, reset_activities):
        """Test signup for non-existent activity"""
        response = client.post("/activities/NonExistent/signup?email=test@mergington.edu")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        data = response.json()
        assert "detail" in data
        assert "Activity not found" in data["detail"]
    
    def test_signup_duplicate_registration(self, client, reset_activities):
        """Test duplicate registration for same activity"""
        email = "test@mergington.edu"
        activity = "Chess Club"
        
        # First signup should succeed
        response = client.post(f"/activities/{activity}/signup?email={email}")
        assert response.status_code == status.HTTP_200_OK
        
        # Second signup should fail
        response = client.post(f"/activities/{activity}/signup?email={email}")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        data = response.json()
        assert "detail" in data
        assert "already signed up" in data["detail"]
    
    def test_signup_url_encoding(self, client, reset_activities):
        """Test signup with URL-encoded activity name and email"""
        email = "test.user+tag@mergington.edu"
        activity = "Programming Class"
        
        # URL encode the parameters
        encoded_activity = "Programming%20Class"
        encoded_email = "test.user%2Btag%40mergington.edu"
        
        response = client.post(f"/activities/{encoded_activity}/signup?email={encoded_email}")
        assert response.status_code == status.HTTP_200_OK
        
        # Verify participant was added with correct email
        response = client.get("/activities")
        participants = response.json()[activity]["participants"]
        assert email in participants


class TestUnregisterEndpoint:
    """Test the unregister endpoint"""
    
    def test_unregister_success(self, client, reset_activities):
        """Test successful unregistration"""
        email = "michael@mergington.edu"  # Already registered in Chess Club
        activity = "Chess Club"
        
        # Get initial participant count
        response = client.get("/activities")
        initial_count = len(response.json()[activity]["participants"])
        assert email in response.json()[activity]["participants"]
        
        # Unregister
        response = client.delete(f"/activities/{activity}/unregister?email={email}")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        assert activity in data["message"]
        
        # Verify participant was removed
        response = client.get("/activities")
        updated_activity = response.json()[activity]
        assert len(updated_activity["participants"]) == initial_count - 1
        assert email not in updated_activity["participants"]
    
    def test_unregister_nonexistent_activity(self, client, reset_activities):
        """Test unregister from non-existent activity"""
        response = client.delete("/activities/NonExistent/unregister?email=test@mergington.edu")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        data = response.json()
        assert "detail" in data
        assert "Activity not found" in data["detail"]
    
    def test_unregister_not_registered(self, client, reset_activities):
        """Test unregister when not registered"""
        email = "notregistered@mergington.edu"
        activity = "Chess Club"
        
        response = client.delete(f"/activities/{activity}/unregister?email={email}")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        data = response.json()
        assert "detail" in data
        assert "not registered" in data["detail"]
    
    def test_unregister_url_encoding(self, client, reset_activities):
        """Test unregister with URL-encoded parameters"""
        # First register a user with special characters
        email = "test.user+tag@mergington.edu"
        activity = "Programming Class"
        
        # Register first
        client.post(f"/activities/{activity}/signup?email={email}")
        
        # Now unregister with URL encoding
        encoded_activity = "Programming%20Class"
        encoded_email = "test.user%2Btag%40mergington.edu"
        
        response = client.delete(f"/activities/{encoded_activity}/unregister?email={encoded_email}")
        assert response.status_code == status.HTTP_200_OK


class TestIntegration:
    """Integration tests"""
    
    def test_full_signup_unregister_cycle(self, client, reset_activities):
        """Test complete signup and unregister cycle"""
        email = "integration@mergington.edu"
        activity = "Science Club"
        
        # Initial state
        response = client.get("/activities")
        initial_participants = response.json()[activity]["participants"].copy()
        assert email not in initial_participants
        
        # Sign up
        response = client.post(f"/activities/{activity}/signup?email={email}")
        assert response.status_code == status.HTTP_200_OK
        
        # Verify signup
        response = client.get("/activities")
        participants_after_signup = response.json()[activity]["participants"]
        assert email in participants_after_signup
        assert len(participants_after_signup) == len(initial_participants) + 1
        
        # Unregister
        response = client.delete(f"/activities/{activity}/unregister?email={email}")
        assert response.status_code == status.HTTP_200_OK
        
        # Verify unregister
        response = client.get("/activities")
        final_participants = response.json()[activity]["participants"]
        assert email not in final_participants
        assert final_participants == initial_participants
    
    def test_multiple_users_same_activity(self, client, reset_activities):
        """Test multiple users signing up for the same activity"""
        activity = "Math Olympiad"
        emails = ["user1@mergington.edu", "user2@mergington.edu", "user3@mergington.edu"]
        
        # Get initial count
        response = client.get("/activities")
        initial_count = len(response.json()[activity]["participants"])
        
        # Sign up multiple users
        for email in emails:
            response = client.post(f"/activities/{activity}/signup?email={email}")
            assert response.status_code == status.HTTP_200_OK
        
        # Verify all users are registered
        response = client.get("/activities")
        participants = response.json()[activity]["participants"]
        assert len(participants) == initial_count + len(emails)
        
        for email in emails:
            assert email in participants