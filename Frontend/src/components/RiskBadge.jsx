const RISK_STYLES = {
  "LOW RISK": "bg-green-100 text-green-800 border-green-300",
  "MEDIUM RISK": "bg-yellow-100 text-yellow-800 border-yellow-300",
  "HIGH RISK": "bg-orange-100 text-orange-800 border-orange-300",
  "VERY HIGH RISK": "bg-red-100 text-red-800 border-red-300",
};

export default function RiskBadge({ label }) {
  const style = RISK_STYLES[label] || "bg-gray-100 text-gray-800 border-gray-300";
  return (
    <span className={`inline-block px-3 py-1 rounded-full text-sm font-semibold border ${style}`}>
      {label}
    </span>
  );
}