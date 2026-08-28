export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-gray-50">
      <div className="text-center space-y-6">
        <h1 className="text-4xl font-bold text-gray-900">RecoverIQ</h1>
        <p className="text-lg text-gray-600">
          Autonomous AI Revenue Recovery Agent
        </p>
        <div className="inline-flex items-center gap-2 rounded-full bg-green-100 px-4 py-2 text-sm font-medium text-green-800">
          <span className="h-2 w-2 rounded-full bg-green-500" />
          Frontend Running
        </div>
        <p className="text-sm text-gray-400">Phase 1 — Foundation</p>
      </div>
    </main>
  );
}
