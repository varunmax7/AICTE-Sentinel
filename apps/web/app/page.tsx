const API_URL = process.env.PUBLIC_API_URL ?? "http://localhost:8000";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-8 text-center">
      <h1 className="text-2xl font-semibold">AICTE Sentinel</h1>
      <p className="max-w-md text-sm text-neutral-500">
        Approval &amp; Compliance Portal — monorepo scaffold (Phase P0). Role portals, workflow
        engine, and AI features land in later phases per <code>IMPLEMENTATION.md</code>.
      </p>
      <p className="text-xs text-neutral-400">Core API: {API_URL}/api/v1/health</p>
    </main>
  );
}
