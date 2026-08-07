"use client";

import { useEffect, useState } from "react";

import { createTargetRole, fetchTargetRoles } from "./api";
import { TargetRoleForm } from "./TargetRoleForm";
import { TargetRoleList } from "./TargetRoleList";
import type { CreateTargetRoleInput, TargetRole } from "./types";


export function TargetRoleDashboard() {
  const [roles, setRoles] = useState<TargetRole[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  async function loadRoles() {
    setIsLoading(true);
    setLoadError(null);
    try {
      const response = await fetchTargetRoles();
      setRoles(response.items);
    } catch {
      setLoadError("目标方向加载失败，请重试。");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    let isCurrent = true;

    fetchTargetRoles()
      .then((response) => {
        if (isCurrent) {
          setRoles(response.items);
        }
      })
      .catch(() => {
        if (isCurrent) {
          setLoadError("目标方向加载失败，请重试。");
        }
      })
      .finally(() => {
        if (isCurrent) {
          setIsLoading(false);
        }
      });

    return () => {
      isCurrent = false;
    };
  }, []);

  async function handleCreate(input: CreateTargetRoleInput) {
    const createdRole = await createTargetRole(input);
    setRoles((currentRoles) => [createdRole, ...currentRoles]);
  }

  return (
    <section className="workspace" aria-labelledby="target-role-heading">
      <div className="workspace-heading">
        <div>
          <p className="section-label">目标岗位方向</p>
          <h2 id="target-role-heading">从一个清晰方向开始</h2>
        </div>
        <p>同一方向只收集职责与能力结构相近的岗位，避免汇总结果失真。</p>
      </div>

      <TargetRoleForm onCreate={handleCreate} />

      <div className="list-heading">
        <h2>已创建的方向</h2>
        <span>{roles.length} 个</span>
      </div>
      <TargetRoleList
        roles={roles}
        isLoading={isLoading}
        loadError={loadError}
        onRetry={() => void loadRoles()}
      />
    </section>
  );
}
