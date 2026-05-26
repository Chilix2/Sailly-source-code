/**
 * Audio Worklet for PCM16 capture at 16kHz
 * Sends 320-sample chunks with 4-byte chunk ID prefix
 */

class PCM16Processor extends AudioWorkletProcessor {
    constructor() {
        super();
        this._chunkCount = 0;
        this._buffer = [];
        this._CHUNK_SIZE = 320; // 20ms at 16kHz
    }

    process(inputs, outputs, parameters) {
        const input = inputs[0];
        if (input.length === 0) return true;

        const channel = input[0];

        // Convert float32 to int16 and buffer
        for (let i = 0; i < channel.length; i++) {
            const s = Math.max(-1, Math.min(1, channel[i]));
            this._buffer.push(s < 0 ? s * 0x8000 : s * 0x7FFF);
        }

        // Send when we have enough samples
        while (this._buffer.length >= this._CHUNK_SIZE) {
            const chunk = this._buffer.splice(0, this._CHUNK_SIZE);
            const pcmData = new Int16Array(chunk);
            const uint8 = new Uint8Array(pcmData.buffer);

            this.port.postMessage({
                type: "audio",
                chunkId: this._chunkCount++,
                data: uint8,
            });
        }

        return true;
    }
}

registerProcessor("pcm16-processor", PCM16Processor);
