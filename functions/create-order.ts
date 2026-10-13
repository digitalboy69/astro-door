// create-order: signed-in user asks to pay. Price comes from the server settings, never from the browser.
import { cors, json, userFrom, rest, settings } from "./_common.ts";
const KEY_ID = Deno.env.get("RAZORPAY_KEY_ID") || "";
const KEY_SECRET = Deno.env.get("RAZORPAY_KEY_SECRET") || "";

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
  if (!KEY_ID || !KEY_SECRET) return json({ error: "payments_not_configured" }, 503);
  const user = await userFrom(req);
  if (!user) return json({ error: "login" }, 401);
  const m = await rest("member_access?user_id=eq." + user.id + "&select=status,plan");
  const row = (m.ok ? await m.json() : [])[0];
  if (!row) return json({ error: "no_record" }, 403);
  if (row.status === "blocked") return json({ error: "blocked" }, 403);
  if (row.plan === "lifetime") return json({ error: "already_lifetime" }, 409);
  const s = await settings();
  const amount = Number(s.price_paise), currency = String(s.currency || "INR");
  if (!amount || amount < 100) return json({ error: "bad_price" }, 500);
  const o = await fetch("https://api.razorpay.com/v1/orders", {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: "Basic " + btoa(KEY_ID + ":" + KEY_SECRET) },
    body: JSON.stringify({ amount, currency, receipt: ("v" + Date.now()).slice(0, 40), notes: { user_id: user.id } }),
  });
  if (!o.ok) return json({ error: "razorpay", status: o.status }, 502);
  const order = await o.json();
  const ins = await rest("payments", { method: "POST", headers: { Prefer: "return=minimal" }, body: JSON.stringify({ user_id: user.id, order_id: order.id, amount_paise: amount, currency }) });
  if (!ins.ok) return json({ error: "db" }, 500);
  return json({ order_id: order.id, amount, currency, key_id: KEY_ID, email: user.email || "" });
});
