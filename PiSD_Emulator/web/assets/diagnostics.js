const el=id=>document.getElementById(id);
let busy=false;
function chart(id,values){
 const c=el(id),ctx=c.getContext("2d"),w=c.width,h=c.height;
 ctx.clearRect(0,0,w,h);ctx.fillStyle="#151b24";ctx.fillRect(0,0,w,h);
 const finite=values.filter(Number.isFinite),lo=Math.min(0,...finite),hi=Math.max(lo+0.001,...finite);
 const x=i=>60+i*(w-80)/Math.max(1,values.length-1), y=v=>h-25-(v-lo)/(hi-lo)*(h-45);
 ctx.font="14px sans-serif";ctx.strokeStyle="#596577";ctx.fillStyle="#d9e4ef";
 for(let i=0;i<=4;i++){const v=lo+(hi-lo)*i/4;ctx.beginPath();ctx.moveTo(58,y(v));ctx.lineTo(w-12,y(v));ctx.stroke();ctx.fillText(v.toFixed(2),3,y(v)+5);}
 ctx.strokeStyle="#57ffed";ctx.lineWidth=2;ctx.beginPath();let open=false;
 values.forEach((v,i)=>{if(!Number.isFinite(v)){open=false;return;}if(open)ctx.lineTo(x(i),y(v));else{ctx.moveTo(x(i),y(v));open=true;}});ctx.stroke();ctx.lineWidth=1;
 if(!finite.length)ctx.fillText("No samples yet",80,40);
 else {ctx.fillText("Latest: "+finite.at(-1).toFixed(2),80,16);ctx.fillText("Oldest → newest",w-150,h-5);}
}
async function refresh(){
 if(busy)return;busy=true;
 try{const r=await fetch("/api/diagnostics",{cache:"no-store"});if(!r.ok)throw Error("Diagnostics unavailable");const data=await r.json();
 el("summary").textContent=data.request_total+" API requests · "+data.requests.length+" retained · "+data.samples.length+" samples";
 chart("fps",data.samples.map(s=>s.physics_fps));chart("speed",data.samples.map(s=>s.speed_mps));chart("latency",data.requests.slice(-180).map(r=>r.handler_ms));
 el("requests").replaceChildren(...data.requests.slice().reverse().map(r=>{const tr=document.createElement("tr");[r.generation,r.method,r.route,r.status,r.handler_ms??"—"].forEach(v=>{const td=document.createElement("td");td.textContent=String(v);tr.append(td);});return tr;}));
 el("events").textContent=data.events.map(e=>e.timestamp+" "+e.level).join("\n");
 }catch(error){el("summary").textContent=error.message;}finally{busy=false;}
}
el("refresh").onclick=refresh;
el("live").onchange=()=>{if(el("live").checked)refresh();};
setInterval(()=>{if(el("live").checked&&!document.hidden)refresh();},1000);
refresh();
