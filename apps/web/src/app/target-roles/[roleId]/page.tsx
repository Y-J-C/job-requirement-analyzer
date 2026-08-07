import { JobPostingDashboard } from "@/features/job-postings/JobPostingDashboard";


type TargetRolePageProps = {
  params: Promise<{ roleId: string }>;
};


export default async function TargetRolePage({ params }: TargetRolePageProps) {
  const { roleId } = await params;
  return <JobPostingDashboard roleId={roleId} />;
}

