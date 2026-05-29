class PCM16Processor extends AudioWorkletProcessor {
  constructor() {
    super();
    this._buf = [];
    this._len = 0;
    this._chunkCount = 0;
  }
  process(inputs) {
    const channel = inputs[0]?.[0];
    if (channel && channel.length > 0) {
      for (let i = 0; i < channel.length; i++) {
        this._buf.push(channel[i]);
        this._len++;
      }
      if (this._len >= 320) {
        const pcm = new Int16Array(this._len);
        for (let i = 0; i < this._len; i++) {
          const c = Math.max(-1, Math.min(1, this._buf[i]));
          pcm[i] = c < 0 ? c * 32768 : c * 32767;
        }
        const chunkId = this._chunkCount % 1000000;
        this._chunkCount++;
        const wrapper = new ArrayBuffer(4 + pcm.buffer.byteLength);
        const view = new DataView(wrapper);
        view.setUint32(0, chunkId, true);
        new Uint8Array(wrapper, 4).set(new Uint8Array(pcm.buffer));
        this.port.postMessage(wrapper, [wrapper]);
        this._buf = [];
        this._len = 0;
      }
    }
    return true;
  }
}
registerProcessor('pcm16-processor', PCM16Processor);
