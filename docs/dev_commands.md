Start Backend

uvicorn backend.main:app --reload --reload-exclude="scripts/**/*" --reload-exclude="scripts/*"

Start Frontend

npm run dev