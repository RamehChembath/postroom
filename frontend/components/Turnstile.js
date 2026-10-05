"use client";
import { useEffect, useRef } from "react";
import Script from "next/script";

const SITE_KEY = process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY;

/** Renders nothing if no site key is configured (local dev) — registration
 *  still works because the backend skips verification when its secret key
 *  is unset too. In production, set both and this becomes a real spam gate. */
export default function Turnstile({ onToken }) {
  const ref = useRef(null);
  const widgetId = useRef(null);

  function renderWidget() {
    if (!SITE_KEY || !ref.current || !window.turnstile || widgetId.current) return;
    widgetId.current = window.turnstile.render(ref.current, {
      sitekey: SITE_KEY,
      callback: (token) => onToken(token),
      "expired-callback": () => onToken(""),
    });
  }

  useEffect(() => {
    if (window.turnstile) renderWidget();
    return () => { if (widgetId.current && window.turnstile) window.turnstile.remove(widgetId.current); };
  }, []);

  if (!SITE_KEY) return null;
  return (
    <>
      <Script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer onLoad={renderWidget} />
      <div ref={ref} style={{ margin: "14px 0" }} />
    </>
  );
}
