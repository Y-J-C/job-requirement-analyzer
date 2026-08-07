import { SummaryDashboard } from "@/features/summary/SummaryDashboard";


export default async function TargetRoleSummaryPage({
  params,
}: {
  params: Promise<{ roleId: string }>;
}) {
  const { roleId } = await params;
  return <SummaryDashboard roleId={roleId} />;
}
