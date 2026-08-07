"use client";

import { useState } from "react";

import { RequirementForm } from "./RequirementForm";
import {
  explicitnessLabels,
  requirementTypeLabels,
  type RequirementInput,
  type RequirementItem,
} from "./types";


type RequirementListProps = {
  items: RequirementItem[];
  onUpdate: (item: RequirementItem, input: RequirementInput) => Promise<void>;
  onDelete: (item: RequirementItem) => void;
  readOnly?: boolean;
};


export function RequirementList({ items, onUpdate, onDelete, readOnly = false }: RequirementListProps) {
  const [editingId, setEditingId] = useState<string | null>(null);

  if (items.length === 0) {
    return <div className="list-state" role="status"><h3>还没有门槛条目</h3><p>从左侧岗位原文中找出一个独立条件，先录入第一条。</p></div>;
  }

  return (
    <ul className="requirement-list">
      {items.map((item) => (
        <li key={item.id}>
          {editingId === item.id ? (
            <RequirementForm
              mode="edit"
              initialValue={item}
              onCancel={() => setEditingId(null)}
              onSubmit={async (input) => {
                await onUpdate(item, input);
                setEditingId(null);
              }}
            />
          ) : (
            <article>
              <header className="requirement-heading">
                <div>
                  <div className="requirement-meta">
                    <span>{requirementTypeLabels[item.requirement_type]}</span>
                    <span>{explicitnessLabels[item.explicitness]}</span>
                    <span>{item.user_confirmed ? "已确认" : "待确认"}</span>
                    {item.confidence !== null ? (
                      <span>
                        {item.user_modified ? "人工修订" : "AI 提取"} · 置信度 {Math.round(Number(item.confidence) * 100)}%
                      </span>
                    ) : null}
                  </div>
                  <h3>{item.normalized_name}</h3>
                </div>
                {readOnly ? null : (
                  <div className="inline-actions">
                    <button type="button" className="secondary-button" aria-label={`编辑 ${item.normalized_name}`} onClick={() => setEditingId(item.id)}>编辑</button>
                    <button type="button" className="danger-button" aria-label={`删除 ${item.normalized_name}`} onClick={() => onDelete(item)}>删除</button>
                  </div>
                )}
              </header>
              <blockquote>{item.original_text}</blockquote>
            </article>
          )}
        </li>
      ))}
    </ul>
  );
}
