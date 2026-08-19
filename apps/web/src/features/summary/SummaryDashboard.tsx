"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { PageState } from "@/components/PageState";
import {
  requirementTypeLabels,
  type RequirementType,
} from "@/features/requirements/types";

import { fetchTargetRoleSummary } from "./api";
import { SummaryExportButton } from "./SummaryExportButton";
import { SummaryList } from "./SummaryList";
import type { TargetRoleSummary } from "./types";


type SummaryFilter = RequirementType | "all";


export function SummaryDashboard({ roleId }: { roleId: string }) {
  const [filter, setFilter] = useState<SummaryFilter>("all");
  const [summary, setSummary] = useState<TargetRoleSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isCurrent = true;
    fetchTargetRoleSummary(roleId, filter)
      .then((loaded) => {
        if (isCurrent) setSummary(loaded);
      })
      .catch(() => {
        if (isCurrent) setError("确认汇总加载失败，请返回后重试。");
      })
      .finally(() => {
        if (isCurrent) setIsLoading(false);
      });
    return () => {
      isCurrent = false;
    };
  }, [filter, roleId]);

  function handleFilterChange(nextFilter: SummaryFilter) {
    setIsLoading(true);
    setError(null);
    setFilter(nextFilter);
  }

  if (isLoading) return <PageState title="正在计算确认汇总" message="正在按岗位去重并整理已确认要求…" />;
  if (error || !summary) return <PageState kind="error" title="确认汇总加载失败" message={error ?? "目标方向不存在。"} />;

  const emptyMessage = summary.confirmed_job_count === 0
    ? "还没有已确认岗位"
    : filter === "all"
      ? "已确认岗位暂时没有可汇总要求"
      : "这个分类下还没有已确认要求";

  return (
    <main className="shell summary-page">
      <nav className="page-nav" aria-label="页面导航">
        <Link className="back-link" href={`/target-roles/${roleId}`}>返回岗位</Link>
        <span>已确认数据</span>
      </nav>
      <header className="detail-header">
        <p className="eyebrow">确定性事实汇总</p>
        <h1>{summary.target_role_name} · 确认汇总</h1>
        <p>只统计已确认岗位；覆盖率按岗位去重，不代表市场硬门槛。</p>
      </header>

      <section className="summary-metrics" aria-label="样本概况">
        <p><strong>{summary.sample_job_count}</strong><span>个全部样本</span></p>
        <p><strong>{summary.confirmed_job_count}</strong><span>个已确认岗位</span></p>
        <p className="sample-notice">{summary.sample_size_notice}</p>
      </section>

      <section className="summary-results" aria-labelledby="summary-results-heading">
        <div className="summary-toolbar">
          <div>
            <h2 id="summary-results-heading">要求覆盖率</h2>
            <p>同名条件在不同要求类型下分别统计。</p>
          </div>
          <div className="summary-toolbar-actions">
            <SummaryExportButton summary={summary} reportName="确认汇总" />
            <div className="field filter-field">
              <label htmlFor="requirement-type-filter">要求类型筛选</label>
              <select
                id="requirement-type-filter"
                value={filter}
                onChange={(event) => handleFilterChange(event.target.value as SummaryFilter)}
              >
                <option value="all">全部类型</option>
                {Object.entries(requirementTypeLabels).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {summary.items.length === 0 ? (
          <div className="list-state" role="status">
            <h3>{emptyMessage}</h3>
            <p>{summary.confirmed_job_count === 0 ? "先完成至少一个岗位的门槛审核与整份确认。" : "切换其他分类，或回到岗位审核页补充已确认要求。"}</p>
          </div>
        ) : <SummaryList items={summary.items} />}
      </section>
    </main>
  );
}
