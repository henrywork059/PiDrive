"""M01 matched browser comparison, virtual-only, no drive authorization.

Compare the opt-in shell with the unchanged classic cockpit in the same
emulator run. Preserve timings as observations; do not invent a latency
acceptance threshold or claim physical qualification.
"""
import hashlib
import json
import statistics
import time
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import expect


# Locator.evaluate passes the located frame element, not its selector.
GEOMETRY = """f => {
    const i=f.querySelector('img'),o=f.querySelector('.mdrv-drive-overlay');
    const a=i.getBoundingClientRect(),b=o.getBoundingClientRect();
    return {image:[a.x,a.y,a.width,a.height],overlay:[b.x,b.y,b.width,b.height],
        natural:[i.naturalWidth,i.naturalHeight],fit:getComputedStyle(i).objectFit,
        scroll:scrollY,viewport:[innerWidth,innerHeight]};
}"""
ALIGNED = """s => {
    const f=document.querySelector(s),i=f.querySelector('img'),o=f.querySelector('.mdrv-drive-overlay');
    const a=i.getBoundingClientRect(),b=o.getBoundingClientRect();
    return i.naturalWidth===426&&i.naturalHeight===240&&a.height>0
      &&new URL(i.currentSrc||i.src,location.href).pathname==='/video_feed'
      &&getComputedStyle(i).objectFit==='contain'
      &&Math.abs(a.width/a.height-i.naturalWidth/i.naturalHeight)<.03
      &&['x','y','width','height'].every(k=>Math.abs(a[k]-b[k])<=2);
}"""


def capture_v17_comparison(browser, runtime, origin, output, revision):
    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    report={"revision":revision,"scope":"matched same-run virtual browser comparison; no latency threshold",
            "hardware_enabled":False,"polling_period_ms":{"GET /api/camera/fps-stats":850,
                "GET /api/status":1400,"GET /api/ai/status":1400},"pairs":[]}
    path=output/"v17-m01-comparison.json"

    def save():
        path.write_text(json.dumps(report,indent=2),encoding="utf-8")

    def neutral():
        state=runtime.status()
        assert state["hardware_enabled"] is False and state["running"]
        motor=state["engine"]["motor"]
        assert abs(motor["left_intended"])<.001 and abs(motor["right_intended"])<.001,motor

    def stop_hit(page, stop):
        return page.locator(stop).evaluate("""el=>{
            const r=el.getBoundingClientRect(),x=r.x+r.width/2,y=r.y+r.height/2;
            const hit=document.elementFromPoint(x,y);
            return {rect:[r.x,r.y,r.width,r.height],hit:!!hit&&el.contains(hit),
              viewport:[innerWidth,innerHeight],scroll:scrollY};
        }""")

    def check_stop(page,stop):
        row=stop_hit(page,stop)
        x,y,w,h=row["rect"]
        vw,vh=row["viewport"]
        assert row["hit"] and w>=44 and h>=44 and x>=0 and y>=0 and x+w<=vw+1 and y+h<=vh+1,row
        return row

    def measure(mode, viewport, variant, sample, pair):
        classic=variant=="classic"
        route="/manual-drive" if mode=="manual" else "/ai-mode"
        shell="#manualDriveShell" if mode=="manual" else "#aiModeShell"
        arm="#mdrvArm" if mode=="manual" else "#aiEnableMotor"
        live="#mdrvLiveCamera" if mode=="manual" else "#aiLive"
        frame="#mdrvPreviewFrame" if mode=="manual" else "#aiPreviewFrame"
        stop="#mdrvStopTop" if mode=="manual" else "#aiStopAll"
        context=browser.new_context(viewport={"width":viewport[0],"height":viewport[1]})
        row={"variant":variant,"sample":sample,"errors":[]}
        pair["samples"].append(row)
        events=[]
        try:
            page=context.new_page()
            page.bring_to_front()
            base=urlsplit(origin)
            def observe(request):
                u=urlsplit(request.url)
                if (u.scheme,u.netloc)==(base.scheme,base.netloc) and (u.path.startswith("/api/") or u.path=="/video_feed"):
                    events.append((time.monotonic(),request.method,u.path))
            page.on("request",observe)
            page.on("pageerror",lambda exc:row["errors"].append(str(exc)))
            neutral()
            started=time.monotonic()
            page.goto(origin+(route if classic else "/drive?mode="+mode),wait_until="domcontentloaded")
            expect(page.locator(shell)).to_be_visible()
            expect(page.locator(arm)).not_to_be_checked()
            if not classic:
                expect(page.locator("body")).to_have_attribute("data-pisd-v17-ready","true")
            row["navigation_to_shell_ms"]=(time.monotonic()-started)*1000
            action=time.monotonic()
            if page.locator(frame).get_attribute("data-preview-mode")!="live":
                page.locator(live).click()
                expect(page.locator(frame)).to_have_attribute("data-preview-mode","live",timeout=15000)
                row["start_live_to_mode_ms"]=(time.monotonic()-action)*1000
            else:
                row["start_live_to_mode_ms"]=None
            decode=time.monotonic()
            page.wait_for_function("""s=>{const i=document.querySelector(s+' img');return i&&
                i.naturalWidth===426&&i.naturalHeight===240&&
                new URL(i.currentSrc||i.src,location.href).pathname==='/video_feed';}""",arg=frame,timeout=15000)
            row["live_decode_wait_ms"]=(time.monotonic()-decode)*1000
            row["live_action_to_decode_ms"]=(time.monotonic()-action)*1000
            if classic:
                toggle=time.monotonic()
                page.locator("#drivingCockpitToggle").click()
                expect(page.locator("#drivingCockpitToggle")).to_have_attribute("aria-pressed","true")
                page.wait_for_function(ALIGNED,arg=frame,timeout=15000)
                row["classic_toggle_to_aligned_ms"]=(time.monotonic()-toggle)*1000
            else:
                page.wait_for_function(ALIGNED,arg=frame,timeout=15000)
            row["navigation_to_aligned_live_ms"]=(time.monotonic()-started)*1000
            # Measure the initial viewport, not an auto-scroll position.
            page.evaluate("window.scrollTo(0,0)")
            page.wait_for_function("scrollY===0")
            row["geometry"]=page.locator(frame).evaluate(GEOMETRY)
            # One long window per variant/pair, with per-request timestamps.
            # A one-request endpoint-count difference is the timer phase
            # envelope, not a new performance threshold. Keep actual counts.
            if sample==0:
                page.wait_for_timeout(2000)
                offset=len(events)
                begin=time.monotonic()
                page.wait_for_timeout(17000)
                elapsed=time.monotonic()-begin
                quiet=events[offset:]
                allowed={"GET /api/camera/fps-stats","GET /api/status"} if mode=="manual" else {"GET /api/ai/status"}
                labels=[m+" "+p for _,m,p in quiet]
                assert set(labels)==allowed,labels
                row["quiet_window_ms"]=elapsed*1000
                row["quiet_counts"]=dict(Counter(labels))
                row["quiet_timestamps_ms"]={k:[round((t-begin)*1000,3) for t,m,p in quiet if m+" "+p==k] for k in sorted(allowed)}
                row["quiet_interval_median_ms"]={k:statistics.median([v-u for u,v in zip(ts,ts[1:])]) for k,ts in row["quiet_timestamps_ms"].items()}
            if not classic and sample==0:
                # Named navigation, actual Tab order and focus-visible styling.
                nav=page.get_by_role("navigation",name="Driving cockpit mode")
                links=[nav.get_by_role("link",name=n,exact=True) for n in ("Manual","AI","Classic layout")]
                assert nav.get_by_role("link").count()==3
                assert nav.locator('[aria-current="page"]').count()==1
                links[0].focus()
                page.keyboard.press("Shift+Tab")
                page.keyboard.press("Tab")
                focus=[]
                for idx,link in enumerate(links):
                    if idx: page.keyboard.press("Tab")
                    expect(link).to_be_focused()
                    info=link.evaluate("""el=>{const r=el.getBoundingClientRect(),s=getComputedStyle(el);
                        return {name:el.textContent.trim(),focusVisible:el.matches(':focus-visible'),
                          outline:s.outlineStyle,outlineWidth:parseFloat(s.outlineWidth),
                          rect:[r.x,r.y,r.width,r.height],current:el.getAttribute('aria-current')};}""")
                    assert info["focusVisible"] and info["outline"]!="none" and info["outlineWidth"]>=2,info
                    assert info["rect"][2]>=44 and info["rect"][3]>=44,info
                    focus.append(info)
                row["navigation_keyboard"]=focus
                page.evaluate("document.activeElement?.blur();window.scrollTo(0,document.documentElement.scrollHeight)")
                page.wait_for_function("scrollY>0")
                row["stop_scrolled"]=check_stop(page,stop)
                page.evaluate("window.scrollTo(0,0)")
                row["stop_initial"]=check_stop(page,stop)
                original=page.locator(frame).evaluate(GEOMETRY)
                row["resize"]=[]
                for w,h in ((768,1024),(1024,768),(1440,900),tuple(viewport)):
                    page.set_viewport_size({"width":w,"height":h})
                    page.evaluate("window.scrollTo(0,0)")
                    page.wait_for_function(ALIGNED,arg=frame,timeout=15000)
                    page.wait_for_function("""s=>{const r=document.querySelector(s+' img').getBoundingClientRect();
                        return scrollY===0&&r.y>=0&&r.y+r.height<=innerHeight+2&&document.documentElement.scrollWidth<=innerWidth+1;}""",arg=frame,timeout=15000)
                    row["resize"].append({"geometry":page.locator(frame).evaluate(GEOMETRY),"stop":check_stop(page,stop)})
                restored=row["resize"][-1]["geometry"]
                assert max(abs(a-b) for a,b in zip(original["image"],restored["image"]))<=2,(original,restored)
                screenshot=output/f"v17-m01-comparison-{mode}-{viewport[0]}.png"
                page.screenshot(path=str(screenshot))
                row["screenshot"]={"file":screenshot.name,"sha256":hashlib.sha256(screenshot.read_bytes()).hexdigest()}
            row["stream_requests"]=sum(m=="GET" and p=="/video_feed" for _,m,p in events)
            assert row["stream_requests"]==1,row
            neutral()
            expect(page.locator(arm)).not_to_be_checked()
            assert not row["errors"],row["errors"]
        except Exception as exc:
            row["failure"]=str(exc)
            raise
        finally:
            context.close()
            save()
        neutral()

    # Alternate order by sample and viewport to reduce systematic warmup bias.
    for mode in ("manual","ai"):
        for viewport in ((1440,900),(390,844)):
            pair={"mode":mode,"viewport":list(viewport),"samples":[]}
            report["pairs"].append(pair)
            for sample in (0,1):
                order=("classic","v17") if (viewport[0]==1440)==(sample==0) else ("v17","classic")
                for variant in order:
                    measure(mode,viewport,variant,sample,pair)
            first={r["variant"]:r for r in pair["samples"] if r["sample"]==0}
            counts={k:first["v17"]["quiet_counts"][k]-v for k,v in first["classic"]["quiet_counts"].items()}
            pair["quiet_count_delta"]=counts
            pair["timing_medians_ms"]={}
            for variant in ("classic","v17"):
                rows=[r for r in pair["samples"] if r["variant"]==variant]
                pair["timing_medians_ms"][variant]={k:statistics.median([r[k] for r in rows]) for k in
                    ("navigation_to_shell_ms","live_action_to_decode_ms","navigation_to_aligned_live_ms")}
            save()
            assert all(abs(delta)<=1 for delta in counts.values()),counts
    return report
