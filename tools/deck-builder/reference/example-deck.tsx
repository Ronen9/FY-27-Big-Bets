// REFERENCE DECK FOR THE LLM — fictional companies / fictional numbers.
// This file is read by tools/deck-builder/server.py at request time and
// embedded in the system prompt as the "gold-standard" example the model
// must mirror for density, atom design, and per-account bespoke pages.
//
// All companies, people, products, and dollar figures below are FICTIONAL.
// If you copy this for your own deck, treat it as a structural template,
// not as factual content.

import type { DesignSystem, Page, SlideMeta } from '@open-slide/core';

export const design: DesignSystem = {
  palette: { bg: '#080d1a', text: '#f0f4ff', accent: '#7c3aed' },
  fonts: {
    display: 'system-ui, -apple-system, "Segoe UI", sans-serif',
    body: 'system-ui, -apple-system, "Segoe UI", sans-serif',
  },
  typeScale: { hero: 144, body: 36 },
  radius: 16,
};

const contosoColor   = '#06b6d4';
const northwindColor = '#f59e0b';
const adventureColor = '#10b981';
const muted          = '#6b7faa';
const cardBg         = '#0f1628';
const H              = 140;
const V              = 120;

const fill = { width: '100%', height: '100%', overflow: 'hidden', fontFamily: 'var(--osd-font-body)' } as const;

// ── Shared atoms ───────────────────────────────────────────────────────────

const Tag = ({ text, color }: { text: string; color: string }) => (
  <div style={{
    display: 'inline-block', padding: '7px 20px', borderRadius: 40,
    background: `${color}22`, color, fontSize: 20, fontWeight: 800,
    letterSpacing: '0.15em', textTransform: 'uppercase', marginBottom: 20,
  }}>
    {text}
  </div>
);

const Chip = ({ label, color }: { label: string; color: string }) => (
  <div style={{
    padding: '14px 36px', borderRadius: 50, border: `2px solid ${color}`,
    color, fontSize: 28, fontWeight: 700, whiteSpace: 'nowrap',
  }}>
    {label}
  </div>
);

const Stat = ({ value, label, color }: { value: string; label: string; color: string }) => (
  <div style={{ flex: 1, background: cardBg, borderRadius: 20, padding: '40px', borderTop: `4px solid ${color}` }}>
    <div style={{ fontSize: 72, fontWeight: 900, color, lineHeight: 1, marginBottom: 14 }}>{value}</div>
    <div style={{ fontSize: 24, color: muted, lineHeight: 1.4 }}>{label}</div>
  </div>
);

const Bullet = ({ text, color }: { text: string; color: string }) => (
  <div style={{
    fontSize: 22, color: 'var(--osd-text)', lineHeight: 1.4,
    paddingLeft: 14, borderLeft: `3px solid ${color}55`,
  }}>
    {text}
  </div>
);

const PlayCard = ({ title, color, b1, b2, b3 }: {
  title: string; color: string; b1: string; b2: string; b3: string;
}) => (
  <div style={{
    flex: 1, background: cardBg, borderRadius: 20, padding: '32px 28px',
    borderLeft: `4px solid ${color}`, display: 'flex', flexDirection: 'column', gap: 18,
  }}>
    <div style={{ fontSize: 30, fontWeight: 800, color, lineHeight: 1.2 }}>{title}</div>
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <Bullet text={b1} color={color} />
      <Bullet text={b2} color={color} />
      <Bullet text={b3} color={color} />
    </div>
  </div>
);

const AccountRow = ({ name, pipeline, signal, color }: {
  name: string; pipeline: string; signal: string; color: string;
}) => (
  <div style={{
    display: 'flex', alignItems: 'center', gap: 36,
    padding: '24px 40px', background: cardBg, borderRadius: 16, borderLeft: `4px solid ${color}`,
  }}>
    <div style={{ fontSize: 28, fontWeight: 800, color, minWidth: 320 }}>{name}</div>
    <div style={{ fontSize: 48, fontWeight: 900, color: 'var(--osd-text)', minWidth: 160 }}>{pipeline}</div>
    <div style={{ fontSize: 22, color: muted, flex: 1 }}>{signal}</div>
  </div>
);

const PipeCard = ({ account, amount, desc, status, color }: {
  account: string; amount: string; desc: string; status: string; color: string;
}) => (
  <div style={{ flex: 1, background: cardBg, borderRadius: 20, padding: '36px 40px', borderTop: `4px solid ${color}` }}>
    <div style={{ fontSize: 20, color, fontWeight: 800, letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 14 }}>{account}</div>
    <div style={{ fontSize: 60, fontWeight: 900, color: 'var(--osd-text)', lineHeight: 1, marginBottom: 12 }}>{amount}</div>
    <div style={{ fontSize: 22, color: muted, marginBottom: 16 }}>{desc}</div>
    <div style={{ fontSize: 20, color, fontWeight: 700 }}>{status}</div>
  </div>
);

const Step = ({ num, title, detail, color }: {
  num: string; title: string; detail: string; color: string;
}) => (
  <div style={{ display: 'flex', alignItems: 'flex-start', gap: 32 }}>
    <div style={{ fontSize: 48, fontWeight: 900, color, lineHeight: 1, minWidth: 56 }}>{num}</div>
    <div>
      <div style={{ fontSize: 32, fontWeight: 800, color: 'var(--osd-text)', lineHeight: 1.2, marginBottom: 8 }}>{title}</div>
      <div style={{ fontSize: 22, color: muted, lineHeight: 1.45 }}>{detail}</div>
    </div>
  </div>
);

// ── Pages ─────────────────────────────────────────────────────────────────

// Page 1 — Cover
const Cover: Page = () => (
  <div style={{
    ...fill, background: 'var(--osd-bg)', color: 'var(--osd-text)',
    display: 'flex', flexDirection: 'column', justifyContent: 'center',
    padding: `0 ${H}px`, position: 'relative',
  }}>
    <div style={{
      position: 'absolute', top: -320, right: -200, width: 860, height: 860,
      borderRadius: '50%', background: 'radial-gradient(circle, rgba(124,58,237,0.2) 0%, transparent 65%)',
      pointerEvents: 'none',
    }} />
    <div style={{
      position: 'absolute', bottom: -160, right: 280, width: 520, height: 520,
      borderRadius: '50%', background: 'radial-gradient(circle, rgba(6,182,212,0.1) 0%, transparent 65%)',
      pointerEvents: 'none',
    }} />

    <div style={{
      fontSize: 22, fontWeight: 800, color: 'var(--osd-accent)',
      letterSpacing: '0.22em', textTransform: 'uppercase', marginBottom: 32,
    }}>
      Acme Region · CRM Sales Play · FY26 Q4
    </div>
    <h1 style={{
      fontFamily: 'var(--osd-font-display)', fontSize: 144, fontWeight: 900,
      margin: '0 0 28px', lineHeight: 1.0, letterSpacing: '-0.02em',
    }}>
      3 Accounts.<br />One Play.
    </h1>
    <p style={{ fontSize: 36, color: muted, margin: '0 0 56px', maxWidth: 1100, lineHeight: 1.45 }}>
      Why our CRM platform is the right move for Contoso, Northwind &amp; Adventure — and how we close it.
    </p>
    <div style={{ display: 'flex', gap: 20 }}>
      <Chip label="Contoso Health" color={contosoColor} />
      <Chip label="Northwind Pay" color={northwindColor} />
      <Chip label="Adventure Pharma" color={adventureColor} />
    </div>
  </div>
);

// Page 2 — The Opportunity
const ContextPage: Page = () => (
  <div style={{
    ...fill, background: 'var(--osd-bg)', color: 'var(--osd-text)',
    padding: `${V}px ${H}px`, display: 'flex', flexDirection: 'column',
  }}>
    <Tag text="The Opportunity" color="var(--osd-accent)" />
    <h2 style={{
      fontFamily: 'var(--osd-font-display)', fontSize: 64, fontWeight: 900,
      margin: '0 0 14px', lineHeight: 1.1, letterSpacing: '-0.01em',
    }}>
      $1.32M qualified pipeline.<br />Q4 closes in weeks.
    </h2>
    <p style={{ fontSize: 28, color: muted, margin: '0 0 36px', lineHeight: 1.4 }}>
      Three enterprise accounts, all on existing agreements, primed for a CRM conversation.
    </p>
    <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
      <AccountRow
        name="Contoso Health"
        pipeline="$720K"
        signal="Region's #1 HMO · Active call-center modernization pipeline"
        color={contosoColor}
      />
      <AccountRow
        name="Northwind Pay"
        pipeline="$430K"
        signal="Global fintech · Expanded cloud deal with us last quarter"
        color={northwindColor}
      />
      <AccountRow
        name="Adventure Pharma"
        pipeline="$170K"
        signal="Global pharma · EA renewal at risk → perfect time to expand"
        color={adventureColor}
      />
    </div>
  </div>
);

// Page 3 — Contoso: Who They Are
const ContosoIntro: Page = () => (
  <div style={{
    ...fill, background: 'var(--osd-bg)', color: 'var(--osd-text)',
    padding: `${V}px ${H}px`, display: 'flex', flexDirection: 'column',
  }}>
    <Tag text="Account 1 · Contoso Health" color={contosoColor} />
    <h2 style={{
      fontFamily: 'var(--osd-font-display)', fontSize: 60, fontWeight: 900,
      margin: '0 0 14px', lineHeight: 1.1,
    }}>
      The region's largest HMO.<br />A digital transformation machine.
    </h2>
    <p style={{ fontSize: 28, color: muted, margin: '0 0 36px', lineHeight: 1.4 }}>
      4.5M insured members. 12 years of AI investment. Actively hiring CRM and digital talent right now.
    </p>
    <div style={{ display: 'flex', gap: 22 }}>
      <Stat value="4.5M" label="Insured members" color={contosoColor} />
      <Stat value="1,200" label="Clinics in the network" color={contosoColor} />
      <Stat value="12 yrs" label="Continuous AI investment" color={contosoColor} />
    </div>
  </div>
);

// Page 4 — Contoso: Our Play
const ContosoPlay: Page = () => (
  <div style={{
    ...fill, background: 'var(--osd-bg)', color: 'var(--osd-text)',
    padding: `${V}px ${H}px`, display: 'flex', flexDirection: 'column',
  }}>
    <Tag text="Our Play · Contoso" color={contosoColor} />
    <h2 style={{
      fontFamily: 'var(--osd-font-display)', fontSize: 56, fontWeight: 900,
      margin: '0 0 10px', lineHeight: 1.1,
    }}>
      Where our CRM creates real value.
    </h2>
    <div style={{
      display: 'inline-block', padding: '8px 24px', borderRadius: 40,
      background: `${contosoColor}22`, color: contosoColor,
      fontSize: 20, fontWeight: 700, marginBottom: 26,
    }}>
      $720K Qualified Pipeline · Customer Service + Insights + RTM
    </div>
    <div style={{ display: 'flex', gap: 22, flex: 1 }}>
      <PlayCard
        title="Customer Service"
        color={contosoColor}
        b1="Unify patient calls across 1,200 clinics"
        b2="AI-assisted agents cut handle time"
        b3="Single view of every patient interaction"
      />
      <PlayCard
        title="Customer Insights RT"
        color={contosoColor}
        b1="Segment 6M patient records in real time"
        b2="Proactive outreach for high-risk members"
        b3="Connect data: clinics, hospitals, home"
      />
      <PlayCard
        title="Real-Time Marketing"
        color={contosoColor}
        b1="Regional health campaigns at digital scale"
        b2="Replace manual phone campaigns"
        b3="Pandemic proved the need — now make it permanent"
      />
    </div>
  </div>
);

// Page 5 — Northwind: Who They Are
const NorthwindIntro: Page = () => (
  <div style={{
    ...fill, background: 'var(--osd-bg)', color: 'var(--osd-text)',
    padding: `${V}px ${H}px`, display: 'flex', flexDirection: 'column',
  }}>
    <Tag text="Account 2 · Northwind Pay" color={northwindColor} />
    <h2 style={{
      fontFamily: 'var(--osd-font-display)', fontSize: 60, fontWeight: 900,
      margin: '0 0 14px', lineHeight: 1.1,
    }}>
      Global fintech.<br />Already inside our ecosystem.
    </h2>
    <p style={{ fontSize: 28, color: muted, margin: '0 0 36px', lineHeight: 1.4 }}>
      $900B+ annual payment volume. Publicly traded. Last quarter they expanded their cloud partnership with us — we are already in the room.
    </p>
    <div style={{ display: 'flex', gap: 22 }}>
      <Stat value="$900B+" label="Annual payment volume processed" color={northwindColor} />
      <Stat value="180+" label="Markets served worldwide" color={northwindColor} />
      <Stat value="600+" label="Supported payment methods" color={northwindColor} />
    </div>
  </div>
);

// Page 6 — Northwind: Our Play
const NorthwindPlay: Page = () => (
  <div style={{
    ...fill, background: 'var(--osd-bg)', color: 'var(--osd-text)',
    padding: `${V}px ${H}px`, display: 'flex', flexDirection: 'column',
  }}>
    <Tag text="Our Play · Northwind" color={northwindColor} />
    <h2 style={{
      fontFamily: 'var(--osd-font-display)', fontSize: 56, fontWeight: 900,
      margin: '0 0 10px', lineHeight: 1.1,
    }}>
      Turn the cloud deal into a CRM conversation.
    </h2>
    <div style={{
      display: 'inline-block', padding: '8px 24px', borderRadius: 40,
      background: `${northwindColor}22`, color: northwindColor,
      fontSize: 20, fontWeight: 700, marginBottom: 26,
    }}>
      $430K Qualified Pipeline · Customer Service + Sales Hub
    </div>
    <div style={{ display: 'flex', gap: 22, flex: 1 }}>
      <PlayCard
        title="Sales Hub"
        color={northwindColor}
        b1="Manage sales teams across 180+ markets"
        b2="Unified pipeline: HQ to every region"
        b3="AI copilot boosts rep productivity"
      />
      <PlayCard
        title="Customer Service"
        color={northwindColor}
        b1="Centralize merchant support globally"
        b2="AI case routing reduces escalations"
        b3="Single CRM for every merchant relationship"
      />
      <PlayCard
        title="The Leverage"
        color={northwindColor}
        b1="Cloud partnership = open door, use it now"
        b2="CRM APIs run natively on their cloud stack"
        b3="No new vendor — one trusted partner"
      />
    </div>
  </div>
);

// Page 7 — Adventure: Who They Are
const AdventureIntro: Page = () => (
  <div style={{
    ...fill, background: 'var(--osd-bg)', color: 'var(--osd-text)',
    padding: `${V}px ${H}px`, display: 'flex', flexDirection: 'column',
  }}>
    <Tag text="Account 3 · Adventure Pharma" color={adventureColor} />
    <h2 style={{
      fontFamily: 'var(--osd-font-display)', fontSize: 56, fontWeight: 900,
      margin: '0 0 14px', lineHeight: 1.1,
    }}>
      Global pharma on a "Pivot to Growth."<br />They need a CRM backbone.
    </h2>
    <p style={{ fontSize: 28, color: muted, margin: '0 0 36px', lineHeight: 1.4 }}>
      35,000 employees across 50+ markets. Launched an open innovation platform last quarter — actively seeking tech co-creation.
    </p>
    <div style={{ display: 'flex', gap: 22 }}>
      <Stat value="35K" label="Employees across 50+ markets" color={adventureColor} />
      <Stat value="100+" label="Years delivering medicines globally" color={adventureColor} />
      <Stat value="Launched" label="Open innovation platform last quarter" color={adventureColor} />
    </div>
  </div>
);

// Page 8 — Adventure: Our Play
const AdventurePlay: Page = () => (
  <div style={{
    ...fill, background: 'var(--osd-bg)', color: 'var(--osd-text)',
    padding: `${V}px ${H}px`, display: 'flex', flexDirection: 'column',
  }}>
    <Tag text="Our Play · Adventure" color={adventureColor} />
    <h2 style={{
      fontFamily: 'var(--osd-font-display)', fontSize: 56, fontWeight: 900,
      margin: '0 0 10px', lineHeight: 1.1,
    }}>
      Save the renewal. Then expand.
    </h2>
    <div style={{
      display: 'inline-block', padding: '8px 24px', borderRadius: 40,
      background: `${adventureColor}22`, color: adventureColor,
      fontSize: 20, fontWeight: 700, marginBottom: 26,
    }}>
      $170K EA Renewal At Risk → Expand to Customer Insights + Marketing Automation
    </div>
    <div style={{ display: 'flex', gap: 22, flex: 1 }}>
      <PlayCard
        title="Customer Insights RT"
        color={adventureColor}
        b1="HCP segmentation with AI-driven analytics"
        b2="Patient program targeting at global scale"
        b3="Builds on their existing AI strategy"
      />
      <PlayCard
        title="Real-Time Marketing"
        color={adventureColor}
        b1="Digital-first HCP engagement campaigns"
        b2="Automate field outreach across 50+ markets"
        b3="Customer is already moving to a digital-first model"
      />
      <PlayCard
        title="The Unlock"
        color={adventureColor}
        b1="Renewal convo = C-suite access"
        b2="Their innovation platform = co-creation opportunity"
        b3="Position our CRM as the commercial backbone"
      />
    </div>
  </div>
);

// Page 9 — Pipeline Numbers
const PipelineNumbers: Page = () => (
  <div style={{
    ...fill, background: 'var(--osd-bg)', color: 'var(--osd-text)',
    padding: `${V}px ${H}px`, display: 'flex', flexDirection: 'column',
  }}>
    <Tag text="The Numbers" color="var(--osd-accent)" />
    <h2 style={{
      fontFamily: 'var(--osd-font-display)', fontSize: 56, fontWeight: 900,
      margin: '0 0 36px', lineHeight: 1.1,
    }}>
      The opportunity in one view.
    </h2>
    <div style={{ display: 'flex', gap: 22, marginBottom: 24 }}>
      <PipeCard
        account="Contoso Health"
        amount="$720K"
        desc="Customer Service · Insights · RTM"
        status="Upside + Committed"
        color={contosoColor}
      />
      <PipeCard
        account="Northwind Pay"
        amount="$430K"
        desc="Customer Service · Sales Hub"
        status="Upside"
        color={northwindColor}
      />
      <PipeCard
        account="Adventure Pharma"
        amount="$170K"
        desc="EA Renewal + CRM Expansion"
        status="At Risk → Save + Expand"
        color={adventureColor}
      />
    </div>
    <div style={{
      background: 'rgba(124,58,237,0.1)', borderRadius: 20, padding: '28px 40px',
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      border: '1px solid rgba(124,58,237,0.3)',
    }}>
      <div style={{ fontSize: 26, color: muted, fontWeight: 600 }}>Combined Qualified Pipeline</div>
      <div style={{ fontSize: 60, fontWeight: 900, color: 'var(--osd-accent)' }}>$1.32M</div>
      <div style={{ fontSize: 22, color: muted, textAlign: 'right' }}>All in our region<br />All in the AI Business motion</div>
    </div>
  </div>
);

// Page 10 — Next Steps
const NextSteps: Page = () => (
  <div style={{
    ...fill, background: 'var(--osd-bg)', color: 'var(--osd-text)',
    padding: `${V}px ${H}px`, display: 'flex', flexDirection: 'column',
  }}>
    <Tag text="Next Steps" color="var(--osd-accent)" />
    <h2 style={{
      fontFamily: 'var(--osd-font-display)', fontSize: 64, fontWeight: 900,
      margin: '0 0 40px', lineHeight: 1.1,
    }}>
      What we do this week.
    </h2>
    <div style={{ display: 'flex', flexDirection: 'column', gap: 32 }}>
      <Step
        num="01"
        color={contosoColor}
        title="Contoso — Book the exec alignment"
        detail="Reach VP Digital & Technology. Anchor on the modernization Phase A and call-center pipeline. Pipeline: $400K + $230K."
      />
      <Step
        num="02"
        color={northwindColor}
        title="Northwind — Leverage the cloud deal"
        detail="Use last quarter's cloud partnership as the opener. Push Customer Service ($360K Upside). Owner: account team A."
      />
      <Step
        num="03"
        color={adventureColor}
        title="Adventure — Renewal save, then expand"
        detail="Schedule save call with the account exec. Frame Customer Insights as the next step inside the 'Pivot to Growth' strategy."
      />
    </div>
  </div>
);

export const meta: SlideMeta = { title: 'Example CRM Sales Play — 3 Accounts (FICTIONAL)' };
export default [
  Cover,
  ContextPage,
  ContosoIntro,
  ContosoPlay,
  NorthwindIntro,
  NorthwindPlay,
  AdventureIntro,
  AdventurePlay,
  PipelineNumbers,
  NextSteps,
] satisfies Page[];
