import Link from "next/link";

import { recruitmentStageLabels, type TargetRole } from "./types";


type TargetRoleListProps = {
  roles: TargetRole[];
  isLoading: boolean;
  loadError: string | null;
  onRetry: () => void;
};


export function TargetRoleList({ roles, isLoading, loadError, onRetry }: TargetRoleListProps) {
  if (isLoading) {
    return <p className="list-state" aria-busy="true">正在加载目标方向…</p>;
  }

  if (loadError) {
    return (
      <div className="list-state error-state" role="alert">
        <p>{loadError}</p>
        <button className="secondary-button" type="button" onClick={onRetry}>
          重新加载
        </button>
      </div>
    );
  }

  if (roles.length === 0) {
    return (
      <div className="list-state" role="status">
        <h3>还没有目标岗位方向</h3>
        <p>先创建一个方向，再向其中添加具体招聘岗位。</p>
      </div>
    );
  }

  return (
    <ul className="role-list">
      {roles.map((role) => (
        <li key={role.id}>
          <div>
            <p className="role-stage">{recruitmentStageLabels[role.recruitment_stage]}</p>
            <h3><Link href={`/target-roles/${role.id}`}>{role.name}</Link></h3>
            {role.description ? <p>{role.description}</p> : null}
          </div>
          <span className="job-count">{role.job_count} 个岗位</span>
        </li>
      ))}
    </ul>
  );
}
