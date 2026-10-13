# Mocked end-to-end test of the door site (login -> pay -> brand -> app). Run: python3 tests/door_test.py
import os, json
from playwright.sync_api import sync_playwright
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PAGE = 'file://' + os.path.join(ROOT, 'site', 'index.html')
st = {'paid': False, 'blocked': False, 'brand_saved': None, 'verify_fail': False, 'orders': 0}
J = lambda r, o, s=200: r.fulfill(status=s, content_type='application/json', headers={'access-control-allow-origin': '*'}, body=json.dumps(o))
def sb(r):
    u = r.request.url; m = r.request.method
    if m == 'OPTIONS': return r.fulfill(status=204, headers={'access-control-allow-origin': '*', 'access-control-allow-headers': '*', 'access-control-allow-methods': '*'})
    if '/rpc/public_settings' in u: return J(r, {'price_paise': 99900, 'validity_days': 365, 'currency': 'INR', 'product_name': 'Vedic Astro Suite', 'whatsapp': '918919748693', 'allow_signup': True})
    if 'grant_type=password' in u:
        b = json.loads(r.request.post_data); 
        if b['password'] == 'wrongpw': return J(r, {'error_description': 'Invalid login credentials'}, 400)
        return J(r, {'access_token': 'tok', 'refresh_token': 'ref', 'expires_in': 3600, 'user': {'id': 'u1', 'email': b['email']}})
    if '/functions/v1/get-app' in u:
        if st['blocked']: return J(r, {'reason': 'blocked'}, 403)
        if not st['paid']: return J(r, {'reason': 'not_paid'}, 402)
        return r.fulfill(status=200, content_type='text/html', headers={'access-control-allow-origin': '*'}, body='<html><head></head><body><h1 id=app>THE APP</h1></body></html>')
    if '/functions/v1/create-order' in u: st['orders'] += 1; return J(r, {'order_id': 'order_X1', 'amount': 99900, 'currency': 'INR', 'key_id': 'rzp_test_x', 'email': 'a@b.co'})
    if '/functions/v1/verify-payment' in u:
        if st['verify_fail']: st['paid'] = True; return J(r, {'error': 'db'}, 500)   # webhook "activates" later
        st['paid'] = True; return J(r, {'ok': True})
    if '/rest/v1/brand_profiles' in u: return J(r, [])
    if '/rpc/save_my_brand' in u: st['brand_saved'] = json.loads(r.request.post_data); return J(r, None, 204) if False else r.fulfill(status=204, headers={'access-control-allow-origin': '*'})
    return J(r, {})
RZP = "window.Razorpay=function(o){this.o=o;this.h={}};window.Razorpay.prototype.on=function(e,f){this.h[e]=f};window.Razorpay.prototype.open=function(){var o=this.o;window.__rzpOpts=o;setTimeout(function(){o.handler({razorpay_order_id:o.order_id,razorpay_payment_id:'pay_1',razorpay_signature:'sig'})},50)};"
def route(r):
    u = r.request.url
    if u.startswith(('file:', 'data:', 'blob:')): return r.continue_()
    if 'checkout.razorpay.com' in u: return r.fulfill(status=200, content_type='application/javascript', body=RZP)
    if 'supabase.co' in u: return sb(r)
    return r.abort()
res = []; ok = lambda n, c, d='': res.append((n, bool(c), d))
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/opt/pw-browsers/chromium')
    def newpage(w=1100):
        ctx = b.new_context(viewport={'width': w, 'height': 800}); ctx.route('**/*', route); pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e))); return ctx, pg, errs
    # 1) wrong password, then login -> pay page
    ctx, pg, errs = newpage(); pg.goto(PAGE); pg.wait_for_timeout(600)
    ok('login visible', pg.is_visible('#login'))
    pg.fill('#em', 'a@b.co'); pg.fill('#pw', 'wrongpw'); pg.click('#go'); pg.wait_for_timeout(500)
    ok('wrong password message', 'Wrong email or password' in pg.inner_text('#msg'))
    pg.fill('#pw', 'rightpw'); pg.click('#go'); pg.wait_for_timeout(900)
    ok('unpaid user sees pay page', pg.is_visible('#pay'))
    ok('price shown from settings', '₹999' in pg.inner_text('#priceBox') and '1 year' in pg.inner_text('#priceBox'), pg.inner_text('#priceBox').replace('\n', ' '))
    ok('pay button text', '₹999' in pg.inner_text('#payBtn'))
    # 2) pay -> brand -> app
    pg.click('#payBtn'); pg.wait_for_timeout(1200)
    ok('order created once', st['orders'] == 1)
    ok('razorpay got server order id + key', pg.evaluate("()=>window.__rzpOpts&&window.__rzpOpts.order_id")=='order_X1' and pg.evaluate("()=>window.__rzpOpts.key")=='rzp_test_x')
    ok('brand page after payment', pg.is_visible('#brand'))
    pg.fill('#bName', 'Acharya Test'); pg.fill('#bTag', 'Guidance'); pg.click('#bSw button[data-c="#3aa0ff"]')
    ok('live preview', pg.inner_text('#pvName') == 'Acharya Test')
    pg.click('#brSave'); pg.wait_for_timeout(1500)
    ok('brand saved with accent', st['brand_saved'] and st['brand_saved']['p_name'] == 'Acharya Test' and st['brand_saved']['p_accent'] == '#3aa0ff', str(st['brand_saved'])[:120])
    ok('app opens after save', pg.evaluate("()=>!!document.getElementById('app')"))
    ok('no page errors (flow 1)', not errs, '; '.join(errs)[:200]); ctx.close()
    # 3) returning paid user goes straight to app
    ctx, pg, errs = newpage(); ctx.add_init_script("localStorage.setItem('vax_sb_session',JSON.stringify({access_token:'tok',refresh_token:'ref',expires_at:Math.floor(Date.now()/1000)+3000,email:'a@b.co',uid:'u1'}))")
    pg.goto(PAGE); pg.wait_for_timeout(1500); ok('paid returning user -> app directly', pg.evaluate("()=>!!document.getElementById('app')")); ctx.close()
    # 4) blocked
    st['blocked'] = True; ctx, pg, errs = newpage(390); ctx.add_init_script("localStorage.setItem('vax_sb_session',JSON.stringify({access_token:'tok',refresh_token:'ref',expires_at:Math.floor(Date.now()/1000)+3000,email:'a@b.co',uid:'u1'}))")
    pg.goto(PAGE); pg.wait_for_timeout(1200); ok('blocked sees pause screen', pg.is_visible('#locked') and 'paused' in pg.inner_text('#lkT').lower())
    ok('no horizontal scroll on phone', pg.evaluate("()=>document.documentElement.scrollWidth<=window.innerWidth")); ctx.close(); st['blocked'] = False
    # 5) verify fails but webhook activated -> poll -> app
    st['paid'] = False; st['verify_fail'] = True; ctx, pg, errs = newpage(); ctx.add_init_script("localStorage.setItem('vax_sb_session',JSON.stringify({access_token:'tok',refresh_token:'ref',expires_at:Math.floor(Date.now()/1000)+3000,email:'a@b.co',uid:'u1'}))")
    pg.goto(PAGE); pg.wait_for_timeout(900); pg.click('#payBtn'); pg.wait_for_timeout(4500)
    ok('fallback polling reaches app', pg.evaluate("()=>!!document.getElementById('app')")); ctx.close()
    # 6) ?brand=1 opens editor for paid user
    st['paid'] = True; ctx, pg, errs = newpage(); ctx.add_init_script("localStorage.setItem('vax_sb_session',JSON.stringify({access_token:'tok',refresh_token:'ref',expires_at:Math.floor(Date.now()/1000)+3000,email:'a@b.co',uid:'u1'}))")
    pg.goto(PAGE + '?brand=1'); pg.wait_for_timeout(1200); ok('?brand=1 shows editor', pg.is_visible('#brand')); ctx.close()
    b.close()
for n, c, d in res: print(('PASS ' if c else 'FAIL ') + n, d)
print(sum(c for _, c, _ in res), '/', len(res))
