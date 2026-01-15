#!/bin/bash
# Trigger Droid reviews on all droid-sentry PRs (#6-15)
# Usage: ./scripts/trigger_sentry_reviews.sh

echo "Triggering Droid reviews for droid-sentry PRs #6-15..."

for pr in 6 7 8 9 10 11 12 13 14 15; do
  gh pr comment $pr --repo droid-code-review-evals/droid-sentry --body "@droid review"
  echo "Triggered review on PR #$pr"
  sleep 2
done

echo ""
echo "All reviews triggered. Monitor progress with:"
echo "  gh run list --repo droid-code-review-evals/droid-sentry --limit 20"
