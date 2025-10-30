/**
 * Telegram WebApp API integration utilities
 * Docs: https://core.telegram.org/bots/webapps
 */

export interface TelegramUser {
  id: number;
  first_name: string;
  last_name?: string;
  username?: string;
  language_code?: string;
  is_premium?: boolean;
  photo_url?: string;
}

export interface TelegramWebApp {
  initData: string;
  initDataUnsafe: {
    query_id?: string;
    user?: TelegramUser;
    receiver?: TelegramUser;
    chat?: {
      id: number;
      type: string;
      title: string;
      username?: string;
      photo_url?: string;
    };
    chat_type?: string;
    chat_instance?: string;
    start_param?: string;
    can_send_after?: number;
    auth_date: number;
    hash: string;
  };
  version: string;
  platform: string;
  colorScheme: "light" | "dark";
  themeParams: Record<string, string>;
  isExpanded: boolean;
  viewportHeight: number;
  viewportStableHeight: number;
  headerColor: string;
  backgroundColor: string;
  isClosingConfirmationEnabled: boolean;
  ready: () => void;
  expand: () => void;
  close: () => void;
  MainButton: {
    text: string;
    color: string;
    textColor: string;
    isVisible: boolean;
    isActive: boolean;
    isProgressVisible: boolean;
    setText: (text: string) => void;
    onClick: (callback: () => void) => void;
    offClick: (callback: () => void) => void;
    show: () => void;
    hide: () => void;
    enable: () => void;
    disable: () => void;
    showProgress: (leaveActive: boolean) => void;
    hideProgress: () => void;
    setParams: (params: {
      text?: string;
      color?: string;
      text_color?: string;
      is_active?: boolean;
      is_visible?: boolean;
    }) => void;
  };
  BackButton: {
    isVisible: boolean;
    onClick: (callback: () => void) => void;
    offClick: (callback: () => void) => void;
    show: () => void;
    hide: () => void;
  };
}

declare global {
  interface Window {
    Telegram?: {
      WebApp: TelegramWebApp;
    };
  }
}

/**
 * Check if the app is running inside Telegram WebApp
 */
export function isTelegramWebApp(): boolean {
  return typeof window !== "undefined" && Boolean(window.Telegram?.WebApp);
}

/**
 * Get Telegram WebApp instance
 */
export function getTelegramWebApp(): TelegramWebApp | null {
  if (!isTelegramWebApp()) {
    return null;
  }
  return window.Telegram!.WebApp;
}

/**
 * Get current Telegram user data
 */
export function getTelegramUser(): TelegramUser | null {
  const webApp = getTelegramWebApp();
  if (!webApp) {
    return null;
  }
  return webApp.initDataUnsafe.user ?? null;
}

/**
 * Initialize Telegram WebApp and notify Telegram that the app is ready
 */
export function initTelegramWebApp(): void {
  const webApp = getTelegramWebApp();
  if (webApp) {
    webApp.ready();
    // Expand to full viewport height
    webApp.expand();
  }
}

/**
 * Get theme parameters from Telegram
 */
export function getTelegramTheme(): "light" | "dark" | null {
  const webApp = getTelegramWebApp();
  if (!webApp) {
    return null;
  }
  return webApp.colorScheme;
}
