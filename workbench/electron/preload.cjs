const { contextBridge, ipcRenderer } = require("electron");
contextBridge.exposeInMainWorld(
  "desktop",
  Object.freeze({
    request: (path, method = "GET", body) =>
      ipcRenderer.invoke("api", { path, method, body }),
    exportReport: (id, format) => ipcRenderer.invoke("export", { id, format }),
    importZip: (name) => ipcRenderer.invoke("import-zip", { name }),
    importDocument: () => ipcRenderer.invoke("import-document"),
    chooseFolder: () => ipcRenderer.invoke("choose-folder"),
    windowControl: (action) => ipcRenderer.invoke("window", action),
    theme: (mode) => ipcRenderer.invoke("theme", mode),
  }),
);
