/**
 * Format a date string using the server's timezone
 * @param dateString - ISO date string from the server
 * @returns Formatted date string in the server's timezone
 */
export function formatDate(dateString: string): string {
  // The server uses Europe/Vienna timezone
  const options: Intl.DateTimeFormatOptions = {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
    timeZone: 'Europe/Vienna',
    timeZoneName: undefined  // Don't show timezone name
  };

  // Parse the date string and ensure it's treated as UTC
  const date = new Date(dateString + 'Z');
  return date.toLocaleString('de-DE', options);
}

export function formatDuration(startDate: string, endDate?: string | null): string {
  const start = new Date(startDate).getTime();
  const end = endDate ? new Date(endDate).getTime() : Date.now();
  
  const durationMs = end - start;
  const seconds = Math.floor(durationMs / 1000);
  
  if (seconds < 60) {
    return `${seconds} seconds`;
  }
  
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  
  if (minutes < 60) {
    return `${minutes}m ${remainingSeconds}s`;
  }
  
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  
  return `${hours}h ${remainingMinutes}m ${remainingSeconds}s`;
} 