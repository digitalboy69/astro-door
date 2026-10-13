import os, json
from playwright.sync_api import sync_playwright
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PAGE = 'file://' + os.path.join(ROOT, 'admin', 'admin.html')
calls = []; uploads = []
M = [
 dict(user_id='u1', email='a@x.com', status='active', plan='paid', expires_at='2027-06-01T00:00:00Z', note='', created_at='2026-10-01T00:00:00Z', features={}, brand_name='Acharya <b>A</b>', brand_tagline='', brand_phone='', brand_accent='#d4a24a', brand_locked=False, paid_total=99900, last_paid='2026-10-02T00:00:00Z'),
 dict(user_id='u2', email='b@x.com', status='pending', plan=None, expires_at=None, note='', created_at='2026-10-05T00:00:00Z', features={}, brand_name='', brand_tagline='', brand_phone='', brand_accent='#d4a24a', brand_locked=False, paid_total=0, last_paid=None),
 dict(user_id='u3', email='c@x.com', status='blocked', plan='paid', expires_at='2027-01-01T00:00:00Z', note='', created_at='2026-10-06T00:00:00Z', features={'sky': False}, brand_name='', brand_tagline='', brand_phone='', brand_accent='#d4a24a', brand_locked=False, paid_total=99900, last_paid=None)]
def J(r, o, s=200): r.fulfill(status=s, content_type='application/json', headers={'access-control-allow-origin': '*'}, body=json.dumps(o))
def sb(r):
    u = r.request.url; m = r.request.method
    if m == 'OPTIONS': return r.fulfill(status=204, headers={'access-control-allow-origin': '*', 'access-control-allow-headers': '*', 'access-control-allow-methods': '*'})
    if 'grant_type=password' in u: return J(r, {'access_token': 't', 'refresh_token': 'r', 'expires_in': 3600, 'user': {'email': 'admin@x.com'}})
    if '/rpc/' in u:
        name = u.split('/rpc/')[1]; body = json.loads(r.request.post_data or '{}'); calls.append((name, body))
        if name == 'is_admin': return J(r, True)
        if name == 'admin_members': return J(r, M)
        if name == 'admin_list_payments': return J(r, [dict(email='a@x.com', order_id='o1', payment_id='pay_1', amount_paise=99900, status='paid', created_at='2026-10-02T00:00:00Z', paid_at='2026-10-02T00:00:00Z')])
        if name == 'public_settings': return J(r, {'price_paise': 99900, 'validity_days': 365, 'product_name': 'VAS', 'whatsapp': '9189', 'allow_signup': True})
        return r.fulfill(status=204, headers={'access-control-allow-origin': '*'})
    if '/storage/v1/object/list/app' in u: return J(r, [dict(name='current.html', updated_at='2026-10-01T00:00:00Z', metadata=dict(size=2400000))])
    if '/storage/v1/object/copy' in u: uploads.append('copy'); return J(r, {'Key': 'x'})
    if '/storage/v1/object/app/current.html' in u: uploads.append(('put', r.request.headers.get('x-upsert'), len(r.request.post_data or ''))); return J(r, {'Key': 'app/current.html'})
    return J(r, {})
def route(r):
    if r.request.url.startswith(('file:', 'data:')): return r.continue_()
    if 'supabase.co' in r.request.url: return sb(r)
    r.abort()
res = []; ok = lambda n, c, d='': res.append((n, bool(c), d))
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/opt/pw-browsers/chromium'); ctx = b.new_context(viewport={'width': 1100, 'height': 800}); ctx.route('**/*', route)
    pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('dialog', lambda d: d.accept())
    pg.goto(PAGE); pg.fill('#em', 'admin@x.com'); pg.fill('#pw', 'x123456'); pg.click('#lgGo'); pg.wait_for_timeout(900)
    ok('admin dashboard shown', pg.is_visible('#ap'))
    ok('3 customers listed', pg.locator('.row').count() == 3)
    ok('brand name escaped (no injected tag)', pg.locator('.row b').count() == 0)
    ok('stats: revenue', '₹1,998' in pg.inner_text('#stats'), pg.inner_text('#stats').replace('\n', ' ')[:120])
    pg.click('.chip[data-f=blocked]'); ok('filter blocked', pg.locator('.row').count() == 1); pg.click('.chip[data-f=all]')
    pg.fill('#q', 'b@x'); ok('search', pg.locator('.row').count() == 1); pg.fill('#q', '')
    pg.click('.row[data-u=u2]'); pg.wait_for_timeout(400); ok('drawer opens', pg.is_visible('#dr'))
    pg.click('[data-a=lifetime]'); pg.wait_for_timeout(600); ok('lifetime rpc', any(c[0] == 'admin_member_action' and c[1]['p_action'] == 'lifetime' and c[1]['p_user'] == 'u2' for c in calls))
    pg.fill('#dBn', 'New Brand'); pg.check('#dLock'); pg.click('#dBrand'); pg.wait_for_timeout(500)
    ok('brand rpc w/ lock', any(c[0] == 'admin_set_brand' and c[1]['p_name'] == 'New Brand' and c[1]['p_locked'] is True for c in calls))
    pg.uncheck('#ft_notes'); pg.click('#dFeat'); pg.wait_for_timeout(500); ok('features rpc', any(c[0] == 'admin_set_features' and c[1]['p_features'] == {'notes': False} for c in calls))
    pg.click('[data-a=extend]'); pg.wait_for_timeout(400); ok('extend rpc', any(c[0] == 'admin_member_action' and c[1]['p_action'] == 'extend' for c in calls))
    pg.click('#dClose'); pg.click('[data-t=pa]'); ok('payments shown', 'pay_1' in pg.inner_text('#pbody'))
    pg.click('[data-t=se]'); pg.fill('#sPrice', '1499'); pg.click('#sSave'); pg.wait_for_timeout(700)
    ok('price saved in paise', any(c[0] == 'admin_set_setting' and c[1]['p_key'] == 'price_paise' and c[1]['p_value'] == 149900 for c in calls))
    pg.click('[data-t=up]'); pg.wait_for_timeout(500); ok('app info shown', '2344 KB' in pg.inner_text('#upInfo') or 'KB' in pg.inner_text('#upInfo'), pg.inner_text('#upInfo'))
    open('/tmp/bad.html', 'w').write('<html>orig</html>'); pg.set_input_files('#upFile', '/tmp/bad.html'); pg.wait_for_timeout(300); ok('wrong file rejected', pg.is_disabled('#upGo'))
    cust = os.path.abspath(os.path.join(ROOT, '..', 'projects-and-apps', 'vedic-astro-suite', 'customer-edition.html'))
    pg.set_input_files('#upFile', cust); pg.wait_for_timeout(1200); ok('customer edition accepted', not pg.is_disabled('#upGo'), pg.inner_text('#upMsg')[:80])
    pg.click('#upGo'); pg.wait_for_timeout(1200); ok('backup + upsert upload', uploads[:1] == ['copy'] and uploads[1][0] == 'put' and uploads[1][1] == 'true', str(uploads))
    ok('no page errors', not errs, '; '.join(errs)[:200]); b.close()
for n, c, d in res: print(('PASS ' if c else 'FAIL ') + n, d)
print(sum(c for _, c, _ in res), '/', len(res))
