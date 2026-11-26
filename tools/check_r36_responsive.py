"""Responsive geometry and resize round trips using disposable hardware-free fixtures."""
import argparse
import json
import tempfile
import traceback
from contextlib import ExitStack
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright

from check_browser_ui import HEIGHTS, ORIGIN, WIDTHS, PAGES, fixture


def reachable(locator, width, height, label):
    expect(locator).to_be_visible()
    locator.scroll_into_view_if_needed()
    box = locator.bounding_box()
    assert box and box['width'] > 0 and box['height'] > 0, label
    assert box['x'] >= -2 and box['x'] + box['width'] <= width + 2, (label, box)
    assert box['y'] < height and box['y'] + box['height'] > 0, (label, box)
    return {key: round(value, 1) for key, value in box.items()}


def square(locator):
    locator.page.wait_for_function('(el) => { const r=el.getBoundingClientRect(); return r.width >= 100 && Math.abs(r.width-r.height) <= 2; }', arg=locator.element_handle())
    box = locator.bounding_box()
    assert box and box['width'] >= 100 and abs(box['width'] - box['height']) <= 2, box
    return box


def dashboard(page, width, height):
    page.wait_for_function('() => state.statusPollingReady')
    if width <= 1080:
        expect(page.locator('#workspace')).to_have_css('display', 'flex')
        expect(page.locator('#workspace > .dock-panel[data-panel="manual"] .manual-shell')).to_have_css('overflow', 'visible')
        pad = square(page.locator('#joystickArea'))
        preview = page.locator('.viewer-frame').bounding_box()
        assert preview and abs(preview['width'] / preview['height'] - 16 / 9) < 0.06, preview
        assert page.locator('#workspace').evaluate('(el) => el.scrollHeight <= el.clientHeight + 2')
        assert pad['width'] >= 100
    else:
        expect(page.locator('#workspace')).to_have_css('display', 'grid')
        square(page.locator('#joystickArea'))
    # Resize the same page, not a fresh context. Keep saved geometry unchanged.
    original = page.evaluate('() => JSON.stringify(currentLayout())')
    page.evaluate('() => saveLayout(state.page, currentLayout())')
    saved = page.evaluate('() => localStorage.getItem(layoutStorageKey(state.page))')
    assert saved == original
    page.set_viewport_size({'width': 1440, 'height': 900})
    expect(page.locator('#workspace')).to_have_css('display', 'grid')
    square(page.locator('#joystickArea'))
    # Begin a real desktop dock drag, then cross into stacked mode before release.
    head = page.locator('#workspace > .dock-panel[data-panel="status"] .panel-head')
    head.scroll_into_view_if_needed()
    box = head.bounding_box()
    page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
    page.mouse.down()
    try:
        page.wait_for_function('() => Boolean(state.dragging)')
        page.mouse.move(box['x'] + box['width'] / 2 + 30, box['y'] + box['height'] / 2)
        page.set_viewport_size({'width': 390, 'height': 844})
        expect(page.locator('#workspace')).to_have_css('display', 'flex')
        page.wait_for_function('() => !state.dragging && !state.resizing')
    finally:
        page.mouse.up()
    square(page.locator('#joystickArea'))
    page.set_viewport_size({'width': width, 'height': height})
    assert page.evaluate('() => JSON.stringify(currentLayout())') == original
    assert page.evaluate('() => localStorage.getItem(layoutStorageKey(state.page))') == saved
    assert page.evaluate('() => Object.values(state.stepInputs).every(value => !value)')
    expect(page.locator('#estopToggle')).to_be_enabled()
    return {'layout_roundtrip': True, 'stored_layout_unchanged': True, 'drag_cancelled_at_breakpoint': True, 'square_pad': True}


def pisd(page, page_name, width):
    result = {}
    if page_name == 'manual':
        square(page.locator('#mdrvDragPad'))
        result['square_pad'] = True
        if width <= 1180:
            areas = page.locator('.mdrv-shell').evaluate('(el) => getComputedStyle(el).gridTemplateAreas')
            assert 'files' in areas, areas
            result['files_area'] = True
        if width <= 759:
            ids = ('manualDriveStatusPanel', 'manualDriveCameraPanel', 'manualDrivePadPanel',
                   'manualDriveStopPanel', 'manualDriveFilesPanel')
            boxes = [page.locator('#' + id_).bounding_box() for id_ in ids]
            assert all(boxes), boxes
            assert all(a['y'] + a['height'] <= b['y'] + 2 for a, b in zip(boxes, boxes[1:])), boxes
            result['stack_order'] = True
    if page_name in ('manual', 'ai'):
        selector = '#mdrvPreviewFrame' if page_name == 'manual' else '#aiPreviewFrame'
        frame = page.locator(selector)
        image = frame.locator('img')
        assert image.evaluate('(el) => ["contain", "cover", "fill"].includes(getComputedStyle(el).objectFit)')
        if width <= 759:
            box = frame.bounding_box()
            assert box and abs(box['width'] / box['height'] - 16 / 9) < 0.06, box
            result['preview_aspect'] = True
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('component', choices=PAGES)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--revision', required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    cases = []
    sizes = list(zip(WIDTHS, HEIGHTS)) + [(844, 390)]
    with tempfile.TemporaryDirectory() as temp, ExitStack() as stack:
        client = fixture(args.component, Path(temp), stack)
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            for page_name, path, stop, primary, preview, opener in PAGES[args.component]:
                if page_name not in ('dashboard', 'front', 'manual', 'ai', 'settings', 'presentation'):
                    continue
                for width, height in sizes:
                    context = browser.new_context(viewport={'width': width, 'height': height},
                                                  has_touch=width <= 900, reduced_motion='reduce')
                    page = context.new_page()
                    writes, errors = [], []
                    case = {'page': page_name, 'width': width, 'height': height, 'errors': errors}
                    cases.append(case)
                    page.on('pageerror', lambda error: errors.append(str(error)))

                    def route_request(route):
                        req = route.request
                        url = urlsplit(req.url)
                        if f'{url.scheme}://{url.netloc}' != ORIGIN:
                            route.abort()
                        elif req.method != 'GET':
                            writes.append(url.path)
                            route.fulfill(status=409, json={'ok': False, 'message': 'Synthetic rejected mutation'})
                        elif url.path in ('/video_feed', '/api/camera/frame.jpg'):
                            route.fulfill(status=204, body='')
                        else:
                            response = client.get(url.path + ('?' + url.query if url.query else ''), base_url=ORIGIN)
                            route.fulfill(status=response.status_code, content_type=response.content_type,
                                          body=response.get_data())

                    context.route('**/*', route_request)
                    try:
                        page.goto(ORIGIN + path, wait_until='load')
                        if args.component == 'PiServer':
                            case.update(dashboard(page, width, height))
                        else:
                            case.update(pisd(page, page_name, width))
                        if stop:
                            target = page.locator(stop)
                            expect(target).to_be_enabled()
                            case['stop'] = reachable(target, width, height, 'STOP')
                            if args.component == 'PiSD' and width <= 900:
                                assert case['stop']['height'] >= 44, case['stop']
                        case['primary'] = reachable(page.locator(primary), width, height, 'Primary')
                        if preview:
                            case['preview'] = reachable(page.locator(preview), width, height, 'Preview')
                        if opener:
                            control = page.locator(opener)
                            if width <= 900:
                                control.tap()
                            else:
                                control.press('Enter')
                            save = {'dashboard': '#saveStyleSettingsBtn', 'manual': '#mdrvOverlaySettingsApply',
                                    'ai': '#aiWorkflowSettingsApply'}[page_name]
                            case['dialog_save'] = reachable(page.locator(save), width, height, 'Dialog Save/Apply')
                            page.screenshot(path=str(args.output / f'{page_name}-{width}x{height}-dialog.png'))
                            page.keyboard.press('Escape')
                        assert set(writes) <= {'/api/camera/preview_state'}, writes
                        case['writes'] = writes[:]
                        page.screenshot(path=str(args.output / f'{page_name}-{width}x{height}.png'), full_page=True)
                    except Exception:
                        errors.append(traceback.format_exc())
                    finally:
                        context.close()
                    print(page_name, width, height, 'FAIL' if errors else 'PASS', errors, flush=True)
            browser.close()
    (args.output / 'matrix.json').write_text(json.dumps({'revision': args.revision, 'cases': cases}, indent=2), encoding='utf-8')
    if any(case['errors'] for case in cases):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
