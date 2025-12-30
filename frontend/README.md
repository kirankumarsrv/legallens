# Lawyer Agent AI - React Frontend

## Overview
This is a full-featured React frontend for the Lawyer Agent AI workflow. It provides an interactive UI for managing legal cases with facts, arguments, predictions, and version history.

## Features

✅ **Case Management** - Create, list, and manage legal cases
✅ **Facts Editor** - Add, edit, approve, reject, and lock facts with evidence tracking
✅ **Arguments Editor** - Create arguments linked to supporting facts, with approval workflow
✅ **Prediction Viewer** - View AI predictions with confidence scores and history
✅ **Prediction Restore** - Restore previous predictions from history
✅ **Progress Tracking** - Visual progress bar showing case completion status
✅ **Responsive UI** - Modern, professional interface with Tailwind-inspired styling
✅ **REST API Integration** - Full integration with FastAPI backend

## Project Structure

```
frontend/
├── public/
│   └── index.html
├── src/
│   ├── components/
│   │   ├── CaseList.tsx           # Case listing and selection
│   │   ├── FactEditor.tsx         # Facts management UI
│   │   ├── ArgumentEditor.tsx     # Arguments management UI
│   │   ├── PredictionViewer.tsx   # Prediction display and history
│   │   └── *.css                  # Component styles
│   ├── pages/
│   │   ├── HomePage.tsx           # Home page with case list
│   │   ├── CaseWorkflow.tsx       # Main case workflow page
│   │   └── *.css                  # Page styles
│   ├── services/
│   │   └── api.ts                 # Axios-based REST API service
│   ├── App.tsx                    # Main app with routing
│   ├── main.tsx                   # Entry point
│   ├── index.css                  # Global styles
│   └── App.css                    # App layout styles
├── package.json                   # Dependencies
├── tsconfig.json                  # TypeScript config
├── vite.config.ts                # Vite configuration
└── README.md                      # This file
```

## Prerequisites

- Node.js 16+ and npm/yarn
- Backend API running on http://localhost:8000
- FastAPI backend with all endpoints available

## Installation

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Set API URL (optional):**
   ```bash
   export REACT_APP_API_URL=http://localhost:8000
   ```
   (Default is `http://localhost:8000`)

## Running the Application

### Development Server
```bash
npm run dev
```
This starts the Vite dev server on http://localhost:3000

### Build for Production
```bash
npm run build
```
This creates optimized production build in `dist/` directory

### Preview Production Build
```bash
npm run preview
```

## API Integration

The frontend communicates with the FastAPI backend via axios. The API service layer is in `src/services/api.ts` and provides the following main endpoints:

### Cases
- `GET /cases` - List all cases
- `POST /cases` - Create new case
- `GET /cases/{caseId}` - Get case details
- `DELETE /cases/{caseId}` - Delete case

### Facts
- `GET /cases/{caseId}/facts` - List facts
- `POST /cases/{caseId}/facts` - Add fact
- `PUT /cases/{caseId}/facts/{factId}` - Update fact
- `POST /cases/{caseId}/facts/{factId}/approve` - Approve fact
- `POST /cases/{caseId}/facts/{factId}/reject` - Reject fact
- `POST /cases/{caseId}/facts/{factId}/lock` - Lock fact

### Arguments
- `GET /cases/{caseId}/arguments` - List arguments
- `POST /cases/{caseId}/arguments` - Add argument
- `PUT /cases/{caseId}/arguments/{argId}` - Update argument
- `POST /cases/{caseId}/arguments/{argId}/approve` - Approve argument
- `POST /cases/{caseId}/arguments/{argId}/reject` - Reject argument
- `POST /cases/{caseId}/arguments/{argId}/lock` - Lock argument

### Predictions
- `GET /cases/{caseId}/predictions` - Get prediction history
- `POST /cases/{caseId}/predictions/restore/{index}` - Restore previous prediction

### State
- `GET /cases/{caseId}/state` - Get state flags
- `POST /cases/{caseId}/state/{flagKey}` - Set state flag
- `DELETE /cases/{caseId}/state/{flagKey}` - Clear state flag

## UI Workflow

1. **Home Page** - View all cases and create new ones
2. **Case Workflow** - Main page with three tabs:
   - **Facts Tab**: Add facts, edit, approve, lock
   - **Arguments Tab**: Create arguments linked to facts, approve, lock
   - **Predictions Tab**: View predictions and restore from history
3. **Progress Bar** - Shows case completion status (facts 30%, arguments 30%, predictions 40%)

## Technologies

- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool
- **React Router** - Client-side routing
- **Axios** - HTTP client
- **CSS3** - Styling with custom properties and grid/flexbox

## Styling

The app uses a custom CSS design system with color variables:
- Primary: `#2c3e50` (Dark blue)
- Secondary: `#3498db` (Light blue)
- Success: `#27ae60` (Green)
- Danger: `#e74c3c` (Red)
- Warning: `#f39c12` (Orange)

## Troubleshooting

### API Connection Failed
- Ensure backend is running on `http://localhost:8000`
- Check CORS settings in FastAPI backend
- Verify `REACT_APP_API_URL` environment variable

### Build Fails
- Delete `node_modules/` and `package-lock.json`
- Run `npm install` again
- Clear Vite cache with `rm -rf node_modules/.vite`

### TypeScript Errors
- Run `npm run build` to check for all errors
- Ensure TypeScript version is up to date: `npm install typescript@latest`

## Development

### Adding New Components
1. Create component in `src/components/ComponentName.tsx`
2. Add styles in `src/components/ComponentName.css`
3. Import and use in pages/other components

### Adding New Pages
1. Create page in `src/pages/PageName.tsx`
2. Add route in `src/App.tsx`
3. Link from navigation or components

### API Service Expansion
Extend `src/services/api.ts` with new endpoints following the existing pattern

## Deployment

### Docker
```dockerfile
FROM node:18-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### Environment Variables
- `REACT_APP_API_URL` - Backend API URL (default: http://localhost:8000)

## Performance Optimization

- Code splitting via React Router
- Lazy loading components
- Memoization where needed
- Optimized CSS with custom properties

## Future Enhancements

- [ ] Add user authentication
- [ ] Export case reports as PDF
- [ ] Multi-language support
- [ ] Advanced search and filtering
- [ ] Dark mode toggle
- [ ] Real-time updates via WebSocket
- [ ] Case template library
- [ ] Integration with document management

## License

MIT

## Support

For issues or questions, refer to the main project documentation or create an issue in the repository.
