export default function AnimePoster({ anime, number }) {
  return (
    <div className={`poster scene-${anime.scene}`} aria-hidden="true">
      <span className="poster-grain" /><span className="poster-disc" />
      <span className="poster-hill hill-back" /><span className="poster-hill hill-front" />
      <span className="poster-line" /><span className="poster-kicker">{anime.kicker}</span>
      <span className="poster-lettering">{anime.lettering}</span>
      <span className="poster-number">{String(number).padStart(2, "0")}</span>
    </div>
  );
}
