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
  if (e.ctrlKey) {
    switch(e.key) {
      // Reset zoom if CTRL+1 is pressed
      case "1":
        e.preventDefault();
        e.stopPropagation();
        viewer.resetMedia();
        break;
    }
  } else {
    const videoPlayer = viewer.videoPlayer;
    switch(e.key) {
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
      case " ":
        e.preventDefault();
        e.stopPropagation();
        viewer.panStart();
        break;
    }
  }
};

/*******************************************************************************
**                               LISTENERS                                    **
*******************************************************************************/
document.addEventListener("DOMContentLoaded", init);
