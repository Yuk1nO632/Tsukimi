export function LoadFailure({ error, retry }) {
  return (
    <div className="portal-empty" role="alert">
      <h3>暂时无法加载</h3>
      <p>{error}</p>
      <button className="outline-button" type="button" onClick={retry}>
        重新加载
      </button>
    </div>
  );
}
export function SkeletonGrid({ count = 6 }) {
  return (
    <div
      className="anime-grid portal-grid skeleton-grid"
      role="status"
      aria-label="正在加载番剧"
    >
      {Array.from({ length: count }, (_, index) => (
        <div key={index}>
          <div className="skeleton-poster" />
          <div className="skeleton-line" />
        </div>
      ))}
    </div>
  );
}
