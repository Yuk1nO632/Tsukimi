"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAccount } from "./account-provider";

export default function AccountPanel() {
  const account = useAccount();
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [nickname, setNickname] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [code, setCode] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [remaining, setRemaining] = useState(0);
  const [deadline, setDeadline] = useState(0);
  const [importing, setImporting] = useState(false);
  useEffect(() => {
    if (!deadline) return;
    const tick = () =>
      setRemaining(Math.max(0, Math.ceil((deadline - Date.now()) / 1000)));
    tick();
    const timer = setInterval(tick, 1000);
    return () => clearInterval(timer);
  }, [deadline]);

  function changeMode(next) {
    setMode(next);
    setError("");
    setMessage("");
    setCode("");
    setPassword("");
    setConfirmation("");
    setCurrentPassword("");
  }
  async function sendCode() {
    setError("");
    setMessage("");
    if (!email.trim()) {
      setError("请先填写邮箱。");
      return;
    }
    try {
      const result = await account.action("code", {
        email,
        purpose: mode === "register" ? "register" : "reset",
      });
      setDeadline(Date.now() + result.retry_after * 1000);
      setMessage(
        account.mail_mode === "file"
          ? "验证码已写入本机开发邮箱文件，请按复习指南查看。"
          : result.message,
      );
    } catch (failure) {
      setError(failure.message);
    }
  }
  async function submit(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    if (mode !== "login" && password !== confirmation) {
      setError("两次输入的密码不一致。");
      return;
    }
    try {
      const path = {
        login: "login",
        register: "register",
        reset: "reset-password",
        password: "password",
      }[mode];
      const payload =
        mode === "password"
          ? { current_password: currentPassword, password }
          : {
              email,
              password,
              ...(mode !== "login" ? { code } : {}),
              ...(mode === "register" ? { nickname } : {}),
            };
      const data = await account.action(path, payload);
      setPassword("");
      setConfirmation("");
      setCode("");
      setCurrentPassword("");
      setMessage(
        data.message || (mode === "register" ? "注册成功。" : "登录成功。"),
      );
      if (mode === "reset" || mode === "password") setMode("login");
    } catch (failure) {
      setError(failure.message);
    }
  }
  async function importData(action) {
    setImporting(true);
    setError("");
    try {
      await account.action("import", { action });
      window.dispatchEvent(new Event("tsukimi-library-refresh"));
      setMessage(
        action === "merge"
          ? "已导入当前浏览器的记录，重复条目保留账号记录。"
          : "已使用账号中的记录。",
      );
    } catch (failure) {
      setError(failure.message);
    } finally {
      setImporting(false);
    }
  }
  async function logout() {
    setError("");
    try {
      await account.action("logout");
      changeMode("login");
      setMessage("已退出当前设备。");
    } catch (failure) {
      setError(failure.message);
    }
  }
  const titles = {
    login: "欢迎回来",
    register: "创建账号",
    reset: "找回密码",
    password: "修改密码",
  };
  const showForm = !account.user || mode === "password";
  return (
    <div className="content-shell account-page">
      <section className="account-intro">
        <span className="portal-eyebrow">TSUKIMI ACCOUNT</span>
        <h1>
          你的片单，
          <br />
          随时接着看。
        </h1>
        <p>登录同一个账号，在电脑和手机上继续追番。</p>
        <div className="account-benefits">
          <span>片单同步</span>
          <span>观看进度</span>
          <span>来源偏好</span>
        </div>
        <Link href="/collection" className="text-button">
          查看我的追番 →
        </Link>
      </section>
      <section className="account-card" aria-label="账号管理">
        {!account.ready ? (
          <>
            <h2>连接账号服务</h2>
            <p role="status">{account.error || "正在读取登录状态…"}</p>
            {account.error && (
              <button
                className="outline-button"
                onClick={() => void account.reload()}
              >
                重试
              </button>
            )}
          </>
        ) : (
          <>
            {account.user && mode !== "password" ? (
              <>
                <div className="account-avatar" aria-hidden="true">
                  {account.user.nickname.slice(0, 1)}
                </div>
                <h2>{account.user.nickname}</h2>
                <p className="account-email">{account.user.email}</p>
                <p className="account-note">
                  片单、观看进度与来源偏好已关联到此账号。
                </p>
                {account.pending_import && (
                  <div className="account-import" role="status">
                    <h3>发现当前浏览器的匿名记录</h3>
                    <p>
                      可将片单、观看进度和来源选择补入账号。重复条目保留账号记录。
                    </p>
                    <div>
                      <button
                        className="solid-button"
                        disabled={account.busy || importing}
                        onClick={() => void importData("merge")}
                      >
                        导入这些记录
                      </button>
                      <button
                        className="text-button"
                        disabled={account.busy || importing}
                        onClick={() => void importData("skip")}
                      >
                        使用账号记录
                      </button>
                    </div>
                  </div>
                )}
                <div className="account-actions">
                  <Link className="solid-button" href="/collection">
                    继续追番 →
                  </Link>
                  <button
                    className="outline-button"
                    onClick={() => changeMode("password")}
                  >
                    修改密码
                  </button>
                  <button
                    className="text-button"
                    disabled={account.busy}
                    onClick={() => void logout()}
                  >
                    退出当前设备
                  </button>
                </div>
              </>
            ) : (
              <>
                <div
                  className="account-tabs"
                  role="group"
                  aria-label="账号操作"
                >
                  {(account.user
                    ? [["password", "修改密码"]]
                    : [
                        ["login", "登录"],
                        ["register", "注册"],
                        ["reset", "找回密码"],
                      ]
                  ).map(([value, label]) => (
                    <button
                      type="button"
                      key={value}
                      aria-pressed={mode === value}
                      disabled={account.busy}
                      onClick={() => changeMode(value)}
                    >
                      {label}
                    </button>
                  ))}
                </div>
                <h2>{titles[mode]}</h2>
                {!account.mail_ready &&
                  mode !== "login" &&
                  mode !== "password" && (
                    <p className="account-note">
                      邮件服务尚未配置。可按指南启用本地开发邮箱，完成本机复习。
                    </p>
                  )}
                {account.mail_mode === "file" && (
                  <p className="account-dev-label">
                    本地开发邮箱 · 验证码写入本机文件
                  </p>
                )}
              </>
            )}
            {showForm && (
              <form onSubmit={submit} className="account-form">
                {mode !== "password" && (
                  <label>
                    邮箱
                    <input
                      type="email"
                      autoComplete="email"
                      value={email}
                      onChange={(event) => setEmail(event.target.value)}
                      required
                      maxLength={254}
                      placeholder="you@example.com"
                    />
                  </label>
                )}
                {mode === "register" && (
                  <label>
                    昵称
                    <input
                      autoComplete="nickname"
                      value={nickname}
                      onChange={(event) => setNickname(event.target.value)}
                      required
                      maxLength={30}
                    />
                  </label>
                )}
                {(mode === "register" || mode === "reset") && (
                  <label>
                    邮箱验证码
                    <span className="account-code-row">
                      <input
                        inputMode="numeric"
                        autoComplete="one-time-code"
                        pattern="[0-9]{6}"
                        maxLength={6}
                        required
                        value={code}
                        onChange={(event) => setCode(event.target.value)}
                        placeholder="6 位验证码"
                      />
                      <button
                        type="button"
                        className="outline-button"
                        disabled={
                          account.busy || remaining > 0 || !account.mail_ready
                        }
                        onClick={() => void sendCode()}
                      >
                        {remaining > 0 ? `${remaining} 秒后重发` : "发送验证码"}
                      </button>
                    </span>
                  </label>
                )}
                {mode === "password" && (
                  <label>
                    当前密码
                    <input
                      type="password"
                      autoComplete="current-password"
                      minLength={10}
                      maxLength={128}
                      required
                      value={currentPassword}
                      onChange={(event) =>
                        setCurrentPassword(event.target.value)
                      }
                    />
                  </label>
                )}
                <label>
                  {mode === "login" || mode === "register" ? "密码" : "新密码"}
                  <input
                    type="password"
                    autoComplete={
                      mode === "login" ? "current-password" : "new-password"
                    }
                    minLength={10}
                    maxLength={128}
                    required
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    placeholder="10–128 个字符"
                  />
                </label>
                {mode !== "login" && (
                  <label>
                    确认密码
                    <input
                      type="password"
                      autoComplete="new-password"
                      minLength={10}
                      maxLength={128}
                      required
                      value={confirmation}
                      onChange={(event) => setConfirmation(event.target.value)}
                    />
                  </label>
                )}
                <button
                  className="solid-button"
                  disabled={account.busy}
                  type="submit"
                >
                  {account.busy
                    ? "正在处理…"
                    : {
                        login: "登录",
                        register: "注册并登录",
                        reset: "重置密码",
                        password: "保存新密码",
                      }[mode]}
                </button>
                {mode === "password" && (
                  <button
                    type="button"
                    className="text-button"
                    onClick={() => changeMode("login")}
                  >
                    返回账号
                  </button>
                )}
              </form>
            )}
          </>
        )}
        {message && (
          <p className="account-message" role="status">
            {message}
          </p>
        )}
        {(error || account.error) && (
          <p className="account-error" role="alert">
            {error || account.error}
          </p>
        )}
      </section>
    </div>
  );
}
