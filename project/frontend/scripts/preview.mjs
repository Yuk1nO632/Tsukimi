import { spawn } from "node:child_process";
import { createServer } from "node:net";
import { fileURLToPath } from "node:url";

const port = Number(process.env.TSUKIMI_PREVIEW_PORT || 3000);
if (!Number.isInteger(port) || port < 1 || port > 65535)
  throw new Error("预览端口无效");
const available = await new Promise((resolve) => {
  const server = createServer();
  server.once("error", () => resolve(false));
  server.listen(port, "127.0.0.1", () => server.close(() => resolve(true)));
});
if (!available) {
  console.error(
    `${port} 端口正在使用。请先在开发终端按 Ctrl+C，再运行 npm.cmd run preview。`,
  );
  process.exit(1);
}
const next = fileURLToPath(
  new URL("../node_modules/next/dist/bin/next", import.meta.url),
);
const cwd = fileURLToPath(new URL("..", import.meta.url));
const env = { ...process.env, TSUKIMI_BUILD_DIR: ".next-preview" };
let current;
function run(args) {
  return new Promise((resolve) => {
    current = spawn(process.execPath, [next, ...args], {
      cwd,
      env,
      stdio: "inherit",
    });
    current.once("error", () => resolve(1));
    current.once("exit", (code) => resolve(code ?? 1));
  });
}
process.once("SIGINT", () => current?.kill("SIGINT"));
process.once("SIGTERM", () => current?.kill("SIGTERM"));
const build = await run(["build"]);
if (build !== 0) process.exit(build);
console.log(
  `生产预览：http://127.0.0.1:${port}；代码修改后需重新运行 preview。`,
);
process.exit(
  await run(["start", "--hostname", "127.0.0.1", "--port", String(port)]),
);
