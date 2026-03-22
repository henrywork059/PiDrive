# PiServer 0_3_12 patch

Changes in this patch:
- rebuilt from the correct 0_3_10 UI base so the 0_3_9 and 0_3_10 layout fixes stay intact
- replaced the top Status card for Record with Last save
- kept Last save inside the same responsive status-card row/grid as the other boxes
- removed the redundant Path card from the Record panel
- kept Session, Elapsed, and Last save together in one row/grid in the Record panel
- shortened the top Last save text to the saved filename while keeping the full value in the hover title
- switched the UI away from the older neon-blue palette to a more restrained charcoal / taupe / clay / sage palette
- bumped app version to 0_3_12 so the browser reloads the updated assets

Changed files:
- PiServer/piserver/web/templates/index.html
- PiServer/piserver/web/static/app.js
- PiServer/piserver/web/static/styles.css
- PiServer/piserver/app.py

Notes:
- This patch intentionally does not touch the 0_3_10 drag-pad and status-grid fixes except to build on top of them.
