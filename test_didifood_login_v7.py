"""
DiDi Food login v7 - Dig into Vue component tree, fix post_data crash.
"""

import sys
import time
import json

sys.stdout.reconfigure(encoding='utf-8')

from playwright.sync_api import sync_playwright


def attempt_login():
    api_responses = []

    def handle_response(response):
        url = response.url
        if response.request.method == "POST" or any(kw in url.lower() for kw in ["login", "auth", "passport", "token"]):
            try:
                body = response.text()
            except Exception:
                body = "<could not read>"
            api_responses.append({"status": response.status, "url": url[:150], "body": body[:500]})

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            locale="es-MX",
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        )
        page = context.new_page()
        page.on("response", handle_response)

        login_url = (
            "https://page.didiglobal.com/public-biz/pc-login/3.0.8/index.html"
            "?appid=120838&role=1&source=70001&country_id=170"
            "&redirectUrl=https%3A%2F%2Fc.didi-food.com%2Flogin%2Fcallback"
            "%3FredirectUrl%3Dhttps%253A%252F%252Fwww.didi-food.com%252Fes-MX%252Ffood%252F"
            "&lang=es-MX"
        )
        print("[1] Loading login...")
        page.goto(login_url, timeout=60000, wait_until="networkidle")
        time.sleep(5)

        # Deep-inspect Vue component tree to find form data
        vue_deep = page.evaluate("""() => {
            function findAllVue(el, depth = 0) {
                const results = [];
                if (el.__vue__ && depth > 0) {
                    const vm = el.__vue__;
                    const data = {};
                    try {
                        const d = vm.$data;
                        for (const key of Object.keys(d)) {
                            const val = d[key];
                            if (typeof val !== 'function' && typeof val !== 'object') {
                                data[key] = val;
                            } else if (val && typeof val === 'object') {
                                data[key] = JSON.parse(JSON.stringify(val));
                            }
                        }
                    } catch(e) {}
                    results.push({
                        depth: depth,
                        tag: el.tagName,
                        componentName: vm.$options.name || vm.$options._componentTag || 'anonymous',
                        data: data,
                    });
                }
                if (depth < 10) {
                    for (const child of el.children) {
                        results.push(...findAllVue(child, depth + 1));
                    }
                }
                return results;
            }
            return findAllVue(document.body);
        }""")
        print(f"[2] Vue components found: {len(vue_deep)}")
        for comp in vue_deep:
            data_str = json.dumps(comp['data'], ensure_ascii=False, default=str)
            if len(data_str) > 300:
                data_str = data_str[:300] + "..."
            print(f"  [{comp['depth']}] <{comp['tag']}> {comp['componentName']}: {data_str}")

        # Now interact with form using proper Vue reactivity
        # First click the password tab
        print("\n[3] Interacting with form...")
        pwd_tab = page.locator("text=Ingresar con contrase").first
        if pwd_tab and pwd_tab.is_visible():
            pwd_tab.click()
            time.sleep(1)

        # After tab click, re-check Vue state
        vue_after_tab = page.evaluate("""() => {
            function findAllVue(el, depth = 0) {
                const results = [];
                if (el.__vue__ && depth > 0) {
                    const vm = el.__vue__;
                    try {
                        const d = JSON.parse(JSON.stringify(vm.$data));
                        const keys = Object.keys(d);
                        if (keys.length > 0 && keys.some(k => ['phone','password','agreed','loginType','formData','countryCode'].includes(k))) {
                            results.push({
                                componentName: vm.$options.name || 'anon',
                                data: d,
                            });
                        }
                    } catch(e) {}
                }
                if (depth < 10) {
                    for (const child of el.children) {
                        results.push(...findAllVue(child, depth + 1));
                    }
                }
                return results;
            }
            return findAllVue(document.body);
        }""")
        print(f"[3b] Relevant Vue components after tab click:")
        for comp in vue_after_tab:
            print(f"  {comp['componentName']}: {json.dumps(comp['data'], ensure_ascii=False, default=str)[:400]}")

        # Type phone number
        phone_input = page.get_by_placeholder("mero de tel").first
        if phone_input and phone_input.is_visible():
            phone_input.click()
            time.sleep(0.3)
            phone_input.type("3108532310", delay=80)
            time.sleep(1)

        # Type password
        pwd_input = page.locator("input[type='password']:visible").first
        if pwd_input:
            pwd_input.click()
            time.sleep(0.3)
            pwd_input.type("Tengoodrappi2004", delay=50)
            time.sleep(1)

        # Click terms
        acepto = page.get_by_text("Acepto", exact=False).first
        if acepto and acepto.is_visible():
            box = acepto.bounding_box()
            if box:
                page.mouse.click(box["x"] - 12, box["y"] + box["height"] / 2)
                time.sleep(1)

        # Re-check Vue state after filling everything
        vue_filled = page.evaluate("""() => {
            function findAllVue(el, depth = 0) {
                const results = [];
                if (el.__vue__) {
                    const vm = el.__vue__;
                    try {
                        const d = JSON.parse(JSON.stringify(vm.$data));
                        const keys = Object.keys(d);
                        if (keys.some(k => ['phone','password','agreed','loginType','formData','countryCode','isAgree'].includes(k))) {
                            results.push({
                                name: vm.$options.name || 'anon',
                                data: d,
                            });
                        }
                    } catch(e) {}
                }
                if (depth < 10) {
                    for (const child of el.children) {
                        results.push(...findAllVue(child, depth + 1));
                    }
                }
                return results;
            }
            return findAllVue(document.body);
        }""")
        print(f"\n[4] Vue state after filling form:")
        for comp in vue_filled:
            print(f"  {comp['name']}: {json.dumps(comp['data'], ensure_ascii=False, default=str)[:500]}")

        # Try setting Vue data directly if we found the right component
        print("\n[5] Setting Vue data directly...")
        set_result = page.evaluate("""() => {
            function findFormVue(el) {
                if (el.__vue__) {
                    const vm = el.__vue__;
                    const d = vm.$data;
                    // Look for component with form-related data
                    if (d.formData || d.phone !== undefined || d.isAgree !== undefined) {
                        return vm;
                    }
                }
                for (const child of el.children) {
                    const v = findFormVue(child);
                    if (v) return v;
                }
                return null;
            }
            const vm = findFormVue(document.body);
            if (!vm) return {error: 'No form Vue component found'};

            const d = vm.$data;
            // Try to set values
            if (d.formData) {
                if (d.formData.phone !== undefined) vm.$set(d.formData, 'phone', '3108532310');
                if (d.formData.password !== undefined) vm.$set(d.formData, 'password', 'Tengoodrappi2004');
                if (d.formData.agreed !== undefined) vm.$set(d.formData, 'agreed', true);
                if (d.formData.isAgree !== undefined) vm.$set(d.formData, 'isAgree', true);
            }
            if (d.phone !== undefined) d.phone = '3108532310';
            if (d.password !== undefined) d.password = 'Tengoodrappi2004';
            if (d.agreed !== undefined) d.agreed = true;
            if (d.isAgree !== undefined) d.isAgree = true;

            return {
                set: true,
                name: vm.$options.name,
                newData: JSON.parse(JSON.stringify(d)),
            };
        }""")
        print(f"  Result: {json.dumps(set_result, ensure_ascii=False, default=str)[:500]}")

        page.screenshot(path="data/raw/screenshot_didifood_v7_ready.png")

        # Clear API responses
        api_responses.clear()

        # Click login
        print("\n[6] Clicking login button...")
        # Use Playwright click on the div.button
        btn = page.locator("div.button.actived").first
        if btn and btn.is_visible():
            btn.click(force=True)
            print("  Clicked!")
        else:
            page.locator("text=Iniciar sesión").last.click(force=True)
            print("  Clicked (text fallback)!")

        time.sleep(12)

        # Results
        print(f"\n[7] API responses after click: {len(api_responses)}")
        for r in api_responses[:10]:
            print(f"  [{r['status']}] {r['url']}")
            print(f"    {r['body'][:200]}")

        page.screenshot(path="data/raw/screenshot_didifood_v7_final.png")
        print(f"\n[8] URL: {page.url[:100]}")

        body = page.inner_text("body")
        if "didi-food.com" in page.url and "didiglobal" not in page.url:
            print("  LOGIN EXITOSO!")
        else:
            print(f"  Still on login: {body[:300]}")

        browser.close()


if __name__ == "__main__":
    attempt_login()
