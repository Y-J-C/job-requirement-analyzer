import { TargetRoleDashboard } from "@/features/target-roles/TargetRoleDashboard";


const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";


export default function Home() {
  return (
    <main className="shell">
      <header className="masthead">
        <p className="eyebrow">文件解析 · 第七阶段</p>
        <h1>岗位门槛分析系统</h1>
        <p className="lede">
          将零散招聘信息整理为有原文依据、经人工确认、可以跨岗位汇总的准入条件。
        </p>
      </header>

      <TargetRoleDashboard />

      <nav className="developer-links" aria-label="开发入口">
        <a href={`${apiBaseUrl}/health`}>API 存活检查</a>
        <a href={`${apiBaseUrl}/health/ready`}>数据库就绪检查</a>
        <a href={`${apiBaseUrl}/docs`}>API 文档</a>
      </nav>

      <footer>
        当前已支持 PDF、Markdown 和 DOCX 文件上传与持久化解析，并可继续进行 DeepSeek
        分析、人工审核、版本切换和岗位门槛汇总；登录尚未启用。
      </footer>
    </main>
  );
}
