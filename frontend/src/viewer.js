import VideoPlayer from "./videoPlayer.js";
import * as utils from "./utils.js";

const COLORS = [
  "185, 219, 63",
  "221, 55, 83",
  "127, 67, 183",
  "51, 94, 224",
  "244, 206, 17",
  "99, 252, 255",
  "70, 233, 242",
  "7, 130, 62",
  "242, 212, 19",
  "223, 50, 229",
  "47, 183, 65",
  "216, 121, 73",
  "45, 49, 173",
  "49, 206, 196",
  "194, 201, 2",
  "81, 194, 198"
];

/**
 * Viewer class containing all the functionality to manage the viewport
 */
export default class Viewer {
  // Maximum scale we allow (3x the original size)
  static MAX_SCALE = 3;
  static ZOOM_INCREMENT = 0.04;

  constructor() {
    this._canvas = document.getElementById("canvas");
    this._image = document.getElementById("image");
    this._media = document.getElementById("media");
    this._video = document.getElementById("video");
    this._viewer = document.getElementById("viewer");

    this.videoPlayer = new VideoPlayer(this);
    this.ctx = this._canvas.getContext("2d");

    this._mediaHeight = 0;
    this._mediaWidth = 0;
    this._viewerHeight = 0;
    this._viewerWidth = 0;

    this._aspectRatio = 1;
    this._scale = 1;
    this._minScale = 1;

    // Data
    this._data = {};

    // State
    this._drawingRect = false;
    this._panning = false;

    // Register listeners
    window.addEventListener("resize", () => this.resizeHandler());
    this._canvas.addEventListener("click", (e) => this.canvasClickHandler(e));
    this._video.addEventListener("loadedmetadata", (e) => this.videoLoadHandler(e), false);
    this._viewer.addEventListener("mousemove", (e) => this.mouseMoveHandler(e));
    this._viewer.addEventListener("wheel", (e) => this.zoom(e));

    // Initial load
    this.cacheViewerDimensions();
    this.resizeCanvas();

    requestAnimationFrame(() => this.drawFrame());
  }

  /*****************************************************************************
  **                                METHODS                                   **
  *****************************************************************************/

  /**
   * Private helper to check if a coordinate pair is within media limits
   * @param {Number} x X position to check
   * @param {Number} y Y position to check
   * @returns Whether x and y are in the current media limits
   */
  _inLimits(x, y) {
    const { topLimit, bottomLimit, leftLimit, rightLimit } = this.limits;
    return leftLimit < x && x < rightLimit && topLimit < y && y < bottomLimit;
  }

  /**
   * Called to update the cached dimensions of the viewer
   */
  cacheViewerDimensions() {
    this._viewerHeight = this._viewer.offsetHeight;
    this._viewerWidth = this._viewer.offsetWidth;
  }

  /**
   * Called to draw a frame on the canvas
   */
  drawFrame() {
    this.ctx.clearRect(0, 0, this._viewerWidth, this._viewerHeight);

    for (let i = 0; i < this._rects.length; ++i) {
      const { x1, y1, x2, y2, hovered } = this._rects[i];
      const colorIdx = parseInt(`${(x1 % 4).toString(2)}${(y1 % 4).toString(2)}`, 2);
      let strokeAlpha = 0.5, fillAlpha = 0.25;

      if (this._drawingRect && i == this._rects.length - 1) {
        strokeAlpha = 1.0;
        fillAlpha = 0;
      } else if (hovered) {
        strokeAlpha = 1.0;
        fillAlpha = 0.75;
      }

      this.ctx.strokeStyle = `rgba(${COLORS[colorIdx]}, ${strokeAlpha})`;
      this.ctx.fillStyle = `rgba(${COLORS[colorIdx]}, ${fillAlpha})`;
      this.ctx.fillRect(x1, y1, x2 - x1, y2 - y1);
      this.ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
    }

    requestAnimationFrame(() => this.drawFrame());
  }

  /**
   * Loads the desired media from a filepath
   * @param {string} media The filepath to the media to load
   */
  loadMedia(media) {
    const lower = media.toLowerCase();
    const extension = lower.substring(media.lastIndexOf(".") + 1);
    switch (extension) {
      case "jpeg":
      case "jpg":
      case "png":
      case "tif":
        const img = new Image();
        img.onload = () => this.imageLoadHandler(img);
        img.src = media;
        this.videoPlayer.unloadVideo();
        break;
      case "mov":
      case "mp4":
        this.videoPlayer.loadVideo(media);
        this._image.src = "";
        break;
      default:
        console.error(`Unsupported filetype ${extension}`);
    }
  }

  /**
   * Called to start panning
   */
  panStart() {
    this._panning = true;
    document.body.style.cursor = "grabbing";
  }

  /**
   * Called to stop panning
   */
  panStop() {
    this._panning = false;
    document.body.style.cursor = "";
  }

  /**
   * Called to reset the position and scale of the media
   */
  resetMedia() {
    let height, width;
    let top = 0, left = 0;

    if (this._aspectRatio < this.viewerAspectRatio) {
      height = this._viewerHeight;
      width = height * this._aspectRatio;
      left = (this._viewerWidth - width) / 2;
    } else {
      width = this._viewerWidth;
      height = width / this._aspectRatio;
      top = (this._viewerHeight - height) / 2;
    }

    this._scale = height / this._mediaHeight;
    this._minScale = this._scale;

    this.mediaDimensions = [height, width];
    this.mediaPosition = [top, left];
  }

  /**
   * Called after a window resize to adjust the canvas
   */
  resizeCanvas() {
    this._canvas.height = this._viewerHeight;
    this._canvas.width = this._viewerWidth;
  }

  /**
   * Called to toggle full screen
   */
  toggleFullScreen() {
    if (document.fullscreenElement) {
      document.exitFullscreen();
    } else if (document.webkitFullscreenElement) {
      document.webkitExitFullscreen(); // Safari
    } else if (this._viewer.webkitRequestFullscreen) {
      this._viewer.webkitRequestFullscreen(); // Safari
    } else {
      this._viewer.requestFullscreen();
    }

    this.cacheViewerDimensions();
    this.resetMedia();
    const fullscreenchange = new CustomEvent("fullscreenchange");
    document.dispatchEvent(fullscreenchange);
  }

  /**
   * Called when the mousewheel is scrolled over the viewer
   * @param {WheelEvent} e Mousewheel event
   */
  zoom(e) {
    e.preventDefault();

    // Get the global cursor position
    const cur = { top: e.clientY, left: e.clientX };
    const [top, left] = this.mediaPosition;

    // Get the position of the cursor relative to the position of the media
    const curRel = { top: cur.top - top, left: cur.left - left };

    // Determine whether we are zooming in or out
    const direction = utils.clamp(e.deltaY, -1, 1) * -1;

    // Save the old scale
    const oldScale = this._scale;

    // Calculate the new scale
    this._scale = utils.clamp(
      this._scale + direction * Viewer.ZOOM_INCREMENT,
      this._minScale,
      Viewer.MAX_SCALE
    );

    if (this._scale === this._minScale) {
      this.resetMedia();
    } else {
      // Get the difference in scale
      const dS = this._scale / oldScale;

      // Actually scale the image
      const height = this._scale * this._mediaHeight;
      const width = height * this._aspectRatio;

      this.mediaDimensions = [height, width];

      // Adjust the viewport to maintain the point under the cursor
      this.mediaPosition = [
        top + (curRel.top - curRel.top * dS),
        left + (curRel.left - curRel.left * dS)
      ];
    }
  }

  /*****************************************************************************
  **                               HANDLERS                                   **
  *****************************************************************************/

  /**
   * Called to handle clicks on a canvas
   */
   canvasClickHandler(e) {
    if (this._drawingRect) {
      this._drawingRect = false;
    } else if (this._inLimits(e.clientX, e.clientY)) {
      this._drawingRect = true;
      this._rects.push({
        x1: e.clientX,
        y1: e.clientY,
        x2: e.clientX,
        y2: e.clientY
      });
    }
  }

  /**
   * Called when an image is loaded
   * @param {HTMLImageElement} img The image element used to load the image
   */
  imageLoadHandler(img) {
    this._mediaHeight = img.height;
    this._mediaWidth = img.width;
    this._aspectRatio = this._mediaWidth / this._mediaHeight;
    this._image.parentNode.replaceChild(img, this._image);
    this._image = img;
    this._image.id = "image";
    this.resetMedia();
  }

  /**
   * Called when the mouse moves
   * @param {MouseEvent} e Event fired when the mouse moves
   */
  mouseMoveHandler(e) {
    if (this._drawingRect && this._rects.length > 0) {
      const lastIdx = this._rects.length - 1;

      const { topLimit, bottomLimit, leftLimit, rightLimit } = this.limits;

      this._rects[lastIdx].x2 = Math.max(Math.min(e.clientX, rightLimit), leftLimit);
      this._rects[lastIdx].y2 = Math.max(Math.min(e.clientY, bottomLimit), topLimit);
    } else if (this._panning) {
      this.mediaPosition = [
        this._oldMediaTop + e.clientY - this._oldMouseY,
        this._oldMediaLeft + e.clientX - this._oldMouseX
      ];
    } else {
      this._oldMouseX = e.clientX;
      this._oldMouseY = e.clientY;
      [this._oldMediaTop, this._oldMediaLeft] = this.mediaPosition;
    }

    let i = 0;
    let hoveredIdx = -1;
    let area = Infinity;

    for (; i < this._rects.length; ++i) {
      let { x1, y1, x2, y2 } = this._rects[i];

      if (x1 > x2) {
        const xt = x2;
        x2 = x1;
        x1 = xt;
      }

      if (y1 > y2) {
        const yt = y2;
        y2 = y1;
        y1 = yt;
      }

      if (x1 < e.clientX && e.clientX < x2
        && y1 < e.clientY && e.clientY < y2
        && area > (x2 - x1) * (y2 - y1)) {
          hoveredIdx = i;
          area = (x2 - x1) * (y2 - y1);
      }

      this._rects[i].hovered = false;
    }

    if (hoveredIdx != -1) {
      this._rects[hoveredIdx].hovered = true;
    }
  }

  /**
   * Called when the document is resized
   */
  resizeHandler() {
    this.cacheViewerDimensions();
    this.resetMedia();
    this.resizeCanvas();
  }

  /**
   * Called when a video is loaded
   */
  videoLoadHandler() {
    this._mediaHeight = this._video.videoHeight;
    this._mediaWidth = this._video.videoWidth;
    this._aspectRatio = this._mediaWidth / this._mediaHeight;
    this.resetMedia();
  }

  /*****************************************************************************
  **                               GETTERS                                    **
  *****************************************************************************/

  /**
   * @returns The rects array for the current frame
   */
  get _rects() {
    const frame = this.videoLoaded ? this._video.currentTime : 0;
    const datum = this._data[frame] || {
      rects: []
    };
    this._data[frame] = datum;
    return datum.rects;
  }

  /**
   * @returns Whether an image is loaded or not
   */
  get imageLoaded() {
    return this._image.src !== "";
  }

  /**
   * @returns The limits of the current media
   */
  get limits() {
    const [top, left] = this.mediaPosition;
    const [height, width] = this.mediaDimensions;
    const topLimit = Math.max(0, top);
    const leftLimit = Math.max(0, left);
    const bottomLimit = Math.min(this._viewerHeight, top + height);
    const rightLimit = Math.min(this._viewerWidth, top + width);
    return { topLimit, bottomLimit, leftLimit, rightLimit };
  }

  /**
   * @returns An array [top, left] representing the media's position
   */
  get mediaDimensions() {
    return [
      Number.parseInt(this._media.style.height.replace("px", "")),
      Number.parseInt(this._media.style.width.replace("px", ""))
    ];
  }

  /**
   * @returns An array [top, left] representing the media's position
   */
  get mediaPosition() {
    return [
      Number.parseInt(this._media.style.top.replace("px", "")),
      Number.parseInt(this._media.style.left.replace("px", ""))
    ];
  }

  /**
   * @returns Whether a video is loaded or not
   */
  get videoLoaded() {
    return this._video.src !== "";
  }

  /**
   * @returns A number describing the current aspect ratio of the viewer
   */
  get viewerAspectRatio() {
    return this._viewerWidth / this._viewerHeight;
  }

  /*****************************************************************************
  **                               SETTERS                                    **
  *****************************************************************************/

  /**
   * @param {Number[]} dim The desired dimensions of the media
   * @param {Number} dim[].height The desired height of the media
   * @param {Number} dim[].width The desired width of the media
   */
  set mediaDimensions([height, width]) {
    utils.setElementDimensions(height, width, this._media);
    utils.setElementDimensions(height, width, this._image);
    utils.setElementDimensions(height, width, this._video);
  }

  /**
   * @param {Number[]} dim The desired dimensions of the media
   * @param {Number} dim[].height The desired height of the media
   * @param {Number} dim[].width The desired width of the media
   */
  set mediaPosition([top, left]) {
    utils.setElementPosition(top, left, this._media);
  }
};
