import type { JobSortOption, JobStatusFilter } from "./jobPostingView";


type JobListControlsProps = {
  query: string;
  status: JobStatusFilter;
  sort: JobSortOption;
  resultCount: number;
  totalCount: number;
  onQueryChange: (value: string) => void;
  onStatusChange: (value: JobStatusFilter) => void;
  onSortChange: (value: JobSortOption) => void;
  onReset: () => void;
};


export function JobListControls({
  query,
  status,
  sort,
  resultCount,
  totalCount,
  onQueryChange,
  onStatusChange,
  onSortChange,
  onReset,
}: JobListControlsProps) {
  const hasCustomView = Boolean(query.trim()) || status !== "all" || sort !== "newest";
  return (
    <div className="job-list-controls" aria-label="岗位列表筛选">
      <div className="field job-search-field">
        <label htmlFor="job-search">搜索岗位</label>
        <input
          id="job-search"
          type="search"
          value={query}
          placeholder="公司、岗位或城市"
          onChange={(event) => onQueryChange(event.currentTarget.value)}
        />
      </div>
      <div className="field">
        <label htmlFor="job-status-filter">岗位状态</label>
        <select
          id="job-status-filter"
          value={status}
          onChange={(event) => onStatusChange(event.currentTarget.value as JobStatusFilter)}
        >
          <option value="all">全部状态</option>
          <option value="processing">处理中</option>
          <option value="review">待审核</option>
          <option value="confirmed">已确认</option>
          <option value="failed">处理失败</option>
        </select>
      </div>
      <div className="field">
        <label htmlFor="job-sort">排序方式</label>
        <select
          id="job-sort"
          value={sort}
          onChange={(event) => onSortChange(event.currentTarget.value as JobSortOption)}
        >
          <option value="newest">最新录入</option>
          <option value="oldest">最早录入</option>
          <option value="company">公司名称</option>
        </select>
      </div>
      <div className="job-view-summary" aria-live="polite">
        <span>显示 {resultCount} / {totalCount} 个岗位</span>
        <button type="button" onClick={onReset} disabled={!hasCustomView}>重置列表</button>
      </div>
    </div>
  );
}
