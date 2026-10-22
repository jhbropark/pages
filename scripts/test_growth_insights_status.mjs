import assert from 'node:assert/strict';
import { summarizeStatuses } from './growth_insights_status.mjs';

const failedSources = summarizeStatuses({
  ig: {
    account: {
      status: 'available',
      followers_count: { status: 'unavailable', reason: 'graph_error' },
    },
    media_status: { status: 'unavailable', reason: 'permission_denied' },
  },
  facebook: {
    videos_status: { status: 'unavailable', reason: 'graph_error' },
  },
});
assert.equal(failedSources.collection_status, 'partial');
assert.equal(failedSources.metric_status_counts.unavailable, 3);

const expectedGapsOnly = summarizeStatuses({
  ig: {
    reels: [{
      insights: {
        follows: { status: 'not_supported', reason: 'not_supported_for_reels_media_insights' },
        profile_visits: { status: 'not_supported', reason: 'not_supported_for_reels_media_insights' },
      },
      audience_views_breakdown: {
        views: { status: 'not_supported', reason: 'not_supported_for_media_insights_breakdown' },
      },
    }],
  },
});
assert.equal(expectedGapsOnly.collection_status, 'complete');
assert.equal(expectedGapsOnly.support_coverage, 'limited');
assert.equal(expectedGapsOnly.metric_status_counts.not_supported, 3);
console.log('growth insight status regression tests passed');
