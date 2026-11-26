const test=require("node:test");
const assert=require("node:assert/strict");
const layout=require("../piserver/web/static/layout_presets.js");
for (const [page,panels] of Object.entries({
 manual:["status","estop","viewer","runtime","manual","record"],
 camera:["status","estop","viewer","camera"],
 auto:["status","estop","viewer","runtime","model","record"]
})) {
 test(page+" preset retains panels and has no overlapping or off-grid boxes",()=>{
   const p=layout.preset(page);
   assert.deepEqual(Object.keys(p.boxes).sort(),panels.sort());
   const occupied=new Set();
   for (const {c,r,w,h} of Object.values(p.boxes)){
     assert.ok(c>=1&&r>=1&&c+w-1<=45&&r+h-1<=25);
     for(let y=r;y<r+h;y++)for(let x=c;x<c+w;x++){
       const key=x+":"+y;assert.ok(!occupied.has(key),key);occupied.add(key);
     }
   }
 });
}
test("preview copies original and preset, never changes saved input",()=>{
 const original={status:{c:3,r:2,w:7,h:6}};
 const preview=layout.begin("manual",original);
 preview.original.status.c=99;preview.candidate.status.c=99;
 assert.equal(original.status.c,3);
 assert.equal(layout.preset("manual").boxes.status.c,1);
 assert.equal(layout.begin("training",original),null);
});
test("saved layout merge preserves previous defaults and override semantics",()=>{
 const defaults={a:{c:1},b:{c:2}};
 assert.deepEqual(layout.merge(defaults,'{"a":{"c":7}}'),{a:{c:7},b:{c:2}});
 assert.deepEqual(layout.merge(defaults,'bad json'),defaults);
 assert.deepEqual(layout.merge(defaults,null),defaults);
});

test("extracted docking math preserves rounding inputs, grid bounds and original box",()=>{
 const box={c:3,r:4,w:8,h:5};
 assert.deepEqual(layout.moveBox(box,-5,100,45,25),{c:1,r:21,w:8,h:5});
 assert.deepEqual(layout.moveBox(box,100,-5,45,25),{c:38,r:1,w:8,h:5});
 assert.deepEqual(layout.resizeBox(box,-20,-20,45,25),{c:3,r:4,w:4,h:3});
 assert.deepEqual(layout.resizeBox(box,100,100,45,25),{c:3,r:4,w:43,h:22});
 assert.deepEqual(box,{c:3,r:4,w:8,h:5});
});
