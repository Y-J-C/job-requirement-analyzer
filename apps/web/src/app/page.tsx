import { TargetRoleDashboard } from "@/features/target-roles/TargetRoleDashboard";


const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";


export default function Home() {
  return (
    <main className="shell">
      <header className="masthead">
        <div className="masthead-copy">
          <p className="eyebrow">从岗位原文到可核验结论</p>
          <h1>岗位门槛分析系统</h1>
          <p className="lede">
            把零散招聘信息整理成有依据、经确认、可比较的岗位要求。
          </p>
        </div>
        <ol className="workflow-steps" aria-label="使用流程">
          <li><span>01</span><strong>创建方向</strong><small>划定样本边界</small></li>
          <li><span>02</span><strong>录入岗位</strong><small>文本、文档或图片</small></li>
          <li><span>03</span><strong>人工审核</strong><small>核对指标与依据</small></li>
          <li><span>04</span><strong>综合分析</strong><small>比较选中岗位</small></li>
        </ol>
      </header>

      <TargetRoleDashboard />

      <footer className="site-footer">
        <p>DeepSeek 提取结果需经人工确认后，才会进入综合分析。</p>
        <nav className="developer-links" aria-label="开发入口">
          <a href={`${apiBaseUrl}/health`}>API 存活检查</a>
          <a href={`${apiBaseUrl}/health/ready`}>数据库就绪检查</a>
          <a href={`${apiBaseUrl}/docs`}>API 文档</a>
        </nav>
      </footer>
    </main>
  );
}
