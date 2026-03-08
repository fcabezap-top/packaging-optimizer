"""
Pytest configuration for users-service tests.

In CI, MONGO_URL is set to mongodb://localhost:27017 (service container).
Locally, developers need a running MongoDB or can override MONGO_URL.
The seed and index creation run normally through the FastAPI lifespan.
"""
