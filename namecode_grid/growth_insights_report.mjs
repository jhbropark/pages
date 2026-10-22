export function unavailable(reason, details = {}) {
  return { status: "unavailable", reason, ...details };
}

export function finalizeObservation(report) {
  const failures = [];
  const visit = (value, path) => {
    if (Array.isArray(value)) {
      value.forEach((entry, index) => visit(entry, path ? `${path}[${index}]` : String(index)));
      return;
    }
    if (!value || typeof value !== "object") return;
    if (value.status === "unavailable") {
      failures.push({ path, reason: value.reason || "unavailable", http_status: value.http_status });
      return;
    }
    for (const [key, child] of Object.entries(value)) {
      if (key === "status" || key === "partial_failures") continue;
      visit(child, path ? `${path}.${key}` : key);
    }
  };
  visit({ ig: report.ig, facebook: report.facebook }, "");
  report.partial_failures = failures;
  report.result_status = failures.length ? "partial" : "complete";
  return report;
}
