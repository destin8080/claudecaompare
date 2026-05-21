"use client";

import { useEffect, useState } from "react";
import { analyze, checkout, fetchConfig, type AnalyzeResponse } from "@/lib/api";
import { dict, type Lang } from "@/lib/i18n";
import Gauge from "@/components/Gauge";

type Cfg = { stripe_enabled: boolean; unlock_price_cents: number; unlock_price_display: string };

const statusMap = { weak: "warn", missing: "fail" } as const;

function money(n: number) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n);
}

export default function Home() {
  const [lang, setLang] = useState<Lang>("en");
  const t = dict[lang];

  const [url, setUrl] = useState("");
  const [visitors, setVisitors] = useState(5000);
  const [aov, setAov] = useState(200);

  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState<AnalyzeResponse | null>(null);
  const [error, setError] = useState("");

  const [cfg, setCfg] = useState<Cfg | null>(null);
  const [checkoutBusy, setCheckoutBusy] = useState(false);
  const [paidBanner, setPaidBanner] = useState(false);
  const [reportId, setReportId] = useState<string | null>(null);

  // bootstrap: config + ?paid=1 detection
  useEffect(() => {
    fetchConfig().then(setCfg).catch(() => setCfg(null));
    const params = new URLSearchParams(window.location.search);
    if (params.get("paid") === "1") {
      setPaidBanner(true);
      const rid = params.get("rid");
      if (rid) {
        const cachedUrl = sessionStorage.getItem("cyw_url") || "";
        const cachedVisitors = Number(sessionStorage.getItem("cyw_visitors") || "5000");
        const cachedAov = Number(sessionStorage.getItem("cyw_aov") || "200");
        if (cachedUrl) {
          setUrl(cachedUrl);
          setVisitors(cachedVisitors);
          setAov(cachedAov);
          // Re-run analysis with the unlock token
          (async () => {
            setLoading(true);
            try {
              const r = await analyze({
                url: cachedUrl,
                monthly_visitors: cachedVisitors,
                avg_order_value: cachedAov,
                unlock: rid,
              });
              setReport(r);
              setReportId(r.forms_summary?.report_id || null);
            } catch (e: any) {
              setError(e?.message || t.serverError);
            } finally {
              setLoading(false);
            }
          })();
        }
      }
      // Clean the URL bar
      window.history.replaceState({}, "", window.location.pathname);
    }
  }, []);

  const onAnalyze = async () => {
    setError("");
    if (!url.trim()) {
      setError(t.enterUrlError);
      return;
    }
    setLoading(true);
    setReport(null);
    try {
      const r = await analyze({ url, monthly_visitors: visitors, avg_order_value: aov });
      setReport(r);
      setReportId(r.forms_summary?.report_id || null);
      sessionStorage.setItem("cyw_url", url);
      sessionStorage.setItem("cyw_visitors", String(visitors));
      sessionStorage.setItem("cyw_aov", String(aov));
      if (r.error) setError(r.error);
    } catch (e: any) {
      setError(e?.message || t.serverError);
    } finally {
      setLoading(false);
    }
  };

  const onUnlock = async () => {
    if (!reportId) return;
    setCheckoutBusy(true);
    try {
      const r = await checkout(reportId, url);
      if (r.ok && r.url) {
        window.location.href = r.url;
        return;
      }
      setError(r.error || "Checkout error");
    } catch (e: any) {
      setError(e?.message || "Checkout error");
    } finally {
      setCheckoutBusy(false);
    }
  };

  const locked = !report ? true : !!report.teaser_locked;
  const shownScore = report ? (locked ? report.teaser_score : report.score || 0) : 0;
  const shownLossUsd = report?.teaser_loss_usd || 0;

  return (
    <div className="wrap">
      {/* MASTHEAD */}
      <header className="masthead">
        <div>
          <div className="brand">
            {t.brand}<span>{t.brandAccent}</span>{t.brandTail}
          </div>
          <div className="lang-switch">
            <button className={lang === "en" ? "on" : ""} onClick={() => setLang("en")}>EN</button>
            <button className={lang === "zh" ? "on" : ""} onClick={() => setLang("zh")}>中文</button>
          </div>
        </div>
        <div className="meta">
          <div>{t.tagline}</div>
          <div>
            {t.subject}: <b>{report?.url || "—"}</b> &nbsp;·&nbsp; {t.issued}: <b>{new Date().toLocaleDateString(lang === "zh" ? "zh-CN" : "en-GB", { day: "numeric", month: "short", year: "numeric" })}</b>
          </div>
        </div>
      </header>

      {/* HERO + INPUT */}
      <div className="hero">
        <div className="eyebrow">{t.confidential}</div>
        <h1>
          {t.heroTitle1} <em>{t.heroTitleEm}</em> {t.heroTitle2}
        </h1>
        <p className="lede">{t.heroLede}</p>

        <div className="url-form">
          <input
            placeholder={t.inputPlaceholder}
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && onAnalyze()}
          />
          <button onClick={onAnalyze} disabled={loading}>
            {loading ? t.analyzing : t.analyze}
          </button>
        </div>
        <div className="params-row">
          <label>
            {t.visitors}
            <input
              type="number"
              min={0}
              value={visitors}
              onChange={(e) => setVisitors(Math.max(0, Number(e.target.value) || 0))}
            />
          </label>
          <label>
            {t.aov}
            <input
              type="number"
              min={0}
              value={aov}
              onChange={(e) => setAov(Math.max(0, Number(e.target.value) || 0))}
            />
          </label>
        </div>
        {error && <div className="url-error">{error}</div>}
        {paidBanner && <div className="banner-thanks">✓ {t.paidThanks}</div>}
      </div>

      {!report && !loading && (
        <div className="empty">
          <h3>{lang === "zh" ? "输入网址，开始审计" : "Enter a URL and run the audit"}</h3>
          <p>{t.heroLede}</p>
        </div>
      )}

      {loading && (
        <div className="empty">
          <h3>{t.analyzing}</h3>
          <p>{lang === "zh" ? "正在抓取页面并分析。首次运行可能需要 20–40 秒。" : "Crawling pages and running checks. First run can take 20–40s."}</p>
        </div>
      )}

      {report && (
        <>
          {/* MONEY */}
          <div className="money">
            <div className="tag">{t.headlineEstimate}</div>
            <div className="figure">
              {money(shownLossUsd)}<small> {t.perMonth}</small>
            </div>
            <div className="sub">{t.headlineSub}</div>
            <div className="disclaim">{t.disclaim}</div>
          </div>

          {/* SCORE BAND */}
          <div className="scoreband">
            <Gauge score={shownScore} locked={locked} label={t.scoreOf} />
            <div className="read">
              <h3>{locked ? t.scoreHeadlineLocked : t.scoreHeadlineUnlocked}</h3>
              <p>{locked ? t.scoreBodyLocked : t.scoreBodyUnlocked}</p>
              <span className={`pill-grade ${locked ? "locked" : "unlocked"}`}>
                {locked ? t.pillLocked : t.pillUnlocked}
              </span>
              <div style={{ marginTop: 10, fontSize: 12, color: "var(--ink-soft)" }}>
                {report.fetched_pages.fetched} {t.fetchedPages}
                {report.fetched_pages.failed ? `  ·  ${report.fetched_pages.failed} failed` : ""}
              </div>
            </div>
          </div>

          {/* PAYWALL */}
          {locked && (
            cfg && !cfg.stripe_enabled ? (
              <div className="paywall notice">
                <h3>{t.paywallTitle}</h3>
                <p>{t.paywallNotConfigured}</p>
              </div>
            ) : (
              <div className="paywall">
                <h3>{t.paywallTitle}</h3>
                <p>{t.paywallSub}</p>
                <div className="pw-row">
                  <button onClick={onUnlock} disabled={checkoutBusy || !reportId}>
                    {checkoutBusy ? "…" : `${t.paywallButton} ${cfg?.unlock_price_display || "$29"}`}
                  </button>
                  <small>Stripe test mode · 4242 4242 4242 4242</small>
                </div>
              </div>
            )
          )}

          {/* SECTION 01 — TRUST */}
          <section className="block">
            <div className="block-head"><span className="sec-num">01</span><h2>{t.sec01}</h2></div>
            <p className="block-intro">{t.sec01Intro}</p>

            {(() => {
              const issues = report.trust.filter((tk) => tk.status !== "pass");
              if (issues.length === 0) {
                return <div className="empty" style={{ marginTop: 0 }}><p>{t.sec01AllPass}</p></div>;
              }
              return (
                <div className="trust-list">
                  {issues.map((tk) => {
                    const cls = statusMap[tk.status as "weak" | "missing"];
                    const text = tk.status === "weak" ? t.weak : t.missing;
                    return (
                      <div className="trust-row" key={tk.key}>
                        <div>
                          <div className="name">{tk.name}</div>
                          <div className="note">{tk.note}</div>
                          {tk.evidence && <div className="ev">{tk.evidence}</div>}
                        </div>
                        <div className={`status ${cls}`}>{text}</div>
                      </div>
                    );
                  })}
                </div>
              );
            })()}
          </section>

          {/* SECTION 02 — CONFLICTS */}
          <section className="block">
            <div className="block-head"><span className="sec-num">02</span><h2>{t.sec02}</h2></div>
            <p className="block-intro">{t.sec02Intro}</p>

            {locked ? (
              <div className="conflict">
                <div className="ctitle">
                  {report.conflicts_count} {lang === "zh" ? "处冲突已检测 — 解锁查看出处与原文" : "conflicts detected — unlock to see sources and snippets"}
                </div>
                <div className="versus">
                  <div className="vbit">
                    <div className="vlabel">{t.locked}</div>
                    <div className="vval">▒▒▒▒▒▒</div>
                  </div>
                  <div className="vbit">
                    <div className="vlabel">{t.locked}</div>
                    <div className="vval">▒▒▒▒▒▒</div>
                  </div>
                </div>
              </div>
            ) : (
              (report.conflicts || []).map((c, i) => (
                <div className="conflict" key={i}>
                  <div className="ctitle">{c.topic}</div>
                  <div className="versus">
                    {c.sides.map((s, j) => (
                      <div className="vbit" key={j}>
                        <div className="vlabel">{s.page_intent}</div>
                        <div className="vval">{s.value || "—"}</div>
                        <div className="vsrc">{s.page_url}</div>
                      </div>
                    ))}
                  </div>
                  <div className="cwhy">{c.description}</div>
                </div>
              ))
            )}

            {/* The loss model */}
            <div className="receipt">
              <div className="rtitle">{lang === "zh" ? "模型 — 公开透明" : "The model — fully disclosed"}</div>
              <div className="formula">
                {lang === "zh" ? "流失订单" : "lost orders"} <span className="op">=</span>{" "}
                {t.modelMonthlyVisitors} <span className="op">×</span> {t.modelReach}{" "}
                <span className="op">×</span> {t.modelDrop} <span className="op">×</span> {t.modelAov}
              </div>
              <div style={{ height: 18 }}></div>
              <div className="rrow">
                <span>{t.modelMonthlyVisitors}</span>
                <span>{visitors.toLocaleString()} <span className="src">— input</span></span>
              </div>
              <div className="rrow">
                <span>{t.modelReach}</span>
                <span>{Math.round((report.forms?.form_reach_rate ?? 0.12) * 100)}% <span className="src">— benchmark</span></span>
              </div>
              <div className="rrow">
                <span>{t.modelDrop}</span>
                <span>{report.forms_summary.extra_required_total > 0 ? `${Math.min(65, report.forms_summary.extra_required_total * 7)}%` : "—"} <span className="src">— derived</span></span>
              </div>
              <div className="rrow">
                <span>{t.modelAov}</span>
                <span>${aov} <span className="src">— input</span></span>
              </div>
              <div className="rtotal">
                <span>{t.modelTotal}</span>
                <b>≈ {money(shownLossUsd)}</b>
              </div>
            </div>
            <p className="honest">{t.modelHonest}</p>
          </section>

          {/* SECTION 03 — ACTIONS */}
          <section className="block">
            <div className="block-head"><span className="sec-num">03</span><h2>{t.sec03}</h2></div>
            <div className="actions">
              {report.actions.map((a, i) => (
                <div className="act" key={i}>
                  <div className="atext">
                    <b>{a.title}</b>
                    <span className="when">{a.when}</span>
                    <p>{a.detail}</p>
                  </div>
                </div>
              ))}
              {locked && (
                <div className="act-locked">
                  {lang === "zh" ? "解锁完整报告以查看全部行动建议" : "Unlock the full report to see every recommended action"}
                </div>
              )}
            </div>
          </section>

          {/* FOOTER */}
          <footer>
            <div className="rule"></div>
            <p className="big">{t.footer1}</p>
            <p>{t.footer2}</p>
            <p style={{ marginTop: 6 }}>{t.poweredBy}</p>
          </footer>
        </>
      )}
    </div>
  );
}
