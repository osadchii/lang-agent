import type { ReactNode } from "react";

import styles from "./ShellLayout.module.css";

interface ShellLayoutProps {
  header: {
    title: string;
    subtitle?: string;
  };
  footer: {
    caption: string;
    ctaLabel: string;
    onCtaClick: () => void;
  };
  children: ReactNode;
}

export function ShellLayout({ header, footer, children }: ShellLayoutProps): JSX.Element {
  return (
    <div className={styles.appShell}>
      <header className={styles.header}>
        <div className={styles.headerContent}>
          <h1>{header.title}</h1>
          {header.subtitle ? <p>{header.subtitle}</p> : null}
        </div>
      </header>

      <main className={styles.main}>{children}</main>

      <footer className={styles.footer}>
        <div>
          <p className={styles.footerCaption}>{footer.caption}</p>
        </div>
        <button className={styles.ctaButton} type="button" onClick={footer.onCtaClick}>
          {footer.ctaLabel}
        </button>
      </footer>
    </div>
  );
}
