/**
 * Simple clamp function
 * @param {Number} val The value to clamp
 * @param {Number} min The minimum val is allowed to be
 * @param {Number} max The maximum val is allowed to be
 * @returns val clamped to min and max
 */
export const clamp = (val, min, max) => Math.max(min, Math.min(max, val));

/**
 * Formats a time in frames to a timestamp of the form HH:MM:SS:FF
 * @param {Number} timeInFrames The total number of frames
 * @param {Number} frameRate The framerate that the frames will be played at
 * @returns An array of time parts starting with hours
 */
export const formatTimeInFrames = (timeInFrames, frameRate) => {
  const timeInSeconds = Math.floor(timeInFrames / frameRate);
  const frames = timeInFrames % frameRate;
  const timeInMinutes = Math.floor(timeInSeconds / 60);
  const seconds = timeInSeconds % 60;
  const hours = Math.floor(timeInMinutes / 60);
  const minutes = timeInMinutes % 60;
  return [hours, minutes, seconds, frames];
};

/**
 * Formats a time in seconds to a timestamp of the form HH:MM:SS
 * @param {Number} timeInFrames The total number of frames
 * @returns An array of time parts starting with hours
 */
export const formatTimeInSeconds = (timeInSeconds) => {
  const timeInMinutes = Math.floor(timeInSeconds / 60);
  const seconds = timeInSeconds % 60;
  const hours = Math.floor(timeInMinutes / 60);
  const minutes = timeInMinutes % 60;
  return [hours, minutes, seconds];
};

/**
 * Sets a collection of styles on the passed DOM element
 * @param {Object} attrs A dictionary of styles to set on the element
 * @param {HTMLElement} element The DOM element to modify
 */
const setElementStyles = (styles, element) => {
  for (const k in styles) {
    element.style[k] = styles[k];
  }
};

/**
 * Sets the height and width of an element via CSS styles
 * @param {Number} height The desired height of the element
 * @param {Number} width The desired width of the element
 * @param {HTMLElement} element The element to modify
 */
export const setElementDimensions = (height, width, element) => setElementStyles({
  height: `${height}px`,
  width: `${width}px`
}, element);


/**
 * Sets the position of an element via CSS top and left properties
 * @param {Number} top The desired top position of the element
 * @param {Number} left The desired left position of the element
 * @param {HTMLElement} element The element to modify
 */
export const setElementPosition = (top, left, element) => setElementStyles({
  top: `${top}px`,
  left: `${left}px`
}, element);
