import { CaretRightIcon } from "@phosphor-icons/react/dist/csr/CaretRight";
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
    return <p className="list-state" role="status">暂无方向</p>;
  }

  return (
    <ul className="role-list">
      {roles.map((role) => (
        <li key={role.id}>
          <Link className="role-row" href={`/target-roles/${role.id}`}>
            <h3>{role.name}</h3>
            <span className="role-stage">{recruitmentStageLabels[role.recruitment_stage]}</span>
            <span className="job-count">{role.job_count} 个岗位</span>
            <CaretRightIcon className="role-row-caret" aria-hidden="true" size={20} />
          </Link>
        </li>
      ))}
    </ul>
  );
}
