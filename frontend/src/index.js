import Viewer from "./viewer.js";

let viewer;

const init = () => {
  viewer = new Viewer();

  // Initialize event listeners
  document.addEventListener("keydown", shortcutsHandler, false);
  document.addEventListener("keyup", keyUpHandler);
};

/*******************************************************************************
**                                HANDLERS                                    **
*******************************************************************************/

/**
 * Handles global key releases
 * @param {KeyboardEvent} e
 */
const keyUpHandler = (e) => {
  switch (e.key) {
    case " ":
      e.preventDefault();
      e.stopPropagation();
      viewer.panStop();
      break;
  }
}

/**
 * Handles global shortcuts
 * @param {KeyboardEvent} e
 */
const shortcutsHandler = (e) => {
  const player = viewer.videoPlayer;

  if (e.ctrlKey && e.shiftKey) {
    switch (e.key) {
      case "ArrowLeft":
        e.preventDefault();
        e.stopPropagation();
        player.seekTo(Math.floor(player.currentTime) - 1);
        break;
      case "ArrowRight":
        e.preventDefault();
        e.stopPropagation();
        player.seekTo(Math.floor(player.currentTime) + 1);
        break;
    }
  } else if (e.ctrlKey) {
    switch (e.key) {
      // Reset zoom if CTRL+1 is pressed
      case "1":
        e.preventDefault();
        e.stopPropagation();
        viewer.resetMedia();
        break;
      case "ArrowLeft":
        e.preventDefault();
        e.stopPropagation();
        player.seekTo((Math.floor(player.currentTime / 60) - 1) * 60);
        break;
      case "ArrowRight":
        e.preventDefault();
        e.stopPropagation();
        player.seekTo((Math.floor(player.currentTime / 60) + 1) * 60);
        break;
    }
  } else if (e.shiftKey) {
    switch (e.key) {
      case "ArrowLeft":
        player.seekTo(player.currentTime, -1);
        break;
      case "ArrowRight":
        player.seekTo(player.currentTime, 1);
        break;
    }
  } else {
    const videoPlayer = viewer.videoPlayer;
    switch (e.key) {
      case "ArrowLeft":
        player.seekTo((Math.floor(player.currentTime / 5) - 1) * 5);
        break;
      case "ArrowRight":
        player.seekTo((Math.floor(player.currentTime / 5) + 1) * 5);
        break;
      case "Escape":
        e.preventDefault();
        e.stopPropagation();
        viewer.cancelRect();
        break;
      case "f":
        viewer.toggleFullScreen();
        break;
      case "k":
        videoPlayer.togglePlay();
        if (videoPlayer.paused) {
          videoPlayer.showControls();
        } else {
          setTimeout(() => videoPlayer.hideControls(), 2000);
        }
        break;
      case "m":
        videoPlayer.toggleMute();
        break;
      case "r":
        viewer.createRect();
        break;
      case " ":
        e.preventDefault();
        e.stopPropagation();
        viewer.panStart();
        break;
      default:
        console.log(e.key);
    }
  }
};

/*******************************************************************************
**                               LISTENERS                                    **
*******************************************************************************/
document.addEventListener("DOMContentLoaded", init);
