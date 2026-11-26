"""Additional R35 setup workflows; reuse hardware-free fixtures and intercept every write."""
import argparse
import json
import tempfile
import traceback
from contextlib import ExitStack
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright

from check_browser_ui import HEIGHTS, ORIGIN, WIDTHS, fixture


def check_slider_pair(page, first, second, width):
    page.keyboard.press('Tab')
    first.focus()
    expect(first).to_be_focused()
    expect(first).to_have_css('outline-style', 'solid')
    first.press('Home')
    first.press('ArrowRight')
    page.keyboard.press('Tab')
    expect(second).to_be_focused()
    page.keyboard.press('Shift+Tab')
    expect(first).to_be_focused()
    if width == 390:
        second.scroll_into_view_if_needed()
        box = second.bounding_box()
        second.tap(position={'x': box['width'] * 0.75, 'y': box['height'] / 2})
    else:
        second.press('End')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('component', choices=('PiServer', 'PiSD'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--revision', required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    cases = []
    with tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
        client = fixture(args.component, Path(tmp), stack)
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            paths = ('/',) if args.component == 'PiServer' else ('/settings', '/panel-presentation')
            for path in paths:
                for width, height in zip(WIDTHS, HEIGHTS):
                    context = browser.new_context(viewport={'width': width, 'height': height},
                                                  has_touch=width == 390, reduced_motion='reduce')
                    page = context.new_page()
                    writes, errors = [], []
                    case = {'path': path, 'width': width, 'errors': errors}
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
                            page.wait_for_function('() => state.statusPollingReady')
                            for field in ('maxThrottle', 'steerMix', 'steerBias', 'steerCurve', 'throttleCurve',
                                          'steerRate', 'throttleRate', 'leftMaxSpeed', 'rightMaxSpeed'):
                                value = page.locator('#' + field + 'Value').text_content().replace('×', ' times')
                                expect(page.locator('#' + field)).to_have_attribute('aria-valuetext', value)
                            expect(page.locator('#maxThrottle')).to_have_accessible_name('Max throttle')
                            expect(page.locator('#steerMix')).to_have_accessible_name('Steering mix')
                            expect(page.locator('#saveRuntimeBtn')).to_have_accessible_description('Tuning ready.')
                            before = list(writes)
                            first, second = page.locator('#steerCurve'), page.locator('#throttleCurve')
                            check_slider_pair(page, first, second, width)
                            expect(first).to_have_attribute('aria-valuetext', '1.05 times')
                            expect(second).to_have_attribute('aria-valuetext', f'{int(second.input_value()) / 100:.2f} times')
                            assert page.evaluate('() => Object.values(state.stepInputs).every(value => !value)')
                            expect(page.locator('#estopToggle')).to_be_enabled()
                            case['named_ranges'] = 9
                        else:
                            if path == '/settings':
                                expect(page.locator('#stApplyDetail')).to_contain_text('Saved settings loaded')
                                first = page.locator('input[name="fontScale"]')
                                second = page.locator('input[name="panelGap"]')
                                expect(page.locator('#stSaveSettings')).to_have_accessible_description(
                                    page.locator('#stApplyDetail').text_content())
                                expect(page.locator('#stStopAll')).to_be_enabled()
                                fields = page.locator('form input[type="range"]')
                                count = 20
                            else:
                                expect(page.locator('#ppFeedback')).to_have_text('Panel presentation settings ready.')
                                auto = page.locator('#ppAutoSave')
                                if auto.is_checked():
                                    auto.tap() if width == 390 else auto.press('Space')
                                expect(auto).not_to_be_checked()
                                first, second = page.locator('#ppFontScale'), page.locator('#ppPanelGap')
                                fields = page.locator('#ppForm input[type="range"]')
                                count = 19
                            expect(fields).to_have_count(count)
                            assert all(fields.evaluate_all('(els) => els.map(el => el.getAttribute("aria-valuetext"))'))
                            before = list(writes)
                            check_slider_pair(page, first, second, width)
                            expect(first).to_have_attribute('aria-valuetext', first.input_value() + ' times')
                            expect(second).to_have_attribute('aria-valuetext', second.input_value() + ' pixels')
                            if path == '/settings':
                                expect(page.locator('#stStopAll')).to_be_enabled()
                            else:
                                expect(page.locator('#ppFeedback')).to_have_text('Live preview applied only.')
                            case['named_ranges'] = count
                        assert writes == before, (before, writes)
                        case['local_only'] = True
                        case['native_keyboard'] = True
                        case['touch_slider'] = width == 390
                        page.screenshot(path=str(args.output / f'{path.strip("/") or "dashboard"}-{width}.png'),
                                        full_page=True, animations='disabled')
                    except Exception:
                        errors.append(traceback.format_exc())
                    finally:
                        case['writes'] = list(writes)
                        context.close()
                    print(path, width, 'FAIL' if errors else 'PASS', errors, flush=True)
            browser.close()
    (args.output / 'matrix.json').write_text(json.dumps({'revision': args.revision, 'cases': cases}, indent=2), encoding='utf-8')
    if any(case['errors'] for case in cases):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
