"use client";
import Link from "next/link";
import { useState } from "react";
import { useAccount } from "./account-provider";

const emptyQuestions = () =>
  Array.from({ length: 3 }, () => ({ question: "", answer: "" }));

function QuestionFields({ questions, onChange }) {
  function update(index, field, value) {
    onChange(
      questions.map((item, current) =>
        current === index ? { ...item, [field]: value } : item,
      ),
    );
  }
  return (
    <fieldset className="security-fields">
      <legend>设置三个密保问题</legend>
      <p className="account-note">
        请使用自己能记住、别人难以猜到的答案，避免生日、学校等公开信息。重置密码时需要全部答对。
      </p>
      {questions.map((item, index) => (
        <div className="security-question" key={index}>
          <label>
            密保问题 {index + 1}
            <input
              required
              minLength={4}
              maxLength={100}
              value={item.question}
              placeholder="输入自定义问题"
              onChange={(event) =>
                update(index, "question", event.target.value)
              }
            />
          </label>
          <label>
            密保答案 {index + 1}
            <input
              type="password"
              autoComplete="off"
              required
              minLength={6}
              maxLength={128}
              value={item.answer}
              placeholder="6–128 个字符"
              onChange={(event) => update(index, "answer", event.target.value)}
            />
          </label>
        </div>
      ))}
      <p className="account-note">
        答案忽略首尾空格和英文大小写，三个问题及答案分别设置为不同内容。
      </p>
    </fieldset>
  );
}

export default function AccountPanel() {
  const account = useAccount();
  const [registrationStep, setRegistrationStep] = useState(1);
  const [mode, setMode] = useState("login");
  const [username, setUsername] = useState("");
  const [nickname, setNickname] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [questions, setQuestions] = useState(emptyQuestions);
  const [challenge, setChallenge] = useState(null);
  const [answers, setAnswers] = useState(["", "", ""]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  function changeMode(next) {
    setMode(next);
    setRegistrationStep(1);
    setError("");
    setMessage("");
    setPassword("");
    setConfirmation("");
    setCurrentPassword("");
    setChallenge(null);
    setAnswers(["", "", ""]);
    setQuestions(emptyQuestions());
  }
  async function loadQuestions() {
    setError("");
    setMessage("");
    setChallenge(null);
    setAnswers(["", "", ""]);
    if (!username.trim()) {
      setError("请先填写账号名。");
      return;
    }
    try {
      setChallenge(await account.action("recovery", { username }));
    } catch (failure) {
      setError(failure.message);
    }
  }
  async function submit(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    if (!["login", "security"].includes(mode) && password !== confirmation) {
      setError("两次输入的密码不一致。");
      return;
    }
    if (mode === "reset" && !challenge) {
      setError("请先获取密保问题。");
      return;
    }
    if (mode === "register" && registrationStep === 1) {
      setRegistrationStep(2);
      return;
    }
    try {
      const path = {
        login: "login",
        register: "register",
        reset: "reset-password",
        password: "password",
        security: "security-questions",
      }[mode];
      const payload =
        mode === "password"
          ? { current_password: currentPassword, password }
          : mode === "security"
            ? { current_password: currentPassword, questions }
            : {
                username,
                password,
                ...(mode === "register" ? { nickname, questions } : {}),
                ...(mode === "reset"
                  ? { challenge: challenge.challenge, answers }
                  : {}),
              };
      const data = await account.action(path, payload);
      setPassword("");
      setConfirmation("");
      setCurrentPassword("");
      setQuestions(emptyQuestions());
      setAnswers(["", "", ""]);
      setChallenge(null);
      setMessage(
        data.message ||
          (mode === "security"
            ? "密保问题已更新。"
            : mode === "register"
              ? "注册成功。"
              : "登录成功。"),
      );
      if (["reset", "password", "security"].includes(mode)) setMode("login");
    } catch (failure) {
      setError(failure.message);
    }
  }
  async function importData(action) {
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
  const editing = mode === "password" || mode === "security";
  const showForm = !account.user || editing;
  return (
    <div
      className={`content-shell account-page${mode === "register" || mode === "security" ? " account-page-expanded" : ""}`}
    >
      <header className="account-intro">
        <span className="portal-eyebrow">TSUKIMI ACCOUNT</span>
        <h1>{account.user ? "我的账号" : "登录与注册"}</h1>
        <p>管理片单与观看进度</p>
        <Link className="outline-button history-entry" href="#watch-history">观看历史 →</Link>
      </header>
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
            {account.user && !editing ? (
              <>
                <div className="account-avatar" aria-hidden="true">
                  {account.user.nickname.slice(0, 1)}
                </div>
                <h2>{account.user.nickname}</h2>
                <p className="account-email">
                  账号名 {account.user.username}
                  {account.user.role === "admin" && (
                    <span className="account-role">管理员</span>
                  )}
                </p>
                <p className="account-note">
                  {account.user.security_configured
                    ? "已设置密保问题，可用于忘记密码后重置。"
                    : "请补设密保问题，以便忘记密码时找回账号。"}
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
                        disabled={account.busy}
                        onClick={() => void importData("merge")}
                      >
                        导入这些记录
                      </button>
                      <button
                        className="text-button"
                        disabled={account.busy}
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
                    className="outline-button"
                    onClick={() => changeMode("security")}
                  >
                    {account.user.security_configured
                      ? "修改密保问题"
                      : "设置密保问题"}
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
                    ? [
                        [
                          mode,
                          editing && mode === "security"
                            ? "设置密保"
                            : "修改密码",
                        ],
                      ]
                    : [
                        ["login", "登录"],
                        ["register", "注册"],
                        ["reset", "找回密码"],
                      ]
                  ).map(([value, label]) => (
                    <button
                      type="button"
                      key={value}
                      disabled={account.busy}
                      aria-pressed={mode === value}
                      onClick={() => changeMode(value)}
                    >
                      {label}
                    </button>
                  ))}
                </div>
                <h2>
                  {
                    {
                      login: "欢迎回来",
                      register:
                        registrationStep === 1 ? "创建账号" : "设置密保问题",
                      reset: "找回密码",
                      password: "修改密码",
                      security: "设置密保问题",
                    }[mode]
                  }
                </h2>
              </>
            )}
            {showForm && (
              <form
                onSubmit={submit}
                className={`account-form${mode === "register" && registrationStep === 1 ? " account-form-identity" : ""}`}
              >
                {mode === "register" && (
                  <ol className="registration-steps" aria-label="注册步骤">
                    <li
                      aria-current={registrationStep === 1 ? "step" : undefined}
                    >
                      <span>1</span>账号信息
                    </li>
                    <li
                      aria-current={registrationStep === 2 ? "step" : undefined}
                    >
                      <span>2</span>密保设置
                    </li>
                  </ol>
                )}
                {!editing &&
                  (mode !== "register" || registrationStep === 1) && (
                    <label>
                      账号名
                      <input
                        autoComplete="username"
                        value={username}
                        required
                        maxLength={mode === "register" ? 32 : 254}
                        minLength={mode === "register" ? 4 : 3}
                        pattern={
                          mode === "register" ? "[A-Za-z0-9_]{4,32}" : undefined
                        }
                        placeholder={
                          mode === "register"
                            ? "4–32 位英文字母、数字或下划线"
                            : "账号名或原邮箱账号"
                        }
                        onChange={(event) => {
                          setUsername(event.target.value);
                          setChallenge(null);
                          setAnswers(["", "", ""]);
                        }}
                      />
                    </label>
                  )}
                {mode === "register" && registrationStep === 1 && (
                  <label>
                    昵称
                    <input
                      autoComplete="nickname"
                      value={nickname}
                      required
                      maxLength={30}
                      onChange={(event) => setNickname(event.target.value)}
                    />
                  </label>
                )}
                {mode === "reset" && (
                  <>
                    <button
                      className="outline-button"
                      type="button"
                      disabled={account.busy}
                      onClick={() => void loadQuestions()}
                    >
                      {challenge ? "重新获取密保问题" : "获取密保问题"}
                    </button>
                    {challenge && (
                      <fieldset className="security-fields">
                        <legend>回答注册时的三个问题</legend>
                        <p className="account-note">
                          本次问题校验 5 分钟有效，最多尝试 5 次。
                        </p>
                        {challenge.questions.map((question, index) => (
                          <label key={index}>
                            {question}
                            <input
                              aria-label={`密保答案 ${index + 1}`}
                              type="password"
                              autoComplete="off"
                              required
                              minLength={6}
                              maxLength={128}
                              value={answers[index]}
                              onChange={(event) =>
                                setAnswers(
                                  answers.map((value, current) =>
                                    current === index
                                      ? event.target.value
                                      : value,
                                  ),
                                )
                              }
                            />
                          </label>
                        ))}
                      </fieldset>
                    )}
                  </>
                )}
                {editing && (
                  <label>
                    当前密码
                    <input
                      type="password"
                      autoComplete="current-password"
                      required
                      minLength={10}
                      maxLength={128}
                      value={currentPassword}
                      onChange={(event) =>
                        setCurrentPassword(event.target.value)
                      }
                    />
                  </label>
                )}
                {mode !== "security" &&
                  (mode !== "register" || registrationStep === 1) && (
                    <>
                      <label>
                        {["login", "register"].includes(mode)
                          ? "密码"
                          : "新密码"}
                        <input
                          type="password"
                          autoComplete={
                            mode === "login"
                              ? "current-password"
                              : "new-password"
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
                            onChange={(event) =>
                              setConfirmation(event.target.value)
                            }
                          />
                        </label>
                      )}
                    </>
                  )}
                {(mode === "security" ||
                  (mode === "register" && registrationStep === 2)) && (
                  <QuestionFields
                    questions={questions}
                    onChange={setQuestions}
                  />
                )}
                <button
                  className="solid-button"
                  disabled={account.busy || (mode === "reset" && !challenge)}
                  type="submit"
                >
                  {account.busy
                    ? "正在处理…"
                    : {
                        login: "登录",
                        register:
                          registrationStep === 1
                            ? "下一步 · 设置密保"
                            : "注册并登录",
                        reset: "重置密码",
                        password: "保存新密码",
                        security: "保存密保问题",
                      }[mode]}
                </button>
                {mode === "register" && registrationStep === 2 && (
                  <button
                    type="button"
                    className="text-button registration-back"
                    disabled={account.busy}
                    onClick={() => setRegistrationStep(1)}
                  >
                    ← 返回账号信息
                  </button>
                )}
                {editing && (
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
