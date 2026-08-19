import Link from "next/link";
import type { ReactNode } from "react";

import { AppNavigation } from "./AppNavigation";


export function AppShell({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <div className="app-frame">
      <aside className="app-sidebar">
        <Link className="app-brand" href="/" aria-label="岗位门槛分析系统首页">
          <span className="app-brand-mark" aria-hidden="true">门</span>
          <strong>岗位门槛</strong>
        </Link>
        <AppNavigation />
      </aside>
      <div className="app-content">{children}</div>
    </div>
  );
}
