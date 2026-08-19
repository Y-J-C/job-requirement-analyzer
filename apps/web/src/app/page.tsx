import { TargetRoleDashboard } from "@/features/target-roles/TargetRoleDashboard";


export default function Home() {
  return (
    <main className="shell home-shell">
      <header className="direction-page-header">
        <h1>方向总览</h1>
      </header>

      <TargetRoleDashboard />
    </main>
  );
}
