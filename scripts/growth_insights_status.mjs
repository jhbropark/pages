export function collectStatuses(value, out = []) {
  if (value && typeof value === 'object') {
    if (['available', 'unavailable', 'not_supported'].includes(value.status)) out.push(value.status);
    for (const [key, child] of Object.entries(value)) {
      if (key !== 'status') collectStatuses(child, out);
    }
  }
  return out;
}

export function summarizeStatuses(value) {
  const statuses = collectStatuses(value);
  const counts = Object.fromEntries(
    ['available', 'unavailable', 'not_supported'].map(status =>
      [status, statuses.filter(item => item === status).length]));
  return {
    collection_status: counts.unavailable > 0 ? 'partial' : 'complete',
    support_coverage: counts.not_supported > 0 ? 'limited' : 'full',
    metric_status_counts: counts,
  };
}
