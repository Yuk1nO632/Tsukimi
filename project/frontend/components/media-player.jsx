"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import PlayerIcon from "./player-icon";

function formatTime(value) {
  if (!Number.isFinite(value) || value < 0) return "00:00";
  const seconds = Math.floor(value);
  return `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
}

export default function MediaPlayer({ media, poster, label, wide, onWide, onRetry, onFindSource, onNextLine, nextHref, autoPlay, initialMuted = false, active, globalKeyboard = false, initialPosition = 0, onProgress }) {
  const progressCallback = useRef(onProgress);
  progressCallback.current = onProgress;
  const startedRef = useRef(false);
  const restoredRef = useRef(false);
  function reportProgress(force = false, complete = false) {
    const video = videoRef.current;
    if (
      !progressCallback.current || !startedRef.current || !restoredRef.current ||
      media.isTest || !video || !Number.isFinite(video.duration) || video.duration <= 0
    ) return;
    progressCallback.current({
      position: video.currentTime,
      duration: video.duration,
      completed: complete || video.ended,
    }, force);
  }
  useEffect(() => {
    const video = videoRef.current;
    return () => {
      if (video && progressCallback.current && startedRef.current && restoredRef.current && !media.isTest && Number.isFinite(video.duration) && video.duration > 0)
        progressCallback.current({ position: video.currentTime, duration: video.duration, completed: video.ended }, true);
    };
  }, [media.isTest]);
  const frameRef = useRef(null);
  const videoRef = useRef(null);
  const controlsRef = useRef(null);
  const hideTimer = useRef(null);
  const clickTimer = useRef(null);
  const controlsHovered = useRef(false);
  const touchReveal = useRef(false);
  const [playing, setPlaying] = useState(false);
  const [hasFrame, setHasFrame] = useState(false);
  const [ended, setEnded] = useState(false);
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [volume, setVolume] = useState(1);
  const [muted, setMuted] = useState(initialMuted);
  const [speed, setSpeed] = useState(1);
  const [waiting, setWaiting] = useState(false);
  const [videoError, setVideoError] = useState("");
  const [notice, setNotice] = useState("");
  const [controlsVisible, setControlsVisible] = useState(true);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const available = media.status === "ready" && !!media.url;
  const overlay = !available || !!videoError;
  const shouldAutoPlay = autoPlay ?? !media.isTest;
  const initialLoading = media.status === "loading" || (shouldAutoPlay && active !== false && available && !hasFrame && !videoError);

  const revealControls = useCallback(() => {
    setControlsVisible(true);
    window.clearTimeout(hideTimer.current);
    hideTimer.current = window.setTimeout(() => {
      const video = videoRef.current;
      const focused = document.activeElement;
      const keyboardFocus = controlsRef.current?.contains(focused) && focused?.matches(":focus-visible");
      if (video && !video.paused && !video.ended && !controlsHovered.current && !keyboardFocus) setControlsVisible(false);
    }, 2600);
  }, []);

  useEffect(() => {
    if (playing && !waiting && !overlay) revealControls();
    else { window.clearTimeout(hideTimer.current); setControlsVisible(true); }
    return () => window.clearTimeout(hideTimer.current);
  }, [playing, waiting, overlay, revealControls]);
  useEffect(() => {
    const sync = () => { setIsFullscreen(document.fullscreenElement === frameRef.current); revealControls(); };
    document.addEventListener("fullscreenchange", sync);
    return () => { document.removeEventListener("fullscreenchange", sync); window.clearTimeout(clickTimer.current); };
  }, [revealControls]);
  useEffect(() => {
    if (!notice) return;
    const timer = window.setTimeout(() => setNotice(""), 3200);
    return () => window.clearTimeout(timer);
  }, [notice]);

  useEffect(() => {
    const video = videoRef.current;
    if (!available || !video) return;
    // Homepage previews suspend the actual source, including HLS segment downloads.
    // Existing watch players omit active and keep their original loading behavior.
    if (active === false) {
      video.pause();
      video.removeAttribute("src");
      video.load();
      return;
    }
    let disposed = false;
    let hls = null;
    if (active !== undefined && media.format !== "hls") video.src = media.url;
    const startPlayback = () => {
      if (!shouldAutoPlay || disposed) return;
      video.play().catch((error) => {
        if (!disposed && error.name !== "AbortError")
          setNotice("自动播放未开始，请点击画面中的播放按钮。");
      });
    };
    video.addEventListener("canplay", startPlayback, { once: true });
    if (media.format === "hls") {
      if (video.canPlayType("application/vnd.apple.mpegurl")) video.src = media.url;
      else {
        import("hls.js").then(({ default: Hls }) => {
          if (disposed) return;
          if (!Hls.isSupported()) { setVideoError("当前浏览器不支持这条 HLS 线路，请切换线路。"); return; }
          hls = new Hls({ enableWorker: true, lowLatencyMode: false });
          hls.on(Hls.Events.ERROR, (_event, data) => {
            if (data.fatal && !disposed) { setPlaying(false); setWaiting(false); setVideoError("HLS 视频读取失败，请重试或切换线路。"); }
          });
          hls.loadSource(media.url);
          hls.attachMedia(video);
        }).catch(() => { if (!disposed) setVideoError("暂时无法加载 HLS 播放组件，请刷新后重试。"); });
      }
    }
    if (video.readyState >= 3) startPlayback();
    const timer = window.setTimeout(() => {
      if (video.readyState === 0 && !video.error) setVideoError("视频加载时间较长，请重试或切换线路。");
    }, 25000);
    return () => {
      disposed = true;
      window.clearTimeout(timer);
      video.removeEventListener("canplay", startPlayback);
      hls?.destroy();
      video.pause();
      if (active !== undefined) {
        video.removeAttribute("src");
        video.load();
      }
    };
  }, [available, media.url, media.format, active, shouldAutoPlay]);

  async function togglePlay() {
    const video = videoRef.current;
    if (!video || !available || videoError) return;
    revealControls();
    if (!video.paused) { video.pause(); return; }
    if (video.ended) video.currentTime = 0;
    setNotice("");
    try { await video.play(); }
    catch (error) { if (error.name !== "AbortError") setNotice("浏览器暂未开始播放，请再次点击播放，或重试来源。"); }
  }
  function seek(value) {
    const video = videoRef.current;
    if (!video || !Number.isFinite(video.duration)) return;
    startedRef.current = true;
    video.currentTime = Math.max(0, Math.min(Number(value), video.duration));
    setCurrentTime(video.currentTime);
    revealControls();
  }
  function changeVolume(value) {
    const video = videoRef.current;
    if (!video) return;
    video.volume = Math.max(0, Math.min(Number(value), 1));
    video.muted = video.volume === 0;
    setVolume(video.volume); setMuted(video.muted);
  }
  function toggleMute() {
    const video = videoRef.current;
    if (!video) return;
    video.muted = !video.muted;
    setMuted(video.muted);
  }
  function changeSpeed(value) {
    if (!videoRef.current) return;
    videoRef.current.playbackRate = Number(value);
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
  useEffect(() => {
    if (!globalKeyboard) return;
    const handlePageKey = (event) => {
      if (event.defaultPrevented || frameRef.current?.contains(event.target)) return;
      onKeyDown(event);
    };
    document.addEventListener("keydown", handlePageKey);
    return () => document.removeEventListener("keydown", handlePageKey);
  }, [globalKeyboard, onKeyDown]);

  function onKeyDown(event) {
    if (!available || videoError || active === false || !(event.target instanceof Element)) return;
    const key = event.key.toLowerCase();
    const arrow = ["arrowleft", "arrowright", "arrowup", "arrowdown"].includes(key);
    const seekArrow = event.target.matches(".seek-range") &&
      (key === "arrowleft" || key === "arrowright");
    const playerButtonKey = frameRef.current?.contains(event.target) &&
      event.target.closest("button") && (arrow || ["k", "m", "f"].includes(key));
    const control = event.target.closest('input,textarea,select,button,a,summary,[role="textbox"],[contenteditable]:not([contenteditable="false"])');
    if (event.altKey || event.ctrlKey || event.metaKey ||
      (control && !seekArrow && !playerButtonKey)) return;
    if (![" ", "k", "arrowleft", "arrowright", "arrowup", "arrowdown", "m", "f"].includes(key)) return;
    event.preventDefault();
    if (event.repeat && !arrow) return;
    revealControls();
    if (key === " " || key === "k") togglePlay();
    else if (key === "f") fullscreen();
    else if (key === "m") toggleMute();
    else if (key === "arrowleft" || key === "arrowright") {
      const offset = key === "arrowright" ? 5 : -5;
      seek((videoRef.current?.currentTime || 0) + offset);
      setNotice(offset > 0 ? "快进 5 秒" : "后退 5 秒");
    } else changeVolume((videoRef.current?.volume || 0) + (key === "arrowup" ? 0.05 : -0.05));
  }
  function clickCanvas(event) {
    if (event.target !== videoRef.current && event.target !== event.currentTarget) return;
    if (touchReveal.current) { touchReveal.current = false; return; }
    frameRef.current?.focus({ preventScroll: true });
    window.clearTimeout(clickTimer.current);
    if (event.detail === 1) clickTimer.current = window.setTimeout(togglePlay, 220);
  }
  function onError() {
    setPlaying(false); setWaiting(false);
    const code = videoRef.current?.error?.code;
    setVideoError(code === 3 ? "视频暂时无法解码，请重试或切换线路。" : code === 4 ? "视频地址或格式暂不可用，请重试或切换线路。" : "视频读取失败，请检查网络后重试。");
  }
  async function findSource() {
    if (document.fullscreenElement === frameRef.current) await document.exitFullscreen().catch(() => {});
    onFindSource?.();
  }
  async function changeLine() {
    if (document.fullscreenElement === frameRef.current) await document.exitFullscreen().catch(() => {});
    onNextLine?.();
  }
  const heading = videoError ? "暂时无法播放这一集" : media.status === "loading" ? "正在匹配并加载来源" : media.status === "unmatched" ? "先为这部番找到播放来源" : media.reason === "no_resources" ? "已匹配作品，暂无播放资源" : media.reason === "episode_missing" ? "来源目录暂缺这一集" : "来源暂时没有准备好";
  const percent = duration ? Math.min(100, currentTime / duration * 100) : 0;

  return <div className={`player-frame${controlsVisible ? " controls-visible" : " controls-hidden"}${initialLoading ? " is-initial-loading" : ""}`} ref={frameRef} tabIndex={0} role="region" aria-label={`${label}播放器，空格播放暂停，方向键快进或调节音量，F 全屏`} onKeyDown={onKeyDown} onPointerMove={revealControls} onPointerDown={(event) => { touchReveal.current = event.pointerType === "touch" && !controlsVisible && event.target === videoRef.current; revealControls(); }} onPointerLeave={() => { controlsHovered.current = false; revealControls(); }}>
    <div className="player-canvas" onClick={clickCanvas} onDoubleClick={(event) => { if (event.target === videoRef.current || event.target === event.currentTarget) { window.clearTimeout(clickTimer.current); fullscreen(); } }}>
      {available && <video ref={videoRef} className="actual-video" preload="metadata" autoPlay={active !== false && shouldAutoPlay} muted={muted} playsInline poster={poster} src={active === undefined && media.format !== "hls" ? media.url : undefined} aria-label={label}
        onLoadedData={() => setHasFrame(true)} onEmptied={() => setHasFrame(false)}
        onLoadedMetadata={(event) => {
          const video = event.currentTarget;
          setDuration(video.duration); setVideoError("");
          if (!restoredRef.current && Number.isFinite(video.duration)) {
            if (initialPosition > 0) video.currentTime = Math.min(initialPosition, Math.max(0, video.duration - 1));
            restoredRef.current = true;
          }
        }}
        onDurationChange={(event) => setDuration(Number.isFinite(event.currentTarget.duration) ? event.currentTarget.duration : 0)}
        onTimeUpdate={(event) => { setCurrentTime(event.currentTarget.currentTime); reportProgress(); }}
        onSeeked={() => reportProgress(true)}
        onPlay={() => { startedRef.current = true; setPlaying(true); setEnded(false); }} onPause={() => { setPlaying(false); reportProgress(true); }}
        onWaiting={() => setWaiting(true)} onPlaying={() => { setWaiting(false); setPlaying(true); }}
        onCanPlay={() => setWaiting(false)} onEnded={() => { setPlaying(false); setWaiting(false); setEnded(true); reportProgress(true, true); }}
        onVolumeChange={(event) => { setVolume(event.currentTarget.volume); setMuted(event.currentTarget.muted); }}
        onRateChange={(event) => setSpeed(event.currentTarget.playbackRate)} onError={onError} />}
      <div className="player-topline"><span className="player-watermark">☾ TSUKIMI</span><span className="player-now-title">{label}</span></div>
      {media.isTest && <span className="test-video-label">测试短片 · 非番剧正片</span>}
      {initialLoading ? <div className="player-buffering" role="status"><span className="loading-dot" />{media.status === "loading" ? "正在加载来源…" : "正在加载视频…"}</div> : overlay ? <div className="player-empty"><span className={`player-empty-icon${media.status === "loading" ? " is-loading" : ""}`} aria-hidden="true"><PlayerIcon name={media.status === "loading" ? "refresh" : "play"} size={30} /></span><h2>{heading}</h2><p>{videoError || media.message || "正在获取这一集的播放地址，请稍候。"}</p>{media.status !== "loading" && <div className="player-empty-actions">{onNextLine && <button className="player-retry" type="button" onClick={changeLine}>换一条线路</button>}<button className="player-retry" type="button" onClick={onRetry}>重新加载</button><button className="player-find-source" type="button" onClick={findSource}>搜索 / 更换来源</button></div>}</div>
        : ended ? <div className="player-ended"><span>本次播放已结束</span><div><button type="button" onClick={togglePlay}>重新播放</button>{nextHref && !media.isTest && <Link href={nextHref} scroll={false}>下一集 <PlayerIcon name="next" size={16} /></Link>}</div></div>
        : !playing && !initialLoading && <button className="player-center-play" type="button" onClick={togglePlay} aria-label="开始播放视频"><PlayerIcon name="play" size={32} /></button>}
      {!overlay && !initialLoading && waiting && <div className="player-buffering" role="status"><span className="loading-dot" />正在缓冲…</div>}
    </div>
    {notice && <div className="player-toast" role="status">{notice}</div>}
    <div className="player-controls real-player-controls" ref={controlsRef} onPointerEnter={() => { controlsHovered.current = true; revealControls(); }} onPointerLeave={() => { controlsHovered.current = false; revealControls(); }} onFocusCapture={revealControls} onBlurCapture={revealControls}>
      <input className="seek-range" aria-label="播放进度" title="左右方向键快进或后退 5 秒" aria-valuetext={`${formatTime(currentTime)}，总时长 ${formatTime(duration)}`} style={{ "--seek-fill": `${percent}%` }} type="range" min="0" max={duration || 1} step="0.1" value={Math.min(currentTime, duration || 1)} disabled={!available || !duration || !!videoError} onChange={(event) => seek(event.target.value)} />
      <button type="button" disabled={!available || !!videoError} onClick={togglePlay} aria-label={playing ? "暂停视频" : "播放视频"} title="播放 / 暂停（空格）"><PlayerIcon name={playing ? "pause" : "play"} /></button>
      {nextHref && !media.isTest && <Link className="player-next" href={nextHref} scroll={false} aria-label="播放下一集" title="下一集"><PlayerIcon name="next" size={18} /></Link>}
      <span className="player-time">{formatTime(currentTime)} <i>/ {formatTime(duration)}</i></span>
      <div className="player-volume"><button type="button" onClick={toggleMute} disabled={!available} aria-label={muted ? "取消静音" : "静音视频"} title="静音（M）"><PlayerIcon name={muted || volume === 0 ? "mute" : "volume"} /></button><input aria-label="音量" type="range" min="0" max="1" step="0.05" value={muted ? 0 : volume} disabled={!available} onChange={(event) => changeVolume(event.target.value)} /></div>
      <select aria-label="播放速度" title="播放倍速" value={speed} disabled={!available} onChange={(event) => changeSpeed(event.target.value)}>{[0.5, 1, 1.25, 1.5, 2].map((rate) => <option key={rate} value={rate}>{rate === 1 ? "倍速" : `${rate}×`}</option>)}</select>
      {onWide && <button className="player-wide" type="button" aria-label={wide ? "退出宽屏" : "宽屏模式"} aria-pressed={wide} title={wide ? "退出宽屏" : "宽屏模式"} onClick={onWide}><PlayerIcon name="wide" /></button>}
      <button type="button" onClick={fullscreen} aria-label={isFullscreen ? "退出播放器全屏" : "播放器全屏"} title={isFullscreen ? "退出全屏（F / Esc）" : "全屏（F）"}><PlayerIcon name={isFullscreen ? "restore" : "fullscreen"} /></button>
    </div>
  </div>;
}
