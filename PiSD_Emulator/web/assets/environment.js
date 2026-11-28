const el=id=>document.getElementById(id);
let profiles=[], running=false, busy=false;
function render(data){
 const previous=el("saved").value;
 profiles=data.profiles; running=data.running;
 el("saved").replaceChildren(...profiles.map(p=>{const o=document.createElement("option");o.value=p.name;o.textContent=p.name;return o;}));
 if(profiles.some(p=>p.name===previous))el("saved").value=previous;
 el("active").textContent=(data.active?.name || "Default/built-in track")+(running?" · PiSD running":" · PiSD stopped");
 el("apply").disabled=running||!profiles.length;el("default").disabled=running;el("load").disabled=!profiles.length;
}
async function action(path,body){
 if(busy)return;busy=true;
 try{const response=await fetch(path,body===undefined?{}:{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
 const data=await response.json();if(!response.ok)throw Error(data.error||"Request failed");render(data);el("message").textContent="Confirmed."; }
 catch(error){el("message").textContent=error.message;}finally{busy=false;}
}
el("refresh").onclick=()=>action("/api/environments");
el("load").onclick=()=>{const p=profiles.find(p=>p.name===el("saved").value);if(!p)return;el("name").value=p.name;el("width").value=p.road_width_m;el("segments").value=JSON.stringify(p.segments,null,2);el("obstacles").value=JSON.stringify(p.obstacles,null,2);el("markings").value=p.markings;el("edges").checked=p.edge_lines;el("lighting").value=p.lighting;};
el("save").onclick=()=>{try{const profile={name:el("name").value,road_width_m:Number(el("width").value),segments:JSON.parse(el("segments").value),obstacles:JSON.parse(el("obstacles").value),markings:el("markings").value,edge_lines:el("edges").checked,lighting:el("lighting").value};const exists=profiles.some(p=>p.name===profile.name);if(exists&&!window.confirm("Replace saved profile?"))return;action("/api/environments/save",{profile,replace:exists});}catch(error){el("message").textContent=error.message;}};
el("apply").onclick=()=>action("/api/environments/select",{name:el("saved").value});
el("default").onclick=()=>action("/api/environments/select",{name:null});
action("/api/environments");
