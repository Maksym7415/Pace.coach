import { Link } from "react-router-dom";

export function ComingSoonPage({ title }: { title: string }) {
  return (
    <div className="mx-auto max-w-lg space-y-3 py-12 text-center">
      <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
      <p className="text-sm text-slate-500">This section is coming soon.</p>
      <Link
        to="/today"
        className="inline-flex rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
      >
        Back to Today
      </Link>
    </div>
  );
}
