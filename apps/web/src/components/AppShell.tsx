import Link from "next/link";
import type { ReactNode } from "react";


export function AppShell({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <>
      <header className="app-header">
        <div className="app-header-inner">
          <Link className="app-brand" href="/" aria-label="岗位门槛分析系统首页">
            <span className="app-brand-mark" aria-hidden="true">门</span>
            <span className="app-brand-copy">
              <strong>岗位门槛</strong>
              <small>证据化分析工作台</small>
            </span>
          </Link>
          <nav className="app-navigation" aria-label="全局导航">
            <Link href="/">方向工作台</Link>
          </nav>
        </div>
      </header>
      {children}
    </>
  );
}
