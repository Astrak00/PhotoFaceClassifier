const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const http = require('http');

// Keep a global reference of the window object
let mainWindow = null;
let splashWindow = null;
let backendProcess = null;
let backendPort = 8000;
let weStartedBackend = false;

// Determine if we're in development or production
const isDev = !app.isPackaged;

// Get the platform and architecture for locating the correct binary
function getPlatformArch() {
  const platform = process.platform; // 'darwin', 'win32', 'linux'
  const arch = process.arch; // 'x64', 'arm64'
  return { platform, arch };
}

// Get the path to the backend executable
function getBackendExecutablePath() {
  const { platform, arch } = getPlatformArch();
  const executableName = platform === 'win32' ? 'face-classifier-backend.exe' : 'face-classifier-backend';
  
  if (isDev) {
    // In development, look for compiled backend in backend/dist/{platform}-{arch}/face-classifier-backend/
    // (PyInstaller directory mode output)
    const devPath = path.join(__dirname, '..', '..', 'backend', 'dist', `${platform}-${arch}`, 'face-classifier-backend', executableName);
    if (fs.existsSync(devPath)) {
      return devPath;
    }
    // Also check old single-file location for backwards compatibility
    const oldPath = path.join(__dirname, '..', '..', 'backend', 'dist', `${platform}-${arch}`, executableName);
    if (fs.existsSync(oldPath)) {
      return oldPath;
    }
    return null; // Will use uv fallback
  } else {
    // In production, backend is in resources/backend/face-classifier-backend
    return path.join(process.resourcesPath, 'backend', executableName);
  }
}

// Get the data directory path (for database, cache, config)
function getDataDir() {
  if (isDev) {
    return path.join(__dirname, '..', '..', 'backend', 'data');
  } else {
    // In production, use app's userData directory for persistent data
    return path.join(app.getPath('userData'), 'data');
  }
}

// Ensure data directory exists
function ensureDataDir() {
  const dataDir = getDataDir();
  if (!fs.existsSync(dataDir)) {
    fs.mkdirSync(dataDir, { recursive: true });
  }
  // Create cache subdirectory too
  const cacheDir = path.join(dataDir, 'cache');
  if (!fs.existsSync(cacheDir)) {
    fs.mkdirSync(cacheDir, { recursive: true });
  }
  return dataDir;
}

// Get the command to start the backend
function getBackendCommand() {
  const executablePath = getBackendExecutablePath();
  const dataDir = ensureDataDir();
  
  if (executablePath && fs.existsSync(executablePath)) {
    // Use compiled executable
    console.log('Using compiled backend:', executablePath);
    return {
      command: executablePath,
      args: ['--host', '127.0.0.1', '--port', String(backendPort)],
      env: {
        ...process.env,
        FACE_CLASSIFIER_DATA_DIR: dataDir,
      },
      cwd: path.dirname(executablePath),
    };
  } else if (isDev) {
    // In development, fallback to uv
    console.log('Using uv to run backend (development mode)');
    const backendPath = path.join(__dirname, '..', '..', 'backend');
    return {
      command: 'uv',
      args: ['run', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', String(backendPort)],
      env: { ...process.env },
      cwd: backendPath,
    };
  } else {
    // Production but no executable found - this is an error
    throw new Error('Backend executable not found in production build');
  }
}

// Update splash window status
function updateSplashStatus(message) {
  if (splashWindow && !splashWindow.isDestroyed()) {
    splashWindow.webContents.send('status-update', message);
  }
}

// Wait for the backend to be ready with progress updates
function waitForBackend(maxAttempts = 120) {
  return new Promise((resolve, reject) => {
    let attempts = 0;
    
    const checkHealth = () => {
      attempts++;
      updateSplashStatus(`Loading... (${attempts}s)`);
      
      const req = http.request({
        hostname: '127.0.0.1',
        port: backendPort,
        path: '/api/health',
        method: 'GET',
        timeout: 2000
      }, (res) => {
        if (res.statusCode === 200) {
          console.log('Backend is ready!');
          updateSplashStatus('Ready!');
          resolve();
        } else {
          retry();
        }
      });
      
      req.on('error', () => {
        retry();
      });
      
      req.on('timeout', () => {
        req.destroy();
        retry();
      });
      
      req.end();
    };
    
    const retry = () => {
      if (attempts < maxAttempts) {
        setTimeout(checkHealth, 1000);
      } else {
        reject(new Error('Backend failed to start after ' + maxAttempts + ' attempts'));
      }
    };
    
    checkHealth();
  });
}

// Check if backend is already running
function checkBackendRunning() {
  return new Promise((resolve) => {
    const req = http.request({
      hostname: '127.0.0.1',
      port: backendPort,
      path: '/api/health',
      method: 'GET',
      timeout: 1000
    }, (res) => {
      resolve(res.statusCode === 200);
    });
    
    req.on('error', () => resolve(false));
    req.on('timeout', () => {
      req.destroy();
      resolve(false);
    });
    
    req.end();
  });
}

// Start the Python backend
async function startBackend() {
  // First check if backend is already running
  updateSplashStatus('Checking for existing server...');
  const alreadyRunning = await checkBackendRunning();
  if (alreadyRunning) {
    console.log('Backend is already running on port', backendPort);
    weStartedBackend = false;
    return;
  }

  const backendCmd = getBackendCommand();
  
  console.log('Starting backend...');
  console.log('Command:', backendCmd.command, backendCmd.args.join(' '));
  console.log('Working directory:', backendCmd.cwd);
  updateSplashStatus('Starting backend server...');
  
  return new Promise((resolve, reject) => {
    backendProcess = spawn(backendCmd.command, backendCmd.args, {
      cwd: backendCmd.cwd,
      env: backendCmd.env,
      stdio: ['pipe', 'pipe', 'pipe'],
      // On Windows, we need to hide the console window
      windowsHide: true,
    });
    
    weStartedBackend = true;
    
    backendProcess.stdout.on('data', (data) => {
      console.log(`Backend: ${data.toString().trim()}`);
    });
    
    backendProcess.stderr.on('data', (data) => {
      console.log(`Backend: ${data.toString().trim()}`);
    });
    
    backendProcess.on('error', (err) => {
      console.error('Failed to start backend:', err);
      backendProcess = null;
      weStartedBackend = false;
      reject(err);
    });
    
    backendProcess.on('close', (code) => {
      console.log(`Backend process exited with code ${code}`);
      backendProcess = null;
    });
    
    // Wait for the backend to be ready
    // Backend startup can take 30-60 seconds due to PyInstaller unpacking
    setTimeout(async () => {
      try {
        await waitForBackend(120); // 120 seconds timeout for packaged app
        resolve();
      } catch (err) {
        reject(err);
      }
    }, 1000);
  });
}

// Stop the backend process
function stopBackend() {
  if (backendProcess && weStartedBackend) {
    console.log('Stopping backend process...');
    
    if (process.platform === 'win32') {
      // On Windows, use taskkill to ensure child processes are also killed
      spawn('taskkill', ['/pid', String(backendProcess.pid), '/f', '/t']);
    } else {
      backendProcess.kill('SIGTERM');
      
      // Force kill after 5 seconds if it hasn't stopped
      setTimeout(() => {
        if (backendProcess) {
          backendProcess.kill('SIGKILL');
        }
      }, 5000);
    }
    
    backendProcess = null;
    weStartedBackend = false;
  }
}

// Create the splash/loading window
function createSplashWindow() {
  splashWindow = new BrowserWindow({
    width: 400,
    height: 300,
    frame: false,
    transparent: true,
    resizable: false,
    center: true,
    alwaysOnTop: true,
    skipTaskbar: true,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.cjs'),
    },
  });

  // Create splash HTML content
  const splashHTML = `
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <style>
        * {
          margin: 0;
          padding: 0;
          box-sizing: border-box;
        }
        body {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          background: linear-gradient(135deg, #18181b 0%, #27272a 100%);
          color: white;
          height: 100vh;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          -webkit-app-region: drag;
          border-radius: 16px;
          overflow: hidden;
        }
        .logo {
          width: 80px;
          height: 80px;
          border-radius: 20px;
          background: linear-gradient(135deg, #8b5cf6 0%, #d946ef 100%);
          display: flex;
          align-items: center;
          justify-content: center;
          margin-bottom: 24px;
          box-shadow: 0 8px 32px rgba(139, 92, 246, 0.3);
        }
        .logo svg {
          width: 40px;
          height: 40px;
          color: white;
        }
        h1 {
          font-size: 24px;
          font-weight: 600;
          margin-bottom: 8px;
          letter-spacing: -0.5px;
        }
        .subtitle {
          font-size: 13px;
          color: #a1a1aa;
          margin-bottom: 32px;
        }
        .spinner-container {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 16px;
        }
        .spinner {
          width: 32px;
          height: 32px;
          border: 3px solid #3f3f46;
          border-top-color: #8b5cf6;
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        .status {
          font-size: 13px;
          color: #71717a;
          min-height: 20px;
        }
        .progress-bar {
          width: 200px;
          height: 4px;
          background: #3f3f46;
          border-radius: 2px;
          overflow: hidden;
          margin-top: 8px;
        }
        .progress-bar-inner {
          height: 100%;
          background: linear-gradient(90deg, #8b5cf6, #d946ef);
          border-radius: 2px;
          animation: progress 2s ease-in-out infinite;
          width: 30%;
        }
        @keyframes progress {
          0% { transform: translateX(-100%); }
          50% { transform: translateX(250%); }
          100% { transform: translateX(-100%); }
        }
      </style>
    </head>
    <body>
      <div class="logo">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"/>
          <circle cx="12" cy="12" r="4"/>
          <line x1="21.17" y1="8" x2="12" y2="8"/>
          <line x1="3.95" y1="6.06" x2="8.54" y2="14"/>
          <line x1="10.88" y1="21.94" x2="15.46" y2="14"/>
        </svg>
      </div>
      <h1>FaceSort</h1>
      <p class="subtitle">Photo Organizer</p>
      <div class="spinner-container">
        <div class="spinner"></div>
        <p class="status" id="status">Initializing...</p>
        <div class="progress-bar">
          <div class="progress-bar-inner"></div>
        </div>
      </div>
      <script>
        window.electronAPI?.onStatusUpdate?.((message) => {
          document.getElementById('status').textContent = message;
        });
      </script>
    </body>
    </html>
  `;

  splashWindow.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(splashHTML)}`);
  
  splashWindow.on('closed', () => {
    splashWindow = null;
  });
}

// Create the main browser window
function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 800,
    minHeight: 600,
    show: false, // Don't show until ready
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
    },
    icon: path.join(__dirname, '..', 'public', 'icon.png'),
    title: 'Face Classifier',
    // macOS specific
    titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
    trafficLightPosition: { x: 15, y: 15 },
  });

  // Load the app
  if (isDev) {
    // In development, load from Vite dev server
    mainWindow.loadURL('http://localhost:5173');
    mainWindow.webContents.openDevTools();
  } else {
    // In production, load from built files
    mainWindow.loadFile(path.join(__dirname, '..', 'dist', 'index.html'));
  }

  // Show main window and close splash when ready
  mainWindow.once('ready-to-show', () => {
    if (splashWindow && !splashWindow.isDestroyed()) {
      splashWindow.close();
    }
    mainWindow.show();
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// IPC handlers
ipcMain.handle('get-backend-url', () => {
  return `http://127.0.0.1:${backendPort}`;
});

ipcMain.handle('select-directory', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openDirectory']
  });
  
  if (result.canceled) {
    return null;
  }
  
  return result.filePaths[0];
});

ipcMain.handle('get-app-info', () => {
  return {
    version: app.getVersion(),
    platform: process.platform,
    arch: process.arch,
    dataDir: getDataDir(),
  };
});

// App lifecycle
app.whenReady().then(async () => {
  // Show splash screen immediately
  createSplashWindow();
  
  try {
    await startBackend();
    createMainWindow();
  } catch (err) {
    console.error('Failed to start application:', err);
    if (splashWindow && !splashWindow.isDestroyed()) {
      splashWindow.close();
    }
    dialog.showErrorBox('Startup Error', 
      `Failed to start the backend server.\n\nError: ${err.message}\n\nPlease check the logs or reinstall the application.`);
    app.quit();
  }

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createMainWindow();
    }
  });
});

app.on('window-all-closed', () => {
  stopBackend();
  
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  stopBackend();
});

app.on('quit', () => {
  stopBackend();
});

// Handle uncaught exceptions
process.on('uncaughtException', (error) => {
  console.error('Uncaught Exception:', error);
  stopBackend();
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
});
