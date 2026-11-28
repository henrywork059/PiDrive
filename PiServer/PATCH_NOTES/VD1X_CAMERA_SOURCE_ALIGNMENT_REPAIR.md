# VD1X — camera source alignment repair

Exact parent 7080c5b9d1e7f2c9f0c562269451c64e3d43243c; failure in 46144600448 job 140977756758, expected portrait image 329.25x439 but overlay still 780.4375x439. Source timing hypothesis; observe src/srcset only in active cockpit, invalidate stale geometry, align current decode/load, guard late completion and disconnect on exit. Keep original 2px regression bound and bounded callback settling. No camera service, settings, safety or saved dock changes. Exact CI pending; no version change.
