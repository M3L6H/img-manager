export default class Pool {
  /**
   * Construct a new pool
   * @param {Function} initFn Factory function to create a new item
   * @param {Function} freeFn Function called to free an item
   * @param {Function} reuseFn Function called to reuse a previously freed item
   */
  constructor(initFn, freeFn, reuseFn) {
    this._freeFn = freeFn;
    this._initFn = initFn;
    this._reuseFn = reuseFn;

    this._id = 0;
    this._free = [];
    this._used = {};
  }

  /**
   * Creates a new item if necessary, but prioritizes reusing old, unused ones instead
   * @returns An item from the pool
   */
  getOne() {
    let theOne;

    if (this._free.length > 0) {
      theOne = this._free.pop();
      this._reuseFn(theOne.item);
    } else {
      theOne = {
        id: this._id,
        item: this._initFn(this._id)
      };
      ++this._id;
    }

    this._used[theOne.id] = theOne.item;

    return theOne;
  }

  /**
   * Called to free an item when it is no longer in use
   * @param {Number} id The id of the item to free
   */
  freeOne(id) {
    const theOne = this._used[id];
    if (!theOne) {
      return;
    }
    this._freeFn(theOne);
    this._free.push({
      id,
      item: theOne
    });
    delete this._used[id];
  }

  /**
   * Called to free all the currently in-use items
   */
  freeAll() {
    for (const id in this._used) {
      const item = this._used[id];
      this._freeFn(item);
      this._free.push({
        id,
        item
      });
    }
    this._used = {};
  }

  /**
   * @returns The currently active members of the pool
   */
  get active() {
    return Object.values(this._used);
  }
}
