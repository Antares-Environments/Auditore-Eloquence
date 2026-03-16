// static/js/audio_processor.js
let audioContext;
let processor;
let workletUrl;

// Inline the AudioWorklet logic to ensure background processing for the Prototype
const workletCode = `
class PCMProcessor extends AudioWorkletProcessor {
    process(inputs, outputs, parameters) {
        const input = inputs[0];
        if (!input || !input[0]) return true;
        
        const float32Array = input[0];
        const int16Array = new Int16Array(float32Array.length);
        
        for (let i = 0; i < float32Array.length; i++) {
            let s = Math.max(-1, Math.min(1, float32Array[i]));
            int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }
        
        // Transfer the PCM buffer directly back to the main thread
        this.port.postMessage(int16Array.buffer, [int16Array.buffer]);
        return true;
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