# VRSEN Lead Generation Frontend

A modern React frontend for the VRSEN lead generation system. This web interface provides a complete dashboard for managing lead generation campaigns, real-time progress tracking, and lead management.

## Features

- **Modern UI**: Built with React 19, TypeScript, and Tailwind CSS
- **Real-time Updates**: Live campaign progress tracking with WebSockets
- **Campaign Management**: Create, monitor, and manage lead generation campaigns
- **Lead Management**: View, filter, edit, and export generated leads
- **Responsive Design**: Works seamlessly on desktop and mobile devices
- **Dark Mode**: Full dark/light theme support
- **Type Safety**: Complete TypeScript implementation with strict typing

## Tech Stack

- **Frontend Framework**: React 19 with TypeScript
- **Styling**: Tailwind CSS with custom design system
- **State Management**: Zustand for client-side state
- **API Client**: TanStack Query for server state management
- **HTTP Client**: Axios with interceptors and error handling
- **Routing**: React Router DOM v6
- **Forms**: React Hook Form with validation
- **Build Tool**: Vite for fast development and optimized builds

## Getting Started

### Prerequisites

- Node.js 18+ 
- npm or yarn
- Backend API server running

### Installation

1. **Install dependencies**:
   ```bash
   npm install
   ```

2. **Set up environment variables**:
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and configure your API endpoints:
   ```env
   VITE_API_BASE_URL=http://localhost:8000/api
   VITE_WS_URL=ws://localhost:8000/ws
   ```

3. **Start the development server**:
   ```bash
   npm run dev
   ```

4. **Open your browser**:
   Visit `http://localhost:5173` to access the application

### Building for Production

```bash
# Build the application
npm run build

# Preview the production build
npm run preview
```

## Key Features

### Campaign Management
- Create new lead generation campaigns with detailed settings
- Configure search queries, business types, and targeting options
- Set advanced parameters like rate limiting and quality thresholds
- Monitor campaign progress in real-time

### Real-time Progress Tracking
- Live updates on campaign execution steps
- Progress bars for each phase (searching, parsing, extracting, validating)
- Real-time statistics on leads found and processed
- WebSocket integration for instant updates

### Lead Management
- View all generated leads in a searchable, filterable table
- Edit lead information and add notes
- Bulk operations for selecting and exporting leads
- Lead quality scoring and confidence indicators

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_BASE_URL` | Backend API base URL | `http://localhost:8000/api` |
| `VITE_WS_URL` | WebSocket connection URL | `ws://localhost:8000/ws` |
| `VITE_APP_ENV` | Application environment | `development` |

## License

MIT License - see the main project LICENSE file for details.
