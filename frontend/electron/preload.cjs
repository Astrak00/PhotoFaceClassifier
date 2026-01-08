const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('electronAPI', {
  // Get the backend URL from main process
  getBackendUrl: () => ipcRenderer.invoke('get-backend-url'),
  
  // Open native directory picker
  selectDirectory: () => ipcRenderer.invoke('select-directory'),
  
  // Platform info
  platform: process.platform,
  
  // Check if running in Electron
  isElectron: true,
  
  // Listen for status updates (used by splash screen)
  onStatusUpdate: (callback) => {
    ipcRenderer.on('status-update', (_event, message) => callback(message));
  },
});
