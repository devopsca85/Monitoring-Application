// Shared CST time formatting — single source of truth

const CST_ZONE = 'America/Chicago';

export function formatCST(dateStr) {
  if (!dateStr) return '-';
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return '-';
  return d.toLocaleString('en-US', {
    timeZone: CST_ZONE,
    year: 'numeric', month: 'short', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
    hour12: true,
  }) + ' CST';
}

export function formatCSTShort(dateStr) {
  if (!dateStr) return '-';
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return '-';
  return d.toLocaleString('en-US', {
    timeZone: CST_ZONE,
    month: 'short', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
    hour12: true,
  }) + ' CST';
}

export function formatCSTTime(dateStr) {
  if (!dateStr) return '-';
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return '-';
  return d.toLocaleString('en-US', {
    timeZone: CST_ZONE,
    hour: '2-digit', minute: '2-digit', second: '2-digit',
    hour12: true,
  }) + ' CST';
}

export function formatCSTHour(dateStr) {
  if (!dateStr) return '-';
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return '-';
  return d.toLocaleString('en-US', {
    timeZone: CST_ZONE,
    hour: '2-digit', minute: '2-digit',
    hour12: true,
  });
}
