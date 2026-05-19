"use client";
import { useEffect, useState } from "react";

export default function Gauge({
  score,
  locked,
  label,
}: {
  score: number;
  locked: boolean;
  label: string;
}) {
  const circ = 351.8;
  const [offset, setOffset] = useState(circ);

  useEffect(() => {
    const id = setTimeout(() => {
      setOffset(circ - (circ * Math.min(100, Math.max(0, score))) / 100);
    }, 200);
    return () => clearTimeout(id);
  }, [score]);

  const stroke = locked ? "#B0791F" : "#5F7359";

  return (
    <div className={`gauge ${locked ? "locked" : ""}`}>
      <svg width="132" height="132" viewBox="0 0 132 132">
        <circle cx="66" cy="66" r="56" fill="none" stroke="#DDD2BF" strokeWidth="13" />
        <circle
          cx="66"
          cy="66"
          r="56"
          fill="none"
          stroke={stroke}
          strokeWidth="13"
          strokeLinecap="round"
          strokeDasharray={circ}
          strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 1.2s cubic-bezier(.2,.7,.2,1)" }}
        />
      </svg>
      <div className="val">
        <b>{locked ? "??" : score}</b>
        <span>{label}</span>
      </div>
    </div>
  );
}
