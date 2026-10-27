"use client";
export default function PageError({ reset }) {
  return (
    <div className="portal-empty content-shell" role="alert">
      <h1>页面暂时无法加载</h1>
      <p>资料服务可能暂时不可用，请稍后重试。</p>
      <button className="solid-button" onClick={reset}>
        重新加载
      </button>
    </div>
  );
}
