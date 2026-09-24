const {
  app,
  BrowserWindow,
  ipcMain,
  dialog,
  protocol,
  net,
  nativeTheme,
  session,
} = require("electron");
const { spawn } = require("node:child_process");
const fs = require("node:fs");
const fsp = fs.promises;
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const crypto = require("node:crypto");
protocol.registerSchemesAsPrivileged([
  {
    scheme: "sentinel",
    privileges: {
      standard: true,
      secure: true,
      supportFetchAPI: true,
      corsEnabled: true,
    },
  },
]);
if (process.env.SXF_WORKBENCH_PROFILE) {
  fs.mkdirSync(process.env.SXF_WORKBENCH_PROFILE, { recursive: true });
  app.setPath("userData", process.env.SXF_WORKBENCH_PROFILE);
}
let win,
  child,
  base,
  quitting = false;
const token = crypto.randomBytes(32).toString("hex");
const routes = {
  GET: [
    /^\/intelligence$/,
    /^\/assets\/discovery\/[^/]+$/,
    /^\/(assets|remediations|agent\/search)$/,
    /^\/agent\/resources\/(skills|knowledge)$/,
    /^\/(health|dashboard|settings|capabilities|events|projects|investigations)$/,
    /^\/events\/[^/]+(?:\/evidence)?$/,
    /^\/projects\/[^/]+\/(files|file|scan)$/,
    /^\/investigations\/[^/]+(?:\/report)?$/,
  ],
  POST: [
    /^\/intelligence\/sync$/,
    /^\/assets\/discovery$/,
    /^\/assets(?:\/[^/]+\/test)?$/,
    /^\/agent\/resources\/(skills|knowledge)$/,
    /^\/investigations\/[^/]+\/repair$/,
    /^\/events\/sync$/,
    /^\/investigations$/,
    /^\/projects$/,
    /^\/projects\/[^/]+\/scan$/,
    /^\/settings\/test\/(xdr|llm)$/,
  ],
  DELETE: [
    /^\/assets\/[^/]+$/,
    /^\/agent\/resources\/(skills|knowledge)\/[^/]+$/,
  ],
  PUT: [
    /^\/assets\/[^/]+$/,
    /^\/agent\/resources\/(skills|knowledge)\/[^/]+$/,
    /^\/settings$/,
    /^\/events\/[^/]+\/project$/,
  ],
};
function allowed(p, m) {
  if (
    typeof p !== "string" ||
    p.length > 4000 ||
    !p.startsWith("/") ||
    p.startsWith("//") ||
    p.includes("\\")
  )
    return false;
  const u = new URL(p, "http://local");
  return (
    u.origin === "http://local" && routes[m]?.some((r) => r.test(u.pathname))
  );
}
async function api(p, m = "GET", body) {
  if (!allowed(p, m)) throw Error("Unsupported desktop API");
  const r = await fetch(base + "/api" + p, {
    method: m,
    headers: {
      "X-Sentinel-Client": "console",
      "X-Sentinel-Token": token,
      "Content-Type": "application/json",
    },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: AbortSignal.timeout(150000),
  });
  if (r.ok && r.headers.get("content-type")?.includes("wordprocessingml"))
    return { base64: Buffer.from(await r.arrayBuffer()).toString("base64") };
  const text = await r.text();
  let data;
  try {
    data = JSON.parse(text);
  } catch {
    data = text;
  }
  if (!r.ok)
    throw Error(
      typeof data.detail === "string"
        ? data.detail
        : "请求失败（" + r.status + "）",
    );
  return data;
}
function authorize(e) {
  if (
    !win ||
    e.sender !== win.webContents ||
    e.senderFrame !== win.webContents.mainFrame ||
    !e.senderFrame.url.startsWith("sentinel://app/")
  )
    throw Error("Untrusted IPC sender");
}
function handle(name, fn) {
  ipcMain.handle(name, async (e, arg) => {
    authorize(e);
    return fn(arg);
  });
}
function startBackend() {
  return new Promise((resolve, reject) => {
    const executable = path.join(
      process.resourcesPath,
      "backend",
      "sentinel-backend.exe",
    );
    const env = { ...process.env, SXF_DESKTOP_TOKEN: token, PYTHONUTF8: "1" };
    child = spawn(executable, [], {
      env,
      windowsHide: true,
      stdio: ["pipe", "pipe", "pipe"],
    });
    let buf = "";
    let settled = false;
    const timer = setTimeout(() => {
      reject(Error("本机服务启动超时"));
      child.kill();
    }, 30000);
    child.stdout.on("data", (chunk) => {
      buf += chunk.toString();
      let i;
      while ((i = buf.indexOf("\n")) >= 0) {
        const line = buf.slice(0, i);
        buf = buf.slice(i + 1);
        try {
          const d = JSON.parse(line);
          if (Number.isInteger(d.port) && d.port > 0 && d.port < 65536) {
            base = "http://127.0.0.1:" + d.port;
            settled = true;
            clearTimeout(timer);
            resolve();
          } else if (d.error) {
            clearTimeout(timer);
            reject(Error(d.error));
          }
        } catch {}
      }
    });
    child.stderr.on("data", (chunk) => {
      fs.appendFileSync(
        path.join(app.getPath("userData"), "backend.log"),
        chunk,
      );
    });
    child.on("error", (err) => {
      clearTimeout(timer);
      reject(err);
    });
    child.on("exit", () => {
      clearTimeout(timer);
      if (!settled) reject(Error("本机服务启动失败"));
      else if (!quitting && win)
        dialog.showErrorBox(
          "本机服务已停止",
          "请重新启动工作台。未完成的调查可重新发起。",
        );
    });
  });
}
if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (win) {
      if (win.isMinimized()) win.restore();
      win.focus();
    }
  });
  app
    .whenReady()
    .then(async () => {
      app.setName("Double Pupil");
      const dist = path.join(__dirname, "../dist");
      protocol.handle("sentinel", (request) => {
        const u = new URL(request.url);
        const rel = decodeURIComponent(u.pathname);
        const file = path.resolve(dist, "." + rel);
        if (u.hostname !== "app" || !file.startsWith(dist + path.sep))
          return new Response("Forbidden", { status: 403 });
        return net.fetch(pathToFileURL(file).toString());
      });
      session.defaultSession.setPermissionRequestHandler((_w, _p, cb) =>
        cb(false),
      );
      session.defaultSession.setPermissionCheckHandler(() => false);
      await startBackend();
      win = new BrowserWindow({
        width: 1560,
        height: 1000,
        minWidth: 1120,
        minHeight: 740,
        show: false,
        frame: false,
        backgroundColor: "#0d1017",
        webPreferences: {
          preload: path.join(__dirname, "preload.cjs"),
          contextIsolation: true,
          nodeIntegration: false,
          sandbox: true,
          webSecurity: true,
        },
      });
      win.webContents.setWindowOpenHandler(() => ({ action: "deny" }));
      win.webContents.on("will-navigate", (e) => e.preventDefault());
      handle("api", ({ path: p, method = "GET", body }) =>
        api(p, method, body),
      );
      handle("window", (action) => {
        if (action === "minimize") win.minimize();
        if (action === "maximize")
          win.isMaximized() ? win.unmaximize() : win.maximize();
        if (action === "close") win.close();
      });
      handle("theme", (mode) => {
        if (["dark", "light", "system"].includes(mode))
          nativeTheme.themeSource = mode;
      });
      handle("import-document", async () => {
        const r = await dialog.showOpenDialog(win, {
          properties: ["openFile"],
          filters: [
            { name: "Knowledge / Skill", extensions: ["md", "txt", "json"] },
          ],
        });
        if (r.canceled) return null;
        const file = r.filePaths[0];
        if ((await fsp.stat(file)).size > 64000) throw Error("文档超过 64 KB");
        return {
          name: path.basename(file),
          content: await fsp.readFile(file, "utf8"),
        };
      });
      handle("choose-folder", async () => {
        const r = await dialog.showOpenDialog(win, {
          properties: ["openDirectory"],
        });
        return r.canceled ? null : r.filePaths[0];
      });
      handle("export", async ({ id, format }) => {
        if (
          !/^inv-[\w-]+$/.test(id) ||
          !["markdown", "json", "docx"].includes(format)
        )
          throw Error("Invalid report");
        const data = await api(
          "/investigations/" + id + "/report?format=" + format,
        );
        const settings = await api("/settings");
        const directory =
          settings.workspace?.report_directory || app.getPath("documents");
        await fsp.mkdir(directory, { recursive: true });
        const r = await dialog.showSaveDialog(win, {
          defaultPath: path.join(
            directory,
            id +
              (format === "docx"
                ? ".docx"
                : format === "json"
                  ? ".json"
                  : ".md"),
          ),
        });
        if (r.canceled) return false;
        await fsp.writeFile(
          r.filePath,
          format === "docx"
            ? Buffer.from(data.base64, "base64")
            : format === "json"
              ? JSON.stringify(data, null, 2)
              : data,
          "utf8",
        );
        return true;
      });
      handle("import-zip", async ({ name }) => {
        if (typeof name !== "string" || name.length < 1 || name.length > 100)
          throw Error("请输入项目名称");
        const r = await dialog.showOpenDialog(win, {
          properties: ["openFile"],
          filters: [{ name: "ZIP", extensions: ["zip"] }],
        });
        if (r.canceled) return null;
        const file = r.filePaths[0];
        if ((await fsp.stat(file)).size > 25 * 1024 * 1024)
          throw Error("ZIP 超过 25 MB");
        const form = new FormData();
        form.append("name", name);
        form.append(
          "file",
          new Blob([await fsp.readFile(file)]),
          "project.zip",
        );
        const response = await fetch(base + "/api/projects/upload", {
          method: "POST",
          headers: {
            "X-Sentinel-Client": "console",
            "X-Sentinel-Token": token,
          },
          body: form,
          signal: AbortSignal.timeout(120000),
        });
        const data = await response.json();
        if (!response.ok) throw Error(data.detail || "ZIP 导入失败");
        return data;
      });
      await win.loadURL("sentinel://app/index.html");
      win.show();
    })
    .catch((err) => {
      fs.appendFileSync(
        path.join(app.getPath("userData"), "startup.log"),
        err.stack + "\n",
      );
      dialog.showErrorBox("Double Pupil 启动失败", err.message);
      app.quit();
    });
  app.on("window-all-closed", () => app.quit());
  app.on("before-quit", () => {
    quitting = true;
    if (child) {
      child.stdin.end();
      const c = child;
      setTimeout(() => c.kill(), 8000).unref();
      child = null;
    }
  });
}
