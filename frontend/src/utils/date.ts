/**
 * Format a date string using the server's timezone
 * @param dateString - ISO date string from the server
 * @returns Formatted date string in the server's timezone
 */
export function formatDate(dateString: string): string {
  // The server uses Europe/Berlin timezone
  const options: Intl.DateTimeFormatOptions = {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    timeZone: 'Europe/Berlin',
  };

  return new Date(dateString).toLocaleString('de-DE', options);
} 