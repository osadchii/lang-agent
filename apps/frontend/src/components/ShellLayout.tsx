import type { ReactNode } from "react";

import styles from "./ShellLayout.module.css";

interface ShellLayoutProps {
  header: {
    eyebrow?: string;
    title: string;
    subtitle?: string;
    supporting?: string;
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
      <div className={styles.backdrop} aria-hidden="true" />

      <div className={styles.shellContent}>
        <header className={styles.hero}>
          <div className={styles.navbar}>
            <div className={styles.brand}>
              <span className={styles.brandGlyph} aria-hidden="true">
                ~
              </span>
              <div className={styles.brandCopy}>
                <span className={styles.brandName}>Kyma</span>
                <span className={styles.brandTagline}>Cypriot Greek Studio</span>
              </div>
            </div>

            <nav className={styles.navLinks} aria-label="Primary navigation">
              <button className={styles.navLink} type="button">
                Decks
              </button>
              <button className={styles.navLink} type="button">
                Flashcards
              </button>
              <button className={styles.navLink} type="button">
                Exercises
              </button>
              <button className={styles.navLink} type="button">
                Insights
              </button>
            </nav>

            <button className={styles.navCta} type="button">
              Join circle
            </button>
          </div>

          <div className={styles.heroCopy}>
            {header.eyebrow ? <span className={styles.eyebrow}>{header.eyebrow}</span> : null}
            <h1>{header.title}</h1>
            {header.subtitle ? <p>{header.subtitle}</p> : null}
            {header.supporting ? <p className={styles.supporting}>{header.supporting}</p> : null}
          </div>
        </header>

        <main className={styles.main}>{children}</main>
      </div>

      <footer className={styles.footer}>
        <div className={styles.footerCard}>
          <div className={styles.footerCopy}>
            <p className={styles.footerCaption}>{footer.caption}</p>
            <span className={styles.footerTagline}>Με αγάπη από τη Μεσόγειο</span>
          </div>
          <button className={styles.ctaButton} type="button" onClick={footer.onCtaClick}>
            {footer.ctaLabel}
          </button>
        </div>
      </footer>
    </div>
  );
}
