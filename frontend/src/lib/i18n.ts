export type Lang = "en" | "zh";

export const dict = {
  en: {
    brand: "Compare",
    brandAccent: "Your",
    brandTail: "Website",
    tagline: "Website Trust & Conversion Audit",
    confidential: "Confidential — Prepared for the site owner",
    heroTitle1: "Your customers trust you. They just",
    heroTitleEm: "can't tell",
    heroTitle2: "if they'll make the cut-off.",
    heroLede:
      "This audit grades the trust signals a buyer looks for, finds where your own pages disagree, and turns the friction into an estimate of lost orders.",
    inputPlaceholder: "https://your-website.com",
    analyze: "Run Audit",
    analyzing: "Analyzing…",
    headlineEstimate: "Your monthly loss",
    perMonth: "/ month",
    headlineSub:
      "Estimated value of orders abandoned each month because of trust gaps and conflicting information on your site — modelled below.",
    disclaim:
      "Directional estimate, not a precise forecast. Visitors and order value are owner-supplied placeholders; the figure's value is its order of magnitude.",
    scoreOf: "/ 100",
    scoreHeadlineLocked: "Preview score — partial view",
    scoreHeadlineUnlocked: "Strong foundation, leaky at the moment of decision",
    scoreBodyLocked:
      "This is the public preview. Your real audit score is hidden — unlock the full report to see the verified score, every conflict found, and the action plan.",
    scoreBodyUnlocked:
      "Trust foundation looks solid. The losses come from inconsistent information that creates doubt right before a time-sensitive purchase.",
    pillLocked: "Preview · Unlock to reveal real score",
    pillUnlocked: "Full report unlocked",
    sec01: "Hard Trust Scan",
    sec01Intro:
      "Only weak or missing signals are listed below — the items your site already passes are kept off the report for brevity.",
    sec01AllPass: "Every trust signal passed. Nothing to fix here.",
    sec02: "The Hesitation Tax",
    sec02Intro:
      "Different pages saying different things creates doubt. Below are the conflicts we found and the model behind the loss estimate.",
    sec03: "Recommended Actions",
    pass: "Pass",
    weak: "Weak",
    missing: "Missing",
    conflicting: "Conflicting",
    paywallTitle: "Unlock the full audit",
    paywallSub:
      "Pay once. See your real score, every conflict found, every required field flagged, plus the action plan you can hand to your developer.",
    paywallButton: "Unlock for",
    paywallNotConfigured:
      "Payments are not configured on this server yet. Add STRIPE_SECRET_KEY in backend/.env and restart the API — your report will then unlock end-to-end.",
    paidThanks: "Payment received — full report unlocked.",
    footer1: "Fix the conflicts, then re-run the audit to watch your score climb.",
    footer2:
      "Compare Your Website · Directional audit. Estimates are heuristic and depend on owner-supplied inputs.",
    visitors: "Monthly visitors",
    aov: "Average order value (USD)",
    issued: "Issued",
    subject: "Subject",
    locked: "Locked",
    seeFull: "Unlock full report",
    poweredBy: "Crawled with Playwright · Analyzed in real time",
    modelMonthlyVisitors: "Monthly visitors",
    modelReach: "Visitors reaching checkout / inquiry",
    modelDrop: "Drop-off from friction / uncertainty",
    modelAov: "Average order value",
    modelTotal: "Estimated monthly loss",
    modelHonest: "Directional estimate only. Visitors and order value are your inputs; the two rates use industry benchmarks you can override.",
    enterUrlError: "Please enter a website URL first.",
    serverError: "The server could not complete this audit. Please try again.",
    fetchedPages: "pages analyzed",
    of: "of",
  },
  zh: {
    brand: "Compare",
    brandAccent: "Your",
    brandTail: "Website",
    tagline: "网站信任与转化审计报告",
    confidential: "机密 — 仅供网站所有者",
    heroTitle1: "顾客信任你的产品，他们只是",
    heroTitleEm: "无法判断",
    heroTitle2: "自己赶不赶得上截单。",
    heroLede:
      "本审计为你检查买家会查看的信任信号，找出不同页面之间互相矛盾的地方，并把这些摩擦换算成预估的订单流失金额。",
    inputPlaceholder: "https://你的网站.com",
    analyze: "开始分析",
    analyzing: "分析中…",
    headlineEstimate: "你每月在亏的钱",
    perMonth: "/ 每月",
    headlineSub:
      "由于信任缺口与页面信息矛盾，每月被放弃订单的预估金额 — 模型见下文。",
    disclaim:
      "这是方向性估算，并非精确预测。访问量与客单价为你提供的占位输入；数字真正的价值在于其数量级。",
    scoreOf: "/ 100",
    scoreHeadlineLocked: "预览分数 — 部分视图",
    scoreHeadlineUnlocked: "信任基础不错，但临门一脚漏单严重",
    scoreBodyLocked:
      "这只是公开预览。你的真实评分被遮蔽 — 解锁完整报告后可看到经核验的分数、所有冲突点以及行动清单。",
    scoreBodyUnlocked:
      "信任基础尚可，损失主要来自页面信息不一致 — 让顾客在下单的关键时刻产生犹豫。",
    pillLocked: "预览版 · 解锁查看真实分数",
    pillUnlocked: "完整报告已解锁",
    sec01: "信任硬指标扫描",
    sec01Intro:
      "为了简洁，下方只列出『弱』和『缺失』项 — 已通过的项目不显示。",
    sec01AllPass: "所有信任信号均已通过，没有可改进的地方。",
    sec02: "犹豫税",
    sec02Intro:
      "不同页面说不同的话会让顾客犹豫。以下是我们发现的冲突点，以及流失金额的计算模型。",
    sec03: "行动建议",
    pass: "通过",
    weak: "弱",
    missing: "缺失",
    conflicting: "冲突",
    paywallTitle: "解锁完整审计",
    paywallSub:
      "一次付费，永久查看。包括真实评分、每一处冲突、每一个多余字段，以及可直接交给开发的行动清单。",
    paywallButton: "立即解锁",
    paywallNotConfigured:
      "服务器尚未配置 Stripe 密钥。请在 backend/.env 中填入 STRIPE_SECRET_KEY 并重启后端，即可端到端完成解锁。",
    paidThanks: "付款成功 — 完整报告已解锁。",
    footer1: "把冲突修好，再跑一次审计，看分数往上走。",
    footer2:
      "Compare Your Website · 方向性审计，估算结果取决于你提供的输入。",
    visitors: "月均访问",
    aov: "客单价（美元）",
    issued: "签发",
    subject: "对象",
    locked: "已加锁",
    seeFull: "解锁完整报告",
    poweredBy: "Playwright 抓取 · 实时分析",
    modelMonthlyVisitors: "月访问量",
    modelReach: "进入结账/询价的访客比例",
    modelDrop: "因摩擦/犹豫流失的比例",
    modelAov: "客单价",
    modelTotal: "预估月损失",
    modelHonest: "仅为方向性估算。访问量与客单价为你提供的输入；两个比例使用行业基准，可自行覆盖。",
    enterUrlError: "请先填写要分析的网址。",
    serverError: "服务器无法完成本次审计，请稍后重试。",
    fetchedPages: "个页面已分析",
    of: "/",
  },
} as const;

export type DictKey = keyof (typeof dict)["en"];
