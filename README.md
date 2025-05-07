# Ad Creative Generator

A powerful tool for generating creative advertisements using AI.

## Features

### Browse Inspiration
- Browse inspirational images by category
- Select reference images for your ad creation

### Create Ad
- Generate images with text prompts
- Use reference images for style transfer
- Add custom text to your advertisements

## Getting Started

### Backend Setup
1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
2. Create a `.env` file with your API keys:
   ```
   OPENAI_API_KEY=your_openai_api_key
   OPENAI_ORG_ID=your_openai_org_id
   SHUTTERSTOCK_API_KEY=your_shutterstock_api_key
   ```
3. Run the backend:
   ```
   uvicorn app.main:app --reload
   ```

### Frontend Setup
1. Navigate to the frontend directory:
   ```
   cd frontend
   ```
2. Install dependencies:
   ```
   npm install
   ```
3. Run the frontend:
   ```
   npm run dev
   ```

## Technologies Used
- Backend: FastAPI, Python
- Frontend: Next.js, React, TypeScript
- APIs: OpenAI, Shutterstock
