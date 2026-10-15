// Inline SVGs. All are decorative (aria-hidden) because a text label always
// accompanies them — risk is never communicated by icon or color alone.

interface P {
  size?: number;
  color?: string;
}

export function BeaconMark({ size = 26 }: P) {
  // A small lighthouse beaming light — the brand mark.
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M12 2.5l1.6 3.2M12 2.5L10.4 5.7"
        stroke="#f5a623"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
      <path d="M9 9h6l1 11H8l1-11z" fill="#fbfaf7" />
      <path d="M9.5 13h5M9.2 16h5.6" stroke="#0b1b2b" strokeWidth="1.3" />
      <path d="M9 9h6l-.5-2.2h-5L9 9z" fill="#f5a623" />
      <path
        d="M16 7.2l3.4-1.2M16 9.4l3.4 1M8 7.2L4.6 6M8 9.4L4.6 10.4"
        stroke="#f5a623"
        strokeWidth="1.3"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function ShieldCheck({ size = 32 }: P) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M12 2.5l7 2.5v5.5c0 4.6-3 8-7 9.5-4-1.5-7-4.9-7-9.5V5l7-2.5z"
        fill="rgba(255,255,255,0.18)"
        stroke="#fff"
        strokeWidth="1.4"
      />
      <path
        d="M8.5 12.2l2.3 2.3 4.4-4.6"
        fill="none"
        stroke="#fff"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function AlertTriangle({ size = 32 }: P) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M12 3.2l9 15.8H3L12 3.2z"
        fill="rgba(255,255,255,0.18)"
        stroke="#fff"
        strokeWidth="1.4"
        strokeLinejoin="round"
      />
      <path d="M12 9v4.5" stroke="#fff" strokeWidth="2" strokeLinecap="round" />
      <circle cx="12" cy="16.4" r="1.1" fill="#fff" />
    </svg>
  );
}

export function OctagonAlert({ size = 32 }: P) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M8 3h8l5 5v8l-5 5H8l-5-5V8l5-5z"
        fill="rgba(255,255,255,0.18)"
        stroke="#fff"
        strokeWidth="1.4"
        strokeLinejoin="round"
      />
      <path d="M12 7.5v5.5" stroke="#fff" strokeWidth="2" strokeLinecap="round" />
      <circle cx="12" cy="16.2" r="1.15" fill="#fff" />
    </svg>
  );
}

export function Dot({ color = "#46586a", size = 12 }: P) {
  return (
    <svg width={size} height={size} viewBox="0 0 12 12" aria-hidden="true">
      <circle cx="6" cy="6" r="5" fill={color} />
    </svg>
  );
}

export function MicIcon({ size = 48 }: P) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
      <rect x="9" y="2.5" width="6" height="11" rx="3" fill="#0b1b2b" />
      <path
        d="M5.5 11a6.5 6.5 0 0013 0M12 17.5V21M8.5 21h7"
        fill="none"
        stroke="#0b1b2b"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  );
}
