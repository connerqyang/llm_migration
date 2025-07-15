# LLM Migration Tool API

FastAPI backend for the LLM Migration Tool dashboard that provides REST endpoints for triggering component migrations, tracking progress, and viewing analytics.

## Features

- **Migration Management**: Trigger and track TUX component migrations
- **Real-time Monitoring**: Track validation steps and error resolution
- **Analytics Dashboard**: Success rates, performance metrics, and error analytics
- **Database Integration**: PostgreSQL with comprehensive migration tracking
- **Background Processing**: Async migration execution with detailed logging

## Quick Start

### 1. Prerequisites

- Python 3.8+
- PostgreSQL database
- Environment variables configured (see `.env.example`)

### 2. Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your database and API configuration
```

### 3. Database Setup

```bash
# Initialize database and insert sample data
python setup_db.py
```

### 4. Start the Server

```bash
# Start the API server
python start_server.py
```

The API will be available at:
- **API Server**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## API Endpoints

### Core Endpoints

- `GET /health` - Health check
- `GET /api/components` - List supported components
- `POST /api/migrate` - Trigger migration
- `GET /api/migrations` - Migration history
- `GET /api/migrations/{id}` - Migration details

### Analytics Endpoints

- `GET /api/analytics/overview` - Overall analytics
- `GET /api/analytics/trends` - Trend data for charts
- `GET /api/analytics/errors` - Error analytics

## Database Schema

The API uses PostgreSQL with the following main tables:

- **components** - Supported TUX components catalog
- **migrations** - Migration attempts and results
- **validation_steps** - Individual validation stage tracking
- **error_logs** - Detailed error information
- **migration_metrics** - Aggregated analytics data

## Testing

```bash
# Run API tests
python test_api.py
```

## Configuration

Key environment variables:

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/llm_migration

# LLM Integration
GEMINI_API_KEY=your_api_key
LOCAL_REPO_PATH=/path/to/repo

# API Settings
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=["http://localhost:3000"]
```

## Integration

This API integrates with:
- Existing LLM migration tool (`src/utils/`)
- React dashboard frontend
- PostgreSQL database for persistence
- Gemini API for code transformation

## Development

The API uses:
- **FastAPI** for REST endpoints
- **SQLAlchemy** for database ORM
- **Pydantic** for data validation
- **Asyncio** for background processing
- **CORS** middleware for frontend integration