// Use relative URLs when the frontend is served by the backend
export const API_BASE_URL = '';
export const WS_BASE_URL = window.location.protocol === 'https:' 
    ? `wss://${window.location.host}` 
    : `ws://${window.location.host}`;

export const config = {
    API_BASE_URL,
    WS_BASE_URL,
} as const;

export default config; 