"use client";

import { useEffect, useRef, useState } from "react";

function formatTime(value) {
  if (!Number.isFinite(value) || value < 0) return "00:00";
  const seconds = Math.floor(value);
  const minutes = Math.floor(seconds / 60);
  return `${String(minutes).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
}

export default function MediaPlayer({ media, poster, label, wide, onWide, onRetry }) {
  const frameRef = useRef(null);
  const videoRef = useRef(null);
  const [playing, setPlaying] = useState(false);
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [volume, setVolume] = useState(1);
  const [muted, setMuted] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [waiting, setWaiting] = useState(false);
  const [videoError, setVideoError] = useState("");
  const [notice, setNotice] = useState("");
  const available = media.status === "ready" && !!media.url;

  useEffect(() => {
    const video = videoRef.current;
    if (!available || !video) return;
    let disposed = false;
    let hls = null;
    if (media.format === "hls") {
      if (video.canPlayType("application/vnd.apple.mpegurl")) video.src = media.url;
      else {
        import("hls.js").then(({default: Hls}) => {
          if (disposed) return;
          if (!Hls.isSupported()) { setVideoError("当前浏览器不支持这条 HLS 线路，请切换线路。"); return; }
          hls = new Hls({ enableWorker: true, lowLatencyMode: false });
          hls.on(Hls.Events.ERROR, (_event, data) => {
            if (data.fatal && !disposed) {setPlaying(false);setWaiting(false);setVideoError("HLS 视频读取失败，请重试或切换线路。");}
          });
          hls.loadSource(media.url);
          hls.attachMedia(video);
        }).catch(() => {if (!disposed) setVideoError("暂时无法加载 HLS 播放组件，请刷新后重试。");});
      }
    }
    const timer = window.setTimeout(() => {
      if (video.readyState === 0 && !video.error) setVideoError("视频加载时间较长，请重试或切换线路。");
    }, 25000);
    return () => { disposed = true; window.clearTimeout(timer); hls?.destroy(); video.pause(); };
  }, [available, media.url, media.format]);

  async function togglePlay() {
    const video = videoRef.current;
    if (!video || !available || videoError) return;
    if (!video.paused) { video.pause(); return; }
    if (video.ended) video.currentTime = 0;
    setNotice("");
    try { await video.play(); }
    catch (error) {
      if (error.name !== "AbortError") setNotice("浏览器暂未开始播放，请再次点击播放，或重试来源。");
    }
  }
  function seek(value) {
    const video = videoRef.current;
    if (!video || !Number.isFinite(video.duration)) return;
    const position = Math.max(0, Math.min(Number(value), video.duration));
    video.currentTime = position;
    setCurrentTime(position);
  }
  function changeVolume(value) {
    const video = videoRef.current;
    if (!video) return;
    const next = Number(value);
    video.volume = next;
    video.muted = next === 0;
    setVolume(next); setMuted(video.muted);
  }
  function toggleMute() {
    const video = videoRef.current;
    if (!video) return;
    video.muted = !video.muted;
    setMuted(video.muted);
  }
  function changeSpeed(value) {
    const video = videoRef.current;
    if (!video) return;
    video.playbackRate = Number(value);
    setSpeed(Number(value));
  }
  async function fullscreen() {
    try {
      if (document.fullscreenElement === frameRef.current) await document.exitFullscreen();
      else if (frameRef.current?.requestFullscreen) await frameRef.current.requestFullscreen();
      else if (videoRef.current?.webkitEnterFullscreen) videoRef.current.webkitEnterFullscreen();
      else throw new Error("unavailable");
    } catch { setNotice("当前浏览器暂时无法全屏，可以使用宽屏模式。"); }
  }
  function onError() {
    setPlaying(false); setWaiting(false);
    const code = videoRef.current?.error?.code;
    setVideoError(code === 3 ? "视频暂时无法解码，请重试或切换线路。" : code === 4 ? "视频地址或格式暂不可用，请重试或切换线路。" : "视频读取失败，请检查网络后重试。");
  }
  const overlay = !available || !!videoError;
  const heading = videoError ? "视频暂时无法播放" : media.status === "loading" ? "正在寻找这一集" : media.status === "unmatched" ? "为故事选择一个来源" : "这一集暂时无法播放";

  return <>
    <div className="player-frame" ref={frameRef}>
      <div className="player-canvas">
        {available && <video ref={videoRef} className="actual-video" preload="metadata" playsInline poster={poster} src={media.format === "hls" ? undefined : media.url} aria-label={label}
          onLoadedMetadata={(event) => {setDuration(event.currentTarget.duration); setVideoError("");}}
          onDurationChange={(event) => setDuration(Number.isFinite(event.currentTarget.duration) ? event.currentTarget.duration : 0)}
          onTimeUpdate={(event) => setCurrentTime(event.currentTarget.currentTime)}
          onPlay={() => setPlaying(true)} onPause={() => setPlaying(false)}
          onWaiting={() => setWaiting(true)} onPlaying={() => {setWaiting(false); setPlaying(true);}}
          onCanPlay={() => setWaiting(false)} onEnded={() => {setPlaying(false); setWaiting(false);}}
          onVolumeChange={(event) => {setVolume(event.currentTarget.volume);setMuted(event.currentTarget.muted);}}
          onRateChange={(event) => setSpeed(event.currentTarget.playbackRate)} onError={onError} />}
        <span className="player-watermark">☾ TSUKIMI</span>
        {media.isTest && <span className="test-video-label">测试短片 · 非番剧正片</span>}
        {overlay ? <div className="player-empty"><span className="player-empty-icon" aria-hidden="true">{media.status === "loading" ? "◌" : "▷"}</span><h2>{heading}</h2><p>{videoError || media.message || "请稍候…"}</p>{media.status !== "loading" && <button className="player-retry" type="button" onClick={onRetry}>重新加载来源</button>}</div>
          : !playing && <button className="player-center-play" type="button" onClick={togglePlay} aria-label="开始播放视频">▶</button>}
        {!overlay && waiting && <div className="player-buffering" role="status">正在缓冲…</div>}
      </div>
      <div className="player-controls real-player-controls">
        <input className="seek-range" aria-label="播放进度" type="range" min="0" max={duration || 1} step="0.1" value={Math.min(currentTime,duration || 1)} disabled={!available || !duration || !!videoError} onChange={(event) => seek(event.target.value)} />
        <button type="button" disabled={!available || !!videoError} onClick={togglePlay} aria-label={playing ? "暂停视频" : "播放视频"}>{playing ? "Ⅱ" : "▶"}</button>
        <span className="player-time">{formatTime(currentTime)} <i>/ {formatTime(duration)}</i></span>
        <div className="player-volume"><button type="button" onClick={toggleMute} disabled={!available} aria-label={muted ? "取消静音" : "静音视频"}>{muted ? "静音" : "音量"}</button><input aria-label="音量" type="range" min="0" max="1" step="0.05" value={muted ? 0 : volume} disabled={!available} onChange={(event) => changeVolume(event.target.value)} /></div>
        <select aria-label="播放速度" value={speed} disabled={!available} onChange={(event) => changeSpeed(event.target.value)}>{[0.5,1,1.25,1.5,2].map((rate) => <option key={rate} value={rate}>{rate}×</option>)}</select>
        <button type="button" aria-pressed={wide} onClick={onWide}>{wide ? "常规" : "宽屏"}</button>
        <button type="button" onClick={fullscreen} aria-label="播放器全屏">⛶</button>
      </div>
    </div>
    {notice && <p className="player-message" role="status">{notice}</p>}
  </>;
}
