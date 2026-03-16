// static/js/audio_processor.js
let audioContext;
let processor;
let workletUrl;

// Inline the AudioWorklet logic with a 2048-frame chunking buffer
const workletCode = `
class PCMProcessor extends AudioWorkletProcessor {
    constructor() {
        super();
        this.buffer = new Float32Array(2048);
        this.offset = 0;
    }
    process(inputs, outputs, parameters) {
        const input = inputs[0];
        if (!input || !input[0]) return true;
        
        const channelData = input[0];
        for (let i = 0; i < channelData.length; i++) {
            this.buffer[this.offset++] = channelData[i];
            
            // Only flush to the main thread when the 2048 buffer is full
            if (this.offset >= 2048) {
                this.flush();
                this.offset = 0;
            }
        }
        return true;
    }
    flush() {
        const int16Array = new Int16Array(2048);
        for (let i = 0; i < 2048; i++) {
            let s = Math.max(-1, Math.min(1, this.buffer[i]));
            int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }
        this.port.postMessage(int16Array.buffer, [int16Array.buffer]);
    }
}
registerProcessor('pcm-processor', PCMProcessor);
`;

export async function startAudioCapture(webSocket, mediaStream) {
    try {
        if (!audioContext) {
            audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
        }
        
        if (audioContext.state === 'suspended') {
            await audioContext.resume();
        }

        const source = audioContext.createMediaStreamSource(mediaStream);
        
        if (!workletUrl) {
            const blob = new Blob([workletCode], { type: 'application/javascript' });
            workletUrl = URL.createObjectURL(blob);
        }
        
        await audioContext.audioWorklet.addModule(workletUrl);
        
        processor = new AudioWorkletNode(audioContext, 'pcm-processor');
        
        processor.port.onmessage = (e) => {
            if (!webSocket || webSocket.readyState !== WebSocket.OPEN) return;
            try {
                webSocket.send(e.data);
            } catch (wsError) {
                console.warn("Failed to send audio chunk to socket:", wsError);
            }
        };
        
        source.connect(processor);
        processor.connect(audioContext.destination);
        
        console.log("Audio capture started: AudioWorklet PCM streaming active.");
        
    } catch (error) {
        console.error("Error setting up audio processor:", error);
    }
}

export function stopAudioCapture() {
    if (processor) {
        processor.disconnect();
        processor = null;
    }
    if (audioContext && audioContext.state !== 'closed') {
        audioContext.close();
        audioContext = null;
    }
    console.log("Audio capture stopped.");
}