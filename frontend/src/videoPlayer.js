import Viewer from "./viewer.js";
import * as utils from "./utils.js";

/**
 * Custom video player class
 */
export default class VideoPlayer {
  /**
   * Called to construct a new video player
   * @param {Viewer} viewer The viewer containing this video player
   */
  constructor(viewer) {
    this._viewer = viewer;

    this._controls = document.getElementById("video-controls");
    this._duration = document.getElementById("duration");
    this._fullscreenButton = document.getElementById("fullscreen-button");
    this._fullscreenIcons = this._fullscreenButton.querySelectorAll("use");
    this._playButton = document.getElementById("play");
    this._playIcons = document.querySelectorAll("#playback-icons use");
    this._progressBar = document.getElementById("progress-bar");
    this._seek = document.getElementById("seek");
    this._seekTooltip = document.getElementById("seek-tooltip");
    this._timeElapsed = document.getElementById("time-elapsed");
    this._video = document.getElementById("video");
    this._volume = document.getElementById("volume");
    this._volumeButton = document.getElementById("volume-button");
    this._volumeHigh = document.querySelector('use[href="#volume-high"]');
    this._volumeIcons = document.querySelectorAll("#volume-button use");
    this._volumeLow = document.querySelector('use[href="#volume-low"]');
    this._volumeMute = document.querySelector('use[href="#volume-mute"]');

    // Initialize event listeners
    document.addEventListener("fullscreenchange", () => this.updateFullscreenButton());

    this._controls.addEventListener("mouseenter", () => {
      this.showControls();
      clearTimeout(this._hideControlsTimeout);
    });
    this._controls.addEventListener("mouseleave", () => {
      if (this._hideControlsTimeout) clearTimeout(this._hideControlsTimeout);
      this._hideControlsTimeout = setTimeout(() => this.hideControls(), 2000);
    });
    this._fullscreenButton.addEventListener("click", () => this._viewer.toggleFullScreen());
    this._playButton.addEventListener("click", () => this.togglePlay());
    this._seek.addEventListener("input", (e) => this.skipTo(e));
    this._seek.addEventListener("mousemove", (e) => this.updateSeekTooltip(e));
    this._video.addEventListener("loadedmetadata", () => this.videoLoaded());
    this._video.addEventListener("play", () => this.updatePlayButton());
    this._video.addEventListener("pause", () => this.updatePlayButton());
    this._video.addEventListener("seeked", () => this.seeked());
    this._video.addEventListener("timeupdate", () => this.updateTimeElapsed());
    this._video.addEventListener("volumechange", () => this.updateVolumeIcon());
    this._video.addEventListener("mousemove", () => {
      this.showControls();
      if (this._hideControlsTimeout) clearTimeout(this._hideControlsTimeout);
      this._hideControlsTimeout = setTimeout(() => this.hideControls(), 2000);
    });
    this._volume.addEventListener("input", () => this.updateVolume());
    this._volumeButton.addEventListener("click", () => this.toggleMute());

    this._video.requestVideoFrameCallback((_, meta) => this.ticker(meta));
  }

  /*****************************************************************************
  **                                METHODS                                   **
  *****************************************************************************/

  /**
   * Get time parts for a value based on whether FPS is available
   * @param {Number} value The value in seconds to get time parts for
   * @returns An array of time parts representing the elapsed time in the video
   */
  getTimeParts(value) {
    let timeParts;

    if (this._fps) {
      const totalFrames = Math.round(this._video.duration * this._fps);
      timeParts = utils.formatTimeInFrames(totalFrames, this._fps);
      this.updateTimestamp(timeParts, this._duration);
      timeParts = utils.formatTimeInFrames(Math.round(value * this._fps), this._fps);
    } else {
      timeParts = utils.formatTimeInSeconds(Math.round(value));
    }

    return timeParts;
  }

  /**
   * Seek to a particular point in the video
   * @param {Number} seconds Seconds to seek to
   * @param {Number} frames Frames to seek to
   */
  seekTo(seconds, frames) {
    if (this._fps && frames !== undefined) {
      seconds = this.currentTime + (frames / this._fps);
    }

    seconds = Math.min(Math.max(0, seconds), this._video.duration);

    this.pause();
    this.skipTo({
      target: {
        value: seconds
      }
    });
  }

  /**
   * Called to load a video into the video player
   * @param {String} video The file path to the video
   */
  loadVideo(video) {
    this._fps = NaN;
    this._fpsRounder = [];
    this._frameNotSeeked = true;

    this._video.src = video;
    this._controls.classList.remove("hidden");
  }

  /**
   * Called to pause the video
   */
  pause() {
    this._video.pause();
    this.showControls();
  }

  /**
   * Called to unload a video from the player
   */
  unloadVideo() {
    this._video.src = "";
    this._controls.classList.add("hidden");
  }

  /**
   * Called to update the timestamp in a time element
   * @param {Number[]} timeParts Array of time parts starting with hours
   * @param {HTMLTimeElement} time Time element to update
   */
  updateTimestamp(timeParts, time) {
    time.innerText = timeParts
      .filter((n, i) => n > 0 || i > 0)
      .map(n => String(n).padStart(2, "0"))
      .join(":");

    if (time.nodeName === "TIME") {
      time.setAttribute("datetime", `PT${timeParts[0]}H${timeParts[1]}M${timeParts[2]}S`);
    }
  }

  /*****************************************************************************
  **                               HANDLERS                                   **
  *****************************************************************************/

  /**
   * Hides the video controls
   */
  hideControls() {
    if (this._video.paused) {
      return;
    }

    this._controls.classList.add('hide');
  }

  /**
   * Called when the video is seeked
   */
  seeked() {
    // This is necessary, since seeking the video desyncs the metadata, causing
    // confusion to the fps calculator
    this._fpsRounder.pop();
    this._frameNotSeeked = false;
  }

  /**
   * Shows the video controls
   */
  showControls() {
    this._controls.classList.remove('hide');
  }

  /**
   * Function to skip video playback to a certain point
   * @param {InputEvent} e Event fired when input is changed
   */
  skipTo(e) {
    const skipTo = e.target.dataset && e.target.dataset.seek ? e.target.dataset.seek : e.target.value;
    this._video.currentTime = skipTo;
    this._progressBar.value = skipTo;
    this._seek.value = skipTo;

    this.seeked();
  }

  /**
   * Ticker called to accurately calculate the framerate of a video
   * @param {Object} meta Metadata object passed by videoFrameCallback
   */
  ticker(meta) {
    const mediaTimeDiff = Math.abs(meta.mediaTime - this._lastMediaTime);
    const frameNumDiff = Math.abs(meta.presentedFrames - this._lastFrameNum);
    const diff = mediaTimeDiff / frameNumDiff;

    if (diff && diff < 1 && this._frameNotSeeked && document.hasFocus()) {
      this._fpsRounder.push(diff);
      this._fps = Math.round(1 / this.fpsAverage) / this._video.playbackRate;
    }

    this._frameNotSeeked = true;
    this._lastMediaTime = meta.mediaTime;
    this._lastFrameNum = meta.presentedFrames;

    if (this._fpsRounder.length < 50) {
      this._video.requestVideoFrameCallback((_, meta) => this.ticker(meta));
    }
  }

  /**
   * Called to toggle whether the video is muted
   */
  toggleMute() {
    this._video.muted = !this._video.muted;

    if (this._video.muted) {
      this._volume.setAttribute("data-volume", this._volume.value);
      this._volume.value = 0;
    } else {
      this._volume.value = this._volume.dataset.volume;
    }
  }

  /**
   * Called to toggle the play state of the video
   */
  togglePlay() {
    if (this._video.paused || this._video.ended) {
      this._video.play();
    } else {
      this._video.pause();
    }
  }

  /**
   * Called to update full screen button when full screen state changes
   */
  updateFullscreenButton() {
    this._fullscreenIcons.forEach(i => i.classList.toggle("hidden"));

    if (document.fullscreenElement) {
      this._fullscreenButton.setAttribute("data-title", "Full screen (f)");
    } else {
      this._fullscreenButton.setAttribute("data-title", "Exit full screen (f)");
    }
  }

  /**
   * Called to update the appearance of the play button
   */
  updatePlayButton() {
    this._playIcons.forEach(icon => icon.classList.toggle("hidden"));

    if (this._video.paused) {
      this._playButton.setAttribute("data-title", "Play (k)");
    } else {
      this._playButton.setAttribute("data-title", "Pause (k)");
    }
  }

  /**
   * Called when the cursor is over the progress bar
   * @param {MouseEvent} e The mouse event passed when the cursor is hovering
   */
  updateSeekTooltip(e) {
    const skipTo = (e.offsetX / e.target.clientWidth) * parseInt(e.target.getAttribute("max"), 10);
    this._seek.setAttribute("data-seek", Math.round(skipTo));
    this.updateTimestamp(this.getTimeParts(skipTo), this._seekTooltip);
    const bb = this._video.getBoundingClientRect();
    this._seekTooltip.style.left = `${e.pageX - bb.left}px`;
  }

  /**
   * Called to update the elapsed timestamp
   */
  updateTimeElapsed() {
    this.updateTimestamp(this.getTimeParts(this._video.currentTime), this._timeElapsed);

    const currentTime = Math.floor(this._video.currentTime);
    this._seek.value = currentTime;
    this._progressBar.value = currentTime;
  }

  /**
   * Called to update the video's volume
   */
  updateVolume() {
    this._video.muted = false;
    this._video.volume = this._volume.value;
  }

  /**
   * Updates the volume icon to reflect the volume of the video
   */
  updateVolumeIcon() {
    this._volumeIcons.forEach(icon => {
      icon.classList.add("hidden");
    });

    this._volumeButton.setAttribute("data-title", "Mute (m)")

    if (this._video.muted || this._video.volume === 0) {
      this._volumeMute.classList.remove("hidden");
      this._volumeButton.setAttribute("data-title", "Unmute (m)")
    } else if (this._video.volume > 0 && this._video.volume <= 0.5) {
      this._volumeLow.classList.remove("hidden");
    } else {
      this._volumeHigh.classList.remove("hidden");
    }
  }

  /**
   * Called when the video's metadata is initially loaded
   */
  videoLoaded() {
    const videoDuration = Math.round(this._video.duration);
    this._seek.setAttribute("max", videoDuration);
    this._progressBar.setAttribute("max", videoDuration);
    const timeParts = utils.formatTimeInSeconds(videoDuration);
    this.updateTimestamp(timeParts, this._duration);
  }

  /*****************************************************************************
  **                               GETTERS                                    **
  *****************************************************************************/

  /**
   * @returns A number representing the current time of the video in seconds
   */
  get currentTime() {
    return this._video.currentTime;
  }

  /**
   * @returns A number representing the average FPS of the video
   */
  get fpsAverage() {
    return this._fpsRounder.reduce((a, b) => a + b) / this._fpsRounder.length;
  }

  /**
   * @returns Whether the video is paused
   */
  get paused() {
    return this._video.paused;
  }
}
