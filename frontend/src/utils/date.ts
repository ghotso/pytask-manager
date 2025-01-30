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