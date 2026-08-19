"use client";

import { FolderSimpleIcon } from "@phosphor-icons/react/dist/csr/FolderSimple";
import { HouseIcon } from "@phosphor-icons/react/dist/csr/House";
import { PlusCircleIcon } from "@phosphor-icons/react/dist/csr/PlusCircle";
import Link from "next/link";
import { usePathname } from "next/navigation";


export function AppNavigation() {
  const pathname = usePathname();

  return (
    <nav className="app-navigation" aria-label="全局导航">
      <Link href="/" aria-current={pathname === "/" ? "page" : undefined}>
        <HouseIcon aria-hidden="true" size={20} weight="regular" />
        方向总览
      </Link>
      <Link
        href="/#new-direction"
        onClick={() => window.dispatchEvent(new Event("open-new-direction"))}
      >
        <PlusCircleIcon aria-hidden="true" size={20} weight="regular" />
        新建方向
      </Link>
      <Link href="/#directions">
        <FolderSimpleIcon aria-hidden="true" size={20} weight="regular" />
        我的方向
      </Link>
    </nav>
  );
}
