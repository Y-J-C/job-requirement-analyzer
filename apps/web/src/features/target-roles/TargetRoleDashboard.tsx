"use client";

import { PlusIcon } from "@phosphor-icons/react/dist/csr/Plus";
import { useEffect, useState } from "react";

import { createTargetRole, fetchTargetRoles } from "./api";
import { TargetRoleForm } from "./TargetRoleForm";
import { TargetRoleList } from "./TargetRoleList";
import type { CreateTargetRoleInput, TargetRole } from "./types";


export function TargetRoleDashboard() {
  const [roles, setRoles] = useState<TargetRole[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isCreateOpen, setIsCreateOpen] = useState(false);

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

  useEffect(() => {
    function openCreateFromHash() {
      if (window.location.hash === "#new-direction") {
        setIsCreateOpen(true);
      }
    }

    function openCreate() {
      setIsCreateOpen(true);
    }

    openCreateFromHash();
    window.addEventListener("hashchange", openCreateFromHash);
    window.addEventListener("open-new-direction", openCreate);
    return () => {
      window.removeEventListener("hashchange", openCreateFromHash);
      window.removeEventListener("open-new-direction", openCreate);
    };
  }, []);

  async function handleCreate(input: CreateTargetRoleInput) {
    const createdRole = await createTargetRole(input);
    setRoles((currentRoles) => [createdRole, ...currentRoles]);
    setIsCreateOpen(false);
  }

  return (
    <section className="direction-dashboard" aria-label="目标岗位方向">
      <section className="direction-create" id="new-direction" aria-label="新建方向">
        <button
          className="primary-create-button"
          type="button"
          aria-expanded={isCreateOpen}
          aria-controls="direction-create-form"
          onClick={() => setIsCreateOpen((current) => !current)}
        >
          {!isCreateOpen ? <PlusIcon aria-hidden="true" size={22} weight="bold" /> : null}
          {isCreateOpen ? "收起" : "新建方向"}
        </button>
        {isCreateOpen ? (
          <div id="direction-create-form">
            <TargetRoleForm onCreate={handleCreate} />
          </div>
        ) : null}
      </section>

      <section className="direction-list" id="directions" aria-labelledby="target-role-heading">
        <h2 id="target-role-heading">已有方向</h2>
        <div className="role-list-columns" aria-hidden="true">
          <span>方向名称</span>
          <span>招聘阶段</span>
          <span>包含岗位</span>
          <span />
        </div>
          <TargetRoleList
            roles={roles}
            isLoading={isLoading}
            loadError={loadError}
            onRetry={() => void loadRoles()}
          />
      </section>
    </section>
  );
}
