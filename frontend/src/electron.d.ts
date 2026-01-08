// Type declarations for Electron preload API
export interface ElectronAPI {
  getBackendUrl: () => Promise<string>;
  selectDirectory: () => Promise<string | null>;
  platform: string;
  isElectron: boolean;
}

declare global {
  interface Window {
    electronAPI?: ElectronAPI;
  }
}

export {};
