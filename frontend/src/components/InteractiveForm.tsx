"use client";
import { useMemo, useState } from "react";
import { dict, type Lang } from "@/lib/i18n";

export default function InteractiveForm({ lang }: { lang: Lang }) {
  const t = dict[lang];

  const [dateIdx, setDateIdx] = useState(0);
  const [slot, setSlot] = useState("");
  const [gift, setGift] = useState(true);
  const [recipientName, setRecipientName] = useState("");
  const [recipientPhone, setRecipientPhone] = useState("");
  const [message, setMessage] = useState("");
  const [hidePrice, setHidePrice] = useState(true);
  const [address, setAddress] = useState("");

  const dates = useMemo(() => {
    const out: { label: string; date: string }[] = [];
    const days = lang === "zh" ? ["日", "一", "二", "三", "四", "五", "六"] : ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"];
    const today = new Date();
    for (let i = 0; i < 3; i++) {
      const d = new Date(today);
      d.setDate(today.getDate() + i);
      const label =
        i === 0
          ? lang === "zh" ? "今天" : "Today"
          : days[d.getDay()];
      const month = lang === "zh"
        ? `${d.getMonth() + 1}月${d.getDate()}日`
        : d.toLocaleString("en-US", { month: "short", day: "numeric" });
      out.push({ label, date: month });
    }
    return out;
  }, [lang]);

  const freePct = Math.min(100, Math.round((address.length / 30) * 100));
  const counterMax = 120;

  return (
    <div className="preview-frame">
      <div className="pv-chrome">
        <i></i><i></i><i></i>
        <span>your-site.com / order</span>
      </div>
      <div className="pv-body">
        <span className="mock-tag">{t.formHeading}</span>

        <div className="steps">
          <div className="on">{lang === "zh" ? "商品" : "Cake"}</div>
          <div className="on">{lang === "zh" ? "配送" : "Delivery"}</div>
          <div>{lang === "zh" ? "留言" : "Message"}</div>
          <div>{lang === "zh" ? "支付" : "Pay"}</div>
        </div>

        <div className="cutoff">
          <span className="dot"></span>
          <span>
            <b>{t.cutoffBanner}</b>
          </span>
        </div>

        <div className="fld">
          <label><span className="pin">1</span> {t.fldDate}</label>
          <div className="datechips">
            {dates.map((d, i) => (
              <button
                type="button"
                key={i}
                className={i === dateIdx ? "sel" : ""}
                onClick={() => setDateIdx(i)}
              >
                <b>{d.label}</b>{d.date}
              </button>
            ))}
          </div>
        </div>

        <div className="fld">
          <label><span className="pin">2</span> {t.fldSlot}</label>
          <select className="inp" value={slot} onChange={(e) => setSlot(e.target.value)}>
            <option value="">—</option>
            <option>10:00 – 13:00</option>
            <option>13:00 – 16:00</option>
            <option>16:00 – 19:00</option>
          </select>
        </div>

        <div
          className={`gifttoggle ${gift ? "on" : ""}`}
          onClick={() => setGift(!gift)}
          role="switch"
          aria-checked={gift}
          tabIndex={0}
          onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && setGift(!gift)}
        >
          <div className="sw"></div>
          <span className="pin">3</span>
          <span>{t.fldGiftToggle}</span>
        </div>

        <div className="two">
          <div className="fld">
            <label>{t.fldRecipientName}</label>
            <input
              className="inp"
              placeholder={lang === "zh" ? "谁来收礼物" : "Who receives the gift"}
              value={recipientName}
              onChange={(e) => setRecipientName(e.target.value)}
            />
          </div>
          <div className="fld">
            <label><span className="pin">4</span> {t.fldRecipientPhone}</label>
            <input
              className="inp"
              placeholder="+60 1_ ___ ____"
              value={recipientPhone}
              onChange={(e) => setRecipientPhone(e.target.value)}
            />
          </div>
        </div>
        <div className="helper" style={{ marginTop: -7, marginBottom: 13 }}>
          {t.fldRecipientHelper}
        </div>

        <div className="fld">
          <label>
            <span className="pin">5</span> {t.fldMessage}{" "}
            <span style={{ color: "var(--ink-soft)", fontWeight: 400 }}>
              · {message.length}/{counterMax}
            </span>
          </label>
          <textarea
            className="inp"
            rows={2}
            value={message}
            maxLength={counterMax}
            onChange={(e) => setMessage(e.target.value)}
            placeholder={lang === "zh" ? "生日快乐！来自……" : "Happy Birthday! With love, ..."}
          />
        </div>

        <div
          className={`ckrow ${hidePrice ? "on" : ""}`}
          onClick={() => setHidePrice(!hidePrice)}
          role="checkbox"
          aria-checked={hidePrice}
          tabIndex={0}
          onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && setHidePrice(!hidePrice)}
        >
          <div className="box"></div>
          <div>
            <b>{t.fldHidePrice}</b>
            <p>{t.fldHidePriceSub}</p>
          </div>
        </div>

        <div className="fld">
          <label><span className="pin">6</span> {t.fldAddress}</label>
          <input
            className="inp"
            placeholder={lang === "zh" ? "地址 — 输入后立即显示运费" : "Address — surcharge shown instantly below"}
            value={address}
            onChange={(e) => setAddress(e.target.value)}
          />
        </div>

        <div className="freebar">
          <div className="ft">
            <span>
              <span className="pin" style={{ width: 15, height: 15, fontSize: 9 }}>7</span> {t.fldFreeBar}
            </span>
            <b>RM 35 {t.fldToGo}</b>
          </div>
          <div className="track">
            <i style={{ width: `${freePct}%` }}></i>
          </div>
        </div>

        <button className="cta" type="button" onClick={(e) => e.preventDefault()}>
          {t.ctaContinue}  ·  RM 165
        </button>
        <div className="cta-sub">🔒 {t.secureSub}</div>
      </div>
    </div>
  );
}
