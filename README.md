# FastAPI Gift Recommendation AI

A FastAPI application that provides gift recommendations using Pydantic AI with OpenRouter integration and Supabase for chat history.

## Features

- Gift recommendation AI powered by Pydantic AI and OpenRouter
- Chat history persistence with Supabase
- Quick reply suggestions (chips)
- CORS enabled for cross-origin requests
- Health check endpoint

## Prerequisites

- Python 3.8+
- Supabase account and credentials
- OpenRouter API key

## Getting Started

Install the required dependencies:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Environment Variables

Create a `.env` file with the following variables:

```env
OPENROUTER_API_KEY=your_key_here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

## Running Locally

Start the development server on http://0.0.0.0:8000

```bash
python main.py
```

The API documentation will be available at http://localhost:8000/docs

## API Endpoints

- `GET /health` - Health check endpoint
- `POST /chat` - Chat endpoint for gift recommendations
  - Request body: `{"message": "string", "session_id": "string"}`
  - Response: `{"reply": "string", "chips": ["string", "string", "string"]}`

## Deploying to Vercel

### Prerequisites for Vercel Deployment

1. Set up environment variables in Vercel dashboard:
   - `OPENROUTER_API_KEY` - Your OpenRouter API key
   - `OPENROUTER_BASE_URL` - https://openrouter.ai/api/v1
   - `SUPABASE_URL` - Your Supabase project URL
   - `SUPABASE_KEY` - Your Supabase anonymous key

### Deploy with Vercel CLI

```bash
npm install -g vercel
vercel --prod
```

### Deploy with Git

Push to your repository with our [git integration](https://vercel.com/docs/deployments/git).

The FastAPI application will be deployed as serverless functions under `/api` endpoints.

### API Endpoints on Vercel

- `GET /api/health` - Health check endpoint
- `POST /api/chat` - Chat endpoint for gift recommendations

