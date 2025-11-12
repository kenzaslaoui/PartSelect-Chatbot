# PartSelect AI Chat Frontend

A React-based chat interface for interacting with the PartSelect AI assistant.

## Features

- Real-time chat interface with AI assistant
- Display of related resources (blogs, repairs, parts)
- Responsive design for mobile and desktop
- TypeScript for type safety
- Vite for fast development and builds

## Getting Started

### Prerequisites

- Node.js (v16 or higher)
- npm or yarn

### Installation

```bash
npm install
```

### Development

Start the development server:

```bash
npm run dev
```

The app will be available at `http://localhost:3000`

The development server is configured to proxy API requests to `http://localhost:8000`

### Build

Build for production:

```bash
npm run build
```

### Preview

Preview the production build:

```bash
npm run preview
```

## API Configuration

The frontend is configured to make requests to the backend API at:
- Development: `http://localhost:8000/api/v1/chat` (proxied through Vite)
- Production: Configure your production API endpoint in the environment variables

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── ChatInterface.tsx      # Main chat component
│   │   ├── ChatInterface.css
│   │   ├── MessageBubble.tsx      # Individual message display
│   │   ├── MessageBubble.css
│   │   ├── ResourceList.tsx       # Display related resources
│   │   └── ResourceList.css
│   ├── types.ts                   # TypeScript type definitions
│   ├── App.tsx
│   ├── App.css
│   ├── main.tsx
│   └── index.css
├── index.html
├── package.json
├── tsconfig.json
└── vite.config.ts
```

## Technology Stack

- React 18
- TypeScript
- Vite
- CSS3 with modern features
