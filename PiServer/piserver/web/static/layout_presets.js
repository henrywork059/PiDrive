/* Browser-local layout helpers; no hardware calls, DOM, or storage mutations. */
(function(root){
  "use strict";
  const presets = {
    manual: {
      name: "Driving", boxes: {
        status:{c:1,r:1,w:35,h:5}, estop:{c:36,r:1,w:10,h:5},
        viewer:{c:1,r:6,w:26,h:15}, manual:{c:27,r:6,w:19,h:15},
        runtime:{c:1,r:21,w:26,h:5}, record:{c:27,r:21,w:19,h:5}
      }
    },
    camera: {
      name:"Camera tuning", boxes:{
        status:{c:1,r:1,w:35,h:5}, estop:{c:36,r:1,w:10,h:5},
        viewer:{c:1,r:6,w:28,h:20}, camera:{c:29,r:6,w:17,h:20}
      }
    },
    auto:{
      name:"Model testing", boxes:{
        status:{c:1,r:1,w:35,h:5}, estop:{c:36,r:1,w:10,h:5},
        viewer:{c:1,r:6,w:26,h:15}, model:{c:27,r:6,w:19,h:8},
        runtime:{c:27,r:14,w:19,h:12}, record:{c:1,r:21,w:26,h:5}
      }
    }
  };
  const clone = layout => JSON.parse(JSON.stringify(layout));
  function merge(defaults, raw) {
    if (!raw) return clone(defaults);
    try { return Object.assign(clone(defaults), JSON.parse(raw)); }
    catch { return clone(defaults); }
  }
  function preset(page) {
    const selected=Object.hasOwn(presets,page)?presets[page]:null;
    return selected?clone(selected):null;
  }
  function begin(page, current) {
    const selected=preset(page);
    return selected?{page,original:clone(current),candidate:selected.boxes,name:selected.name}:null;
  }
  // Geometry helpers extracted from app.js; no DOM or storage access.
  const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
  function moveBox(box, col, row, cols, rows) {
    return {...box, c:clamp(col,1,cols-box.w+1), r:clamp(row,1,rows-box.h+1)};
  }
  function resizeBox(box, dw, dh, cols, rows) {
    return {...box, w:clamp(box.w+dw,4,cols-box.c+1), h:clamp(box.h+dh,3,rows-box.r+1)};
  }
  const api={clone,merge,preset,begin,moveBox,resizeBox};
  if (typeof module !== "undefined" && module.exports) module.exports=api;
  else root.PiServerLayout=api;
})(typeof window !== "undefined" ? window : globalThis);
