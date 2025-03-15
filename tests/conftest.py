import os
import pytest
import tempfile
from app.db import Database


@pytest.fixture
def test_db():
    """Create a temporary database for testing."""
    # Create a temporary file for the test database
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    temp_file.close()
    
    # Create the database
    db = Database(temp_file.name)
    
    yield db
    
    # Clean up
    os.unlink(temp_file.name)