/**
 * Sailly Browser Demo Client
 * - Capture microphone audio as PCM16 16kHz
 * - Send 4-byte chunk ID + PCM data over WebSocket
 * - Receive PCM24 audio, play via AudioContext
 * - Display transcript
 * - Echo gate: reduce mic gain while bot is speaking
 * - Interrupt: space bar or speaking over bot stops playback
 */

class DemoBrowser {
    constructor() {
        this.ws = null;
        this.isConnected = false;
        this.callActive = false;
        this.callSidStorageKey = "saillyDemoCallSid";

        // Audio contexts
        this.recordingCtx = null;
        this.playbackCtx = null;
        this.worklet = null;
        this.micGainNode = null;     // Gate: reduces mic during bot speech
        this.mediaStream = null;

        // Bot speaking state
        this.isBotSpeaking = false;
        this.activeAudioSources = []; // Track for interrupt support
        this.botSpeakingTimer = null; // Debounce to detect end of speech

        // UI elements
        this.callBtn = document.getElementById("call-btn");
        this.transcript = document.getElementById("transcript");
        this.statusEl = document.getElementById("call-status");
        this.statusInd = document.getElementById("status-indicator");
        this.errorBox = document.getElementById("error");
        this.interruptHint = null;   // Injected dynamically

        // Event listeners
        this.callBtn.addEventListener("click", () => this.toggleCall());

        // Space bar interrupt
        document.addEventListener("keydown", (e) => {
            if (e.code === "Space" && this.isBotSpeaking && this.callActive) {
                e.preventDefault();
                this.interruptBot("space_key");
            }
        });
    }

    async init() {
        try {
            // Create audio contexts
            this.recordingCtx = new AudioContext({ sampleRate: 16000 });
            this.playbackCtx = new AudioContext({ sampleRate: 24000 });

            // Load worklet for PCM capture
            await this.recordingCtx.audioWorklet.addModule("/static/worklet.js");
            const workletNode = new AudioWorkletNode(this.recordingCtx, "pcm16-processor");

            // Echo gate: gain node between mic and worklet
            this.micGainNode = this.recordingCtx.createGain();
            this.micGainNode.gain.value = 1.0;
            this.micGainNode.connect(workletNode);
            workletNode.connect(this.recordingCtx.destination);

            this.worklet = workletNode;

            // Inject interrupt hint element
            this._injectInterruptHint();

            this.showStatus("Bereit", "inactive");
        } catch (err) {
            this.showError(`Initialization error: ${err.message}`);
        }
    }

    _injectInterruptHint() {
        const hint = document.createElement("div");
        hint.id = "interrupt-hint";
        hint.style.cssText = `
            display: none;
            position: fixed;
            bottom: 80px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(0,0,0,0.75);
            color: #fff;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 13px;
            z-index: 999;
            pointer-events: none;
            white-space: nowrap;
        `;
        hint.textContent = "🎙️ LEERTASTE drücken zum Unterbrechen";
        document.body.appendChild(hint);
        this.interruptHint = hint;
    }

    async toggleCall() {
        if (this.callActive) {
            await this.endCall();
        } else {
            await this.startCall();
        }
    }

    async startCall() {
        try {
            this.showStatus("Verbindung wird hergestellt...", "connecting");
            this.callBtn.disabled = true;

            // Request microphone
            try {
                this.mediaStream = await navigator.mediaDevices.getUserMedia({
                    audio: { echoCancellation: true, noiseSuppression: true },
                });
            } catch (err) {
                this.showError(`Mikrophone error: ${err.message}`);
                return;
            }

            // Connect mic → echo gate → worklet
            const source = this.recordingCtx.createMediaStreamSource(this.mediaStream);
            source.connect(this.micGainNode);

            // Connect WebSocket
            const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
            const wsUrl = `${protocol}//${window.location.host}/ws/demo`;
            this.ws = new WebSocket(wsUrl);

            this.ws.binaryType = "arraybuffer";
            this.ws.onopen = () => this.onWsOpen();
            this.ws.onmessage = (evt) => this.onWsMessage(evt);
            this.ws.onerror = (evt) => this.onWsError(evt);
            this.ws.onclose = () => this.onWsClose();

            this.worklet.port.onmessage = (evt) => this.onWorkletMessage(evt);
        } catch (err) {
            this.showError(`Start error: ${err.message}`);
            this.callBtn.disabled = false;
        }
    }

    async onWsOpen() {
        this.isConnected = true;
        this.showStatus("Anruf läuft", "active");
        this.callBtn.textContent = "📞 Anruf beenden";
        this.callBtn.classList.remove("start");
        this.callBtn.classList.add("end");
        this.callBtn.disabled = false;
        this.callActive = true;

        // Send handshake. Reuse call_sid after transient reconnects so one
        // logical browser call stays attached to one server-side transcript.
        const savedCallSid = sessionStorage.getItem(this.callSidStorageKey);
        this.ws.send(JSON.stringify({ tenant: "doboo", voice: "Kore", call_sid: savedCallSid }));
    }

    onWsMessage(evt) {
        if (evt.data instanceof ArrayBuffer) {
            // Binary: PCM24 audio for playback — bot is speaking
            this._onBotAudioReceived(new Uint8Array(evt.data));
        } else {
            // Text: JSON messages
            try {
                const msg = JSON.parse(evt.data);
                if (msg.type === "session_init" && msg.call_sid) {
                    sessionStorage.setItem(this.callSidStorageKey, msg.call_sid);
                } else if (msg.type === "transcript") {
                    this.addTranscript(msg.role, msg.text);
                }
            } catch (e) {
                console.warn("Non-JSON message:", evt.data);
            }
        }
    }

    onWsError(evt) {
        console.error("WebSocket error:", evt);
        this.showError("WebSocket error");
    }

    onWsClose() {
        this.isConnected = false;
        this.callActive = false;
        this.callBtn.textContent = "📞 Anruf starten";
        this.callBtn.classList.remove("end");
        this.callBtn.classList.add("start");
        this.callBtn.disabled = false;
        this.showStatus("Anruf beendet", "inactive");
        this._setBotSpeaking(false);
    }

    onWorkletMessage(evt) {
        const { type, chunkId, data } = evt.data;
        if (type === "audio" && this.ws && this.isConnected) {
            // Prepend 4-byte chunk ID to audio
            const header = new Uint8Array(4);
            new DataView(header.buffer).setUint32(0, chunkId, true);
            const combined = new Uint8Array(header.length + data.length);
            combined.set(header);
            combined.set(data, header.length);
            this.ws.send(combined);
        }
    }

    _onBotAudioReceived(pcmData) {
        this._setBotSpeaking(true);
        this.playAudio(pcmData);

        // Reset speaking timer — bot speaking ends 600ms after last audio chunk
        if (this.botSpeakingTimer) clearTimeout(this.botSpeakingTimer);
        this.botSpeakingTimer = setTimeout(() => {
            this._setBotSpeaking(false);
        }, 600);
    }

    _setBotSpeaking(speaking) {
        this.isBotSpeaking = speaking;

        if (speaking) {
            // Reduce mic gain to 0.05 to prevent echo feedback
            if (this.micGainNode) {
                this.micGainNode.gain.setTargetAtTime(0.05, this.recordingCtx.currentTime, 0.1);
            }
            if (this.interruptHint) this.interruptHint.style.display = "block";
            this.showStatus("Bot spricht... (LEERTASTE: unterbrechen)", "active");
        } else {
            // Restore mic gain
            if (this.micGainNode) {
                this.micGainNode.gain.setTargetAtTime(1.0, this.recordingCtx.currentTime, 0.1);
            }
            if (this.interruptHint) this.interruptHint.style.display = "none";
            if (this.callActive) this.showStatus("Anruf läuft", "active");
        }
    }

    interruptBot(reason) {
        console.log(`[Interrupt] Bot interrupted by: ${reason}`);

        // Stop all active audio sources
        for (const src of this.activeAudioSources) {
            try { src.stop(); } catch (_) {}
        }
        this.activeAudioSources = [];

        // Clear speaking state immediately
        if (this.botSpeakingTimer) clearTimeout(this.botSpeakingTimer);
        this._setBotSpeaking(false);

        // Notify server (optional — server will process next user turn naturally)
        if (this.ws && this.isConnected) {
            try {
                this.ws.send(JSON.stringify({ type: "interrupt" }));
            } catch (_) {}
        }
    }

    playAudio(pcmData) {
        if (!this.playbackCtx) return;

        // Convert byte array to float32
        const int16Array = new Int16Array(pcmData.buffer);
        const float32Array = new Float32Array(int16Array.length);
        for (let i = 0; i < int16Array.length; i++) {
            float32Array[i] = int16Array[i] / 32768.0;
        }

        // Create audio buffer and play
        const audioBuffer = this.playbackCtx.createAudioBuffer(
            1,
            float32Array.length,
            24000
        );
        audioBuffer.getChannelData(0).set(float32Array);

        const source = this.playbackCtx.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(this.playbackCtx.destination);

        // Track source for interrupt support
        this.activeAudioSources.push(source);
        source.onended = () => {
            const idx = this.activeAudioSources.indexOf(source);
            if (idx !== -1) this.activeAudioSources.splice(idx, 1);
        };

        source.start();
    }

    async endCall() {
        sessionStorage.removeItem(this.callSidStorageKey);
        this.callActive = false;
        this._setBotSpeaking(false);
        this.showStatus("Beendet", "inactive");

        if (this.ws) {
            this.ws.close();
        }

        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach((track) => track.stop());
        }

        this.callBtn.disabled = false;
        this.callBtn.textContent = "📞 Anruf starten";
        this.callBtn.classList.remove("end");
        this.callBtn.classList.add("start");
    }

    addTranscript(role, text) {
        const transcriptEmpty = this.transcript.querySelector(".transcript-empty");
        if (transcriptEmpty) {
            transcriptEmpty.remove();
        }

        // If bot just started a new transcript entry, also interrupt any playing audio
        if (role === "bot" && this.isBotSpeaking) {
            // Bot sent new text while still playing — that's expected (streaming)
        } else if (role === "user" && this.isBotSpeaking) {
            // User is talking while bot is speaking — interrupt bot
            this.interruptBot("user_speech");
        }

        const msgDiv = document.createElement("div");
        msgDiv.classList.add("transcript-message", role);

        const bubble = document.createElement("div");
        bubble.classList.add("transcript-bubble");
        bubble.textContent = text;

        const label = document.createElement("div");
        label.classList.add("transcript-label");
        label.textContent = role === "user" ? "Du" : "Sailly";

        msgDiv.appendChild(bubble);
        msgDiv.appendChild(label);
        this.transcript.appendChild(msgDiv);

        // Scroll to bottom
        this.transcript.scrollTop = this.transcript.scrollHeight;
    }

    showStatus(text, state) {
        this.statusEl.textContent = text;
        if (state === "active") {
            this.statusInd.classList.add("active");
        } else {
            this.statusInd.classList.remove("active");
        }
    }

    showError(message) {
        this.errorBox.textContent = `❌ ${message}`;
        this.errorBox.style.display = "block";
        setTimeout(() => {
            this.errorBox.style.display = "none";
        }, 5000);
    }
}

// Initialize when ready
window.addEventListener("DOMContentLoaded", async () => {
    const demo = new DemoBrowser();
    await demo.init();
});
