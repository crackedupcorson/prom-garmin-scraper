# Fatigue Checker — Roadmap & Tasks

This file lists small, actionable tasks to implement the conservative, rule-based fatigue mismatch detector described in `.github/prompts/fatigue-checker.md`.

IMPORTANT: Items 3, 6, and 7 form one conceptual unit (IF bands → baseline stats → ride vs baseline).
These three tasks must remain "pure data" steps: implement only data extraction, binning, and numeric aggregation.
Do NOT add any interpretation or classification logic into steps 3–6. Keep baseline computation dumb and deterministic.

- [x] 1. Create fatigue module skeleton
- [x] 2. Implement history gating checks
- [x] 3. Implement IF band definitions (pure data only)
- [x] 4. Implement easy-ride detector
 - [x] 5. Compute per-ride strain metrics
 - [x] 6. Build baseline statistics per IF band (pure aggregation)
 - [x] 7. Compare rides to band baselines (pure comparison)
- [x] 8. Aggregate 7-day classifications
- [x] 9. Implement rolling window gating
- [x] 10. Training-load context checks
- [ ] 11. Expose Prometheus metrics
- [ ] 12. Add text summary endpoint
- [ ] 13. Write unit tests for rules
- [ ] 14. Document feature in README
- [ ] 15. Make thresholds configurable
- [ ] 16. Integrate with intervals pipeline
- [ ] 17. Add sample dataset fixtures
- [ ] 18. Code review and comments

How to use:
- Check a box when the task is complete (commit the change).
- I will also keep the internal tracker in sync when you ask me to mark items complete.

If you'd like, I can start work on item 1 now.