import { RequirementReviewDashboard } from "@/features/requirements/RequirementReviewDashboard";


export default async function RequirementReviewPage({
  params,
}: {
  params: Promise<{ jobId: string }>;
}) {
  const { jobId } = await params;
  return <RequirementReviewDashboard jobId={jobId} />;
}
