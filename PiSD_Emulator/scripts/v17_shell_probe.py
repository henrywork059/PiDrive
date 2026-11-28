"""V17 M01: real virtual-runtime/browser shell regression, no motor enable."""
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import expect


def capture_v17_shell(browser, runtime, origin, output, revision):
    output = Path(output)
    report = {"revision": revision, "hardware_enabled": False, "cases": []}
    assert runtime.status()["hardware_enabled"] is False

    def neutral():
        motor = runtime.status()["engine"]["motor"]
        assert abs(motor["left_intended"]) < .001 and abs(motor["right_intended"]) < .001, motor

    def alignment(page, selector):
        return page.locator(selector).evaluate("""f => {
          const i=f.querySelector('img'),o=f.querySelector('.mdrv-drive-overlay');
          const r=e=>{const b=e.getBoundingClientRect();return [b.x,b.y,b.width,b.height]};
          return {image:r(i),overlay:r(o),natural:[i.naturalWidth,i.naturalHeight],
                  fit:getComputedStyle(i).objectFit,viewport:[innerWidth,innerHeight]};
        }""")

    for width, height in ((1440,900),(390,844)):
        context = browser.new_context(viewport={"width":width,"height":height})
        try:
            page = context.new_page()
            page.bring_to_front()
            errors = []
            requests = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            def observe(request):
                parsed = urlsplit(request.url)
                if parsed.path.startswith("/api/") or parsed.path == "/video_feed":
                    requests.append((request.method, parsed.path, request.post_data))
            page.on("request", observe)
            classic_ids = {}
            for mode, route in (("manual","/manual-drive"),("ai","/ai-mode")):
                page.goto(origin+route,wait_until="domcontentloaded")
                classic_ids[mode] = page.locator("[id]").evaluate_all("(els)=>els.map(e=>e.id)")
                assert page.locator("body").get_attribute("data-pisd-v17") is None
            for mode, frame, arm, live, stop in (
                ("manual","#mdrvPreviewFrame","#mdrvArm","#mdrvLiveCamera","#mdrvStopTop"),
                ("ai","#aiPreviewFrame","#aiEnableMotor","#aiLive","#aiStopAll"),
            ):
                case = {"mode":mode,"viewport":[width,height]}
                report["cases"].append(case)
                try:
                    if mode == "manual":
                        page.goto(origin+"/drive?mode=manual",wait_until="domcontentloaded")
                    else:
                        page.get_by_role("navigation",name="Driving cockpit mode").get_by_role("link",name="AI",exact=True).click()
                    expect(page.locator("body")).to_have_attribute("data-pisd-v17-ready","true")
                    expect(page.locator("body")).to_have_attribute("data-pisd-v17",mode)
                    expect(page.locator("#v17ModeNav [aria-current=page]")).to_have_text("Manual" if mode=="manual" else "AI")
                    expect(page.locator(arm)).not_to_be_checked()
                    ids = page.locator("[id]").evaluate_all("(els)=>els.map(e=>e.id)")
                    assert sorted(i for i in ids if i!="v17ModeNav")==sorted(classic_ids[mode]), "legacy DOM IDs changed"
                    assert page.locator("#mdrvPreviewFrame,#aiPreviewFrame").count()==1
                    scripts=page.locator("script[src]").evaluate_all("(els)=>els.map(e=>new URL(e.src).pathname)")
                    assert sum(s.endswith("/manual_drive.js") or s.endswith("/ai_mode.js") for s in scripts)==1, scripts
                    assert sum(s.endswith("/global_space_stop.js") for s in scripts)==1, scripts
                    neutral()
                    offset=len(requests)
                    page.locator(live).click()
                    expect(page.locator(frame)).to_have_attribute("data-preview-mode","live",timeout=15000)
                    page.wait_for_function("""s => { const i=document.querySelector(s+' img');return i&&new URL(i.currentSrc||i.src,location.href).pathname==='/video_feed'&&i.naturalWidth>0; }""",arg=frame,timeout=15000)
                    for theme in ("dark","light","legacy"):
                        # Existing presentation application, no persisted setting change.
                        page.evaluate("""theme => { const p=window.PiSDPanelPresentation; p.apply({...p.read(),theme}); window.scrollTo(0,0); }""",theme)
                        page.wait_for_function("""s=>{const f=document.querySelector(s),i=f.querySelector('img'),o=f.querySelector('.mdrv-drive-overlay'),a=i.getBoundingClientRect(),b=o.getBoundingClientRect();return scrollY===0&&a.height>0&&['x','y','width','height'].every(k=>Math.abs(a[k]-b[k])<=2)&&getComputedStyle(i).objectFit==='contain';}""",arg=frame,timeout=10000)
                        geom=alignment(page,frame)
                        assert abs(geom["image"][2]/geom["image"][3]-geom["natural"][0]/geom["natural"][1])<.03,geom
                        assert geom["image"][1]<height and geom["image"][1]+geom["image"][3]<=height+2,geom
                        stop_box=page.locator(stop).bounding_box()
                        assert stop_box and stop_box["height"]>=44 and stop_box["y"]>=0 and stop_box["y"]+stop_box["height"]<=height,stop_box
                        case.setdefault("themes",{})[theme]={"geometry":geom,"stop":stop_box}
                        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth+1")
                        path=output/f"v17-m01-{mode}-{width}-{theme}.png"
                        page.screenshot(path=str(path))
                        case["themes"][theme]["file"]=path.name
                        case["themes"][theme]["sha256"]=hashlib.sha256(path.read_bytes()).hexdigest()
                    page.wait_for_timeout(2000)
                    quiet=len(requests)
                    page.wait_for_timeout(6000)
                    quiet_events=requests[quiet:]
                    allowed={"/api/status","/api/camera/fps-stats"} if mode=="manual" else {"/api/ai/status"}
                    assert all(method=="GET" and path in allowed for method,path,_ in quiet_events),quiet_events
                    case["quiet_requests"]=[path for _,path,_ in quiet_events]
                    case["stream_requests"]=sum(method=="GET" and path=="/video_feed" for method,path,_ in requests[offset:])
                    assert case["stream_requests"]==1,case
                    neutral()
                    expect(page.locator(arm)).not_to_be_checked()
                    assert not errors,errors
                except Exception as exc:
                    case["failure"]=str(exc)
                    raise
                finally:
                    (output/"v17-m01-shell.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
            # The existing AI pagehide emits neutral correction and STOP.
            # No new authority/config write, camera start or nonzero manual
            # request may be caused by the mode link itself.
            offset=len(requests)
            page.get_by_role("navigation",name="Driving cockpit mode").get_by_role("link",name="Manual",exact=True).click()
            expect(page.locator("body")).to_have_attribute("data-pisd-v17","manual")
            page.wait_for_timeout(1500)
            for method,path,body in requests[offset:]:
                if method=="POST":
                    assert path in ("/api/control/stop","/api/ai/stop","/api/ai/manual-correction"),(path,body)
                    if path=="/api/ai/manual-correction":
                        payload=json.loads(body or "{}")
                        assert payload.get("steering")==0 and payload.get("throttle")==0,payload
            neutral()
            page.get_by_role("link",name="Classic layout").click()
            expect(page.locator("#manualDriveShell")).to_be_visible()
            assert page.locator("body").get_attribute("data-pisd-v17") is None
            assert page.locator("#drivingCockpitToggle").is_visible()
            report["cases"][-1]["return_and_classic_verified"]=True
        finally:
            context.close()
            (output/"v17-m01-shell.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
        neutral()
    return report
