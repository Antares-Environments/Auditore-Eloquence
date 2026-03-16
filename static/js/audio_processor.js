// static/js/audio_processor.js
let audioContext;
let processor;

export async function startAudioCapture(webSocket, mediaStream) {
    try {
        if (!audioContext) {
            // Initialize AudioContext at 16kHz explicitly inside user action stack
            audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
        }
        
        // Browsers might suspend it initially
        if (audioContext.state === 'suspended') {
            await audioContext.resume();
        }

        const source = audioContext.createMediaStreamSource(mediaStream);
        
        // 1024 buffer size significantly drops encoding latency from ~250ms down to ~64ms for real-time live capabilities.
        processor = audioContext.createScriptProcessor(1024, 1, 1);
        
        source.connect(processor);
        processor.connect(audioContext.destination);
        
        processor.onaudioprocess = (e) => {
            // Drop processing if socket is not ready to avoid local buffering memory leaks
            if (!webSocket || webSocket.readyState !== WebSocket.OPEN) return;
            
            const inputData = e.inputBuffer.getChannelData(0);
            const pcmData = convertFloat32ToInt16(inputData);
            
            try {
                webSocket.send(pcmData);
            } catch (wsError) {
                console.warn("Failed to send audio chunk to socket:", wsError);
            }
        };
        
        console.log("Audio capture started: Raw PCM streaming active.");
        
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

// Helper function to convert browser's native Float32 audio to 16-bit PCM
function convertFloat32ToInt16(float32Array) {
    let int16Array = new Int16Array(float32Array.length);
    for (let i = 0; i < float32Array.length; i++) {
        // Clamp the values to prevent clipping distortion
        let s = Math.max(-1, Math.min(1, float32Array[i]));
        int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }
    return int16Array.buffer;
}