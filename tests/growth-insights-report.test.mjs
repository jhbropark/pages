import test from "node:test";
import assert from "node:assert/strict";
import { finalizeObservation, unavailable } from "../namecode_grid/growth_insights_report.mjs";

test("marks a report partial when a requested metric is unavailable", () => {
  const report = finalizeObservation({
    ig: { reels: [{ insights: { reach: { status: "available", data: [{ name: "reach" }] },
                                follows: unavailable("unsupported_metric") } }] },
    facebook: { videos: [{ insights: { read_insights: unavailable("graph_error", { http_status: 403 }) } }] },
  });
  assert.equal(report.result_status, "partial");
  assert.deepEqual(report.partial_failures.map(x => x.path), [
    "ig.reels[0].insights.follows",
    "facebook.videos[0].insights.read_insights",
  ]);
  assert.equal(report.partial_failures[1].http_status, 403);
});

test("marks a complete report when all requested reads are available", () => {
  const report = finalizeObservation({
    ig: { account: { status: "available", username: "namecode_original" } },
    facebook: { videos: [] },
  });
  assert.equal(report.result_status, "complete");
  assert.deepEqual(report.partial_failures, []);
});
