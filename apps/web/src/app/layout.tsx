import type { Metadata } from "next";
import type { ReactNode } from "react";

import { AppShell } from "@/components/AppShell";

import "./globals.css";


export const metadata: Metadata = {
  title: "岗位门槛分析系统",
  description: "将招聘信息转换为可核验、可汇总的岗位准入条件。",
};


export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body><AppShell>{children}</AppShell></body>
    </html>
  );
}
