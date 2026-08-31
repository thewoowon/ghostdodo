import type { ReactNode } from "react";

import { FieldNotebook } from "@/components/brand/svg/marks";

import styles from "./PolicyPage.module.css";

/** Shared shell for policy and explainer pages. */
export function PolicyPage({
  title,
  lede,
  children,
}: {
  title: string;
  lede: string;
  children: ReactNode;
}) {
  return (
    <article className={`gd-shell ${styles.page}`}>
      <header className={styles.header}>
        <FieldNotebook size={28} className={styles.mark} />
        <h1 className={styles.title}>{title}</h1>
        <p className={styles.lede}>{lede}</p>
      </header>
      <div className={styles.body}>{children}</div>
    </article>
  );
}
