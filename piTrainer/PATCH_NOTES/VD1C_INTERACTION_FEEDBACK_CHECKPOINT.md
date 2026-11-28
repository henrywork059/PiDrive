# Visual Design Update 1C — interaction feedback

Base: 11a01ea35deb54486fc8e60e1a9b00d07d33682d. Prior four applicable workflows passed (46045121027, 46045121057, 46045121112, 46045121039). Owner requested another update while stability main CI executes. VD14 partial only.

Secondary-role buttons now explicitly retain distinct hovered and pressed fills rather than a more specific resting rule overriding generic feedback. Native Qt test checks actual pressed/disabled center pixel fills, unchanged size and no click.

Preserve prior VD1A/VD1B, 1.0.0 and historical notes, existing safety, settings, data, layouts and pinned screenshots. No version allocation, merge, deployment or stable promotion. Source anchors and targeted diff reviewed; candidate rendered tests and CI not yet run. No full requirement acceptance claimed.
