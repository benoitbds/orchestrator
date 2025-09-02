# Claude Context - Orchestrator Project

## Project Overview
**Orchestrator** is an agentic MVP running on Raspberry Pi that combines a Python FastAPI backend with a Next.js frontend to create an intelligent document processing and task management system.

## Architecture

### Backend (Python + FastAPI)
- **Core**: FastAPI server with SQLite database
- **Agent System**: Modular agents (planner, executor, writer, embeddings)
- **Document Processing**: PDF/TXT/DOCX support with OCR capabilities
- **AI Integration**: OpenAI LLM and embeddings for semantic search
- **Real-time**: WebSocket streaming for live updates

### Frontend (Next.js + React)
- **Modern Stack**: Next.js 15, React 19, TypeScript
- **UI Components**: Radix UI with Tailwind CSS
- **State Management**: Zustand + SWR for API calls
- **Visualizations**: D3.js for backlog diagrams
- **Testing**: Vitest + Testing Library

## Development Commands

### Backend
```bash
# Install dependencies
poetry install --with dev

# Start development server
poetry run uvicorn api.main:app --reload

# Run tests
poetry run pytest

# Linting/formatting
poetry run ruff check
poetry run ruff format

# Command line usage
poetry run python orchestrator/core_loop.py "Your objective"
```

### Frontend
```bash
cd frontend

# Install dependencies
pnpm install

# Development server
pnpm run dev

# Build
pnpm run build

# Tests
pnpm run test

# Linting
pnpm run lint
```

## Key File Locations

### Backend Structure
- `api/` - FastAPI endpoints and WebSocket handlers
- `orchestrator/` - Core business logic and agents
- `agents/` - Modular agent implementations
- `prompts/` - YAML prompt templates
- `tests/` - Comprehensive test suite

### Frontend Structure
- `src/app/` - Next.js app router pages
- `src/components/` - React components organized by feature
- `src/lib/` - Utility functions and API clients
- `src/stores/` - Zustand state management
- `src/models/` - TypeScript type definitions

## Environment Setup
Required environment variables:
- `OPENAI_API_KEY` - For LLM and embedding services

Optional:
- Tesseract OCR for image processing: `sudo apt-get install tesseract-ocr`

## Key Features to Understand

### Document Management
- Upload via API: `POST /projects/{id}/documents`
- Text chunking with tiktoken for optimal embedding
- Semantic search: `POST /projects/{id}/search`
- File size limit: ~5MB (larger files are summarized)

### Agent System
- **Planner**: Breaks down objectives into tasks
- **Executor**: Executes individual tasks with tools
- **Writer**: Generates content and responses
- **Embeddings**: Handles document vectorization

### Real-time Communication
- WebSocket endpoint for streaming agent responses
- Frontend uses custom hooks for real-time updates
- State synchronization between components

## Testing Strategy
- Backend: pytest with async support
- Frontend: Vitest with jsdom for component testing
- API testing with httpx
- Comprehensive test coverage across all modules

## Deployment
- Docker containers for both services
- Caddy reverse proxy configuration
- ARM64 optimized for Raspberry Pi deployment
- docker-compose for local development

## Code Style & Conventions
- Python: Follow PEP 8, use type hints, Pydantic models
- TypeScript: Strict mode, proper component typing
- Components: Functional components with hooks
- API: RESTful design with clear endpoint naming
- Error handling: Comprehensive error boundaries and validation

## Common Tasks
- Adding new agents: Extend base classes in `agents/`
- New API endpoints: Add to `api/main.py` with proper validation
- Frontend features: Use existing component patterns and state management
- Document processors: Extend `doc_processing.py` for new formats
- Prompts: Add YAML files to `prompts/` directory

## Performance Considerations
- Raspberry Pi optimization for ARM64
- Efficient text chunking for large documents
- Connection pooling for database operations
- Client-side caching with SWR
- Streaming responses for real-time feedback