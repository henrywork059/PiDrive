# Visual Design Update 1E — narrow target repair

Base: 1022d3c924e3b3aada7a437d24aae38cac3dbc00.

VD1D exact 1022d3c924e3b3aada7a437d24aae38cac3dbc00: regression 46106062134 failed PiSD job 140858954823 (Reset height 28.515625 <44); other 3 jobs passed. Native Windows 46106062125, trainer visuals 46106062103, emulator 46106062097 passed. Downloaded actual artifacts 15247463564, 15247372269, 15247658056, 15247626803; all archive SHA-256 matched and CRC passed. PiSD light font faces loaded before abort, no VD1D theme captures. PiServer both themes loaded both local fonts; 22/22 theme screenshot hashes matched; all 6 measured targets >=44px, but Save y=825 and bottom=869 at 844 viewport in both themes, not fully reachable. Native Linux and Windows registered Inter Variable / Inter Variable Text and IBM Plex Mono with expected sizes; all 96 native capture hashes matched. Linux requested geometry 48/48, Windows 0/48; representative captures show clipping of lower Data controls at narrow width, not full workspace acceptance.

Request and fix: Parent artifact target geometry reports Save extends 25px beyond narrow viewport. Scoped <=600px curated dialog uses fixed-parent inset, independent flexible scrolling body and equal-width footer actions, preventing footer clipping without changing workspace dock or E-stop.

Files: shared component stylesheet; tools/check_vd1a_web.py adds viewport x/y and trial-click hit checks while preserving original >=44px and persistence assertions, plus narrow captures. Source and prior four visual notes inspected; new rendered CI pending. Existing versions, fonts, safety, configuration, approved screenshots and history preserved. No merge or stable promotion. Broader redesign waits for repair qualification.
