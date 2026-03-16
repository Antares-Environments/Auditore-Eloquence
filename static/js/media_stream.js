// static/js/media_stream.js
import { startAudioCapture, stopAudioCapture } from './audio_processor.js';

document.addEventListener("DOMContentLoaded", () => {
  const sessionToggle = document.getElementById("session-toggle");
  const statusIndicator = document.getElementById("status-indicator");
  const videoFeed = document.getElementById("video-feed");
  const donutContainer = document.getElementById("donut-container");
  const centerText = document.getElementById("donut-center-text");
  const templateDetails = document.getElementById("template-details");
  
  const idlePanel = document.getElementById("idle-panel");
  const activeSessionPanel = document.getElementById("active-session-panel");
  const eventLog = document.getElementById("live-event-log");

  let socket;
  let activeStream;
  let selectedTemplate = "";
  let templateData = window.TEMPLATE_DATA || {};
  let isSessionActive = false;

  // Globally expose hover interaction functions for SVG inline handlers
  window.hoverRingItem = function(selectedId, categoryLabel) {
    const slice = document.getElementById('slice-' + selectedId);
    if (slice) {
        slice.classList.add("hover");
    }
    const centerNode = document.getElementById("donut-center-text");
    if (centerNode) {
        centerNode.textContent = categoryLabel;
    }
  };

  window.resetRingItem = function(selectedId) {
    const slice = document.getElementById('slice-' + selectedId);
    if (slice) {
        slice.classList.remove("hover");
    }
    const centerNode = document.getElementById("donut-center-text");
    if (centerNode) {
        centerNode.textContent = selectedTemplate ? selectedTemplate : "SELECT TEMPLATE";
    }
  };

  window.clickRingItem = function(selectedId, categoryLabel) {
    document.querySelectorAll(".donut-slice").forEach(p => {
        p.classList.remove("selected", "hover");
    });
    
    const activeSlice = document.getElementById('slice-' + selectedId);
    if (activeSlice) {
        activeSlice.classList.add("selected");
    }
    
    selectedTemplate = categoryLabel;
    
    const centerNode = document.getElementById("donut-center-text");
    if (centerNode) {
        centerNode.textContent = categoryLabel;
        centerNode.style.borderColor = "var(--element-olive)";
    }
    
    const detailsNode = document.getElementById("template-details");
    if (detailsNode) {
        detailsNode.style.display = "block";
        detailsNode.textContent = templateData[categoryLabel]?.description || "Template configuration loaded.";
    }
  };

  function logEvent(message) {
    const time = new Date().toLocaleTimeString();
    const entry = document.createElement("div");
    entry.textContent = `[${time}] ${message}`;
    eventLog.appendChild(entry);
    eventLog.scrollTop = eventLog.scrollHeight; 
  }

  let playbackContext;
  let nextPlaybackTime = 0;
  let activeAudioNodes = [];

  window.stopAgentAudio = function() {
    activeAudioNodes.forEach(source => {
        try { source.stop(); } catch(e) {}
    });
    activeAudioNodes = [];
    if (playbackContext) {
        nextPlaybackTime = playbackContext.currentTime;
    }
  };

  async function startSession() {
    try {
      if (!selectedTemplate) {
        statusIndicator.className = "orange";
        statusIndicator.textContent = "SELECT TEMPLATE FIRST";
        return;
      }

      isSessionActive = true;
      sessionToggle.textContent = "TERMINATE SESSION";
      idlePanel.style.display = "none";
      activeSessionPanel.style.display = "flex";
      eventLog.innerHTML = ""; 
      logEvent(`Initializing protocol: ${selectedTemplate}...`);

      const requiresVideo = templateData[selectedTemplate]?.requires_video_audit || false;
      const requiresScreen = selectedTemplate === "Demo Video" || templateData[selectedTemplate]?.requires_screen_audit || false;
      
      let audioConstraints = { echoCancellation: true, noiseSuppression: true, autoGainControl: true };

      if (requiresScreen) {
          logEvent("Screen Modality requested. Awaiting user permission...");
          const screenStream = await navigator.mediaDevices.getDisplayMedia({ video: true });
          const micStream = await navigator.mediaDevices.getUserMedia({ audio: audioConstraints });
          
          activeStream = new MediaStream([
              ...screenStream.getVideoTracks(),
              ...micStream.getAudioTracks()
          ]);

          screenStream.getVideoTracks()[0].onended = () => {
              logEvent("Screen share terminated by user.");
              if (isSessionActive) terminateSessionUI();
          };
      } else {
          activeStream = await navigator.mediaDevices.getUserMedia({ 
              video: requiresVideo, 
              audio: audioConstraints 
          });
      }

      videoFeed.srcObject = activeStream;
      videoFeed.play();
      
      // We no longer lock the mic with isCharonSpeaking, enabling full-duplex barge-in
      window.isCharonSpeaking = false;
      
      logEvent(`Template Config: Visual Auditing is ${requiresVideo || requiresScreen ? "ENABLED" : "DISABLED"}`);

      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const wsUrl = `${protocol}//${window.location.host}/stream?template=${encodeURIComponent(selectedTemplate)}`;
      socket = new WebSocket(wsUrl);

      socket.onopen = () => {
        logEvent("Secure socket established with backend engine.");
        
        try {
          startAudioCapture(socket, activeStream);

          // Client-Side VAD for Instant Barge-In
          window.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
          const analyser = window.audioCtx.createAnalyser();
          const micSource = window.audioCtx.createMediaStreamSource(activeStream);
          micSource.connect(analyser);
          analyser.fftSize = 256;
          const dataArray = new Uint8Array(analyser.frequencyBinCount);

          window.vadInterval = setInterval(() => {
              if (activeAudioNodes.length === 0) return; // Only trigger if agent is actively speaking
              
              analyser.getByteFrequencyData(dataArray);
              let sum = 0;
              for(let i = 0; i < dataArray.length; i++) sum += dataArray[i];
              let avg = sum / dataArray.length;
              
              if (avg > 35) { // Threshold for user speech detection
                  logEvent("[BARGE-IN] User speech detected. Halting agent audio.");
                  window.stopAgentAudio();
                  if (socket.readyState === WebSocket.OPEN) {
                      socket.send(JSON.stringify({ "client_event": "barge_in" }));
                  }
              }
          }, 50);

          if (requiresVideo || requiresScreen) {
              const canvas = document.createElement("canvas");
              const ctx = canvas.getContext("2d");
              
              window.videoAuditInterval = setInterval(() => {
                  if (socket.readyState === WebSocket.OPEN && videoFeed.readyState === videoFeed.HAVE_ENOUGH_DATA) {
                      canvas.width = 640;
                      canvas.height = 480;
                      ctx.drawImage(videoFeed, 0, 0, canvas.width, canvas.height);
                      const base64Frame = canvas.toDataURL("image/jpeg", 0.7);
                      socket.send(JSON.stringify({ "video_frame": base64Frame }));
                  }
              }, 2000); 
          }

          statusIndicator.className = "green";
          statusIndicator.textContent = `ACTIVE: ${selectedTemplate}`;
        } catch (mediaError) {
          logEvent(`[ERROR] Audio engine failed: ${mediaError.message}`);
          statusIndicator.className = "red";
          statusIndicator.textContent = "AUDIO CODEC REJECTED";
        }
      };

      socket.onmessage = async (event) => {
        if (event.data instanceof Blob) {
            if (!playbackContext) {
                playbackContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 24000 });
            }
            if (playbackContext.state === 'suspended') {
                await playbackContext.resume();
            }

            const arrayBuffer = await event.data.arrayBuffer();
            const int16Array = new Int16Array(arrayBuffer);
            const float32Array = new Float32Array(int16Array.length);
            
            for (let i = 0; i < int16Array.length; i++) {
                float32Array[i] = int16Array[i] / 32768.0;
            }

            const audioBuffer = playbackContext.createBuffer(1, float32Array.length, 24000);
            audioBuffer.getChannelData(0).set(float32Array);

            const source = playbackContext.createBufferSource();
            source.buffer = audioBuffer;
            source.connect(playbackContext.destination);

            source.onended = () => {
                const idx = activeAudioNodes.indexOf(source);
                if (idx > -1) activeAudioNodes.splice(idx, 1);
            };
            activeAudioNodes.push(source);

            const currentTime = playbackContext.currentTime;
            if (nextPlaybackTime < currentTime) {
                nextPlaybackTime = currentTime + 0.01;
            }
            
            source.start(nextPlaybackTime);
            nextPlaybackTime += audioBuffer.duration;
            return;
        }

        const data = JSON.parse(event.data);
        
        if (data.system_event) {
          if (data.system_event === "interrupted" || data.system_event === "flush") {
              window.stopAgentAudio();
              return;
          }
          // Simplify logs for Neat Transparency
          logEvent(`[SYSTEM] ${data.system_event}`);
          return;
        }

        if (data.indicator && !data.async_results) {
          logEvent(`[SYSTEM 1: LIVE] ${data.message}`);
          statusIndicator.className = data.indicator;
          statusIndicator.textContent = data.message;
        }
        
        if (data.async_results) {
          if (data.async_results.pacing) {
            const pace = data.async_results.pacing;
            if (pace.indicator !== "green" && pace.indicator !== "white") {
              logEvent(`[PACING METRICS] ${pace.message}`);
            }
            statusIndicator.className = pace.indicator;
            statusIndicator.textContent = pace.message;
          }
          
          if (data.async_results.council && Array.isArray(data.async_results.council)) {
            data.async_results.council.forEach(evalResult => {
                if (evalResult && evalResult.message) {
                    logEvent(`[SYSTEM 2: COUNCIL] ${evalResult.message}`);
                    if (evalResult.indicator !== "green") {
                        statusIndicator.className = evalResult.indicator;
                        statusIndicator.textContent = evalResult.message;
                    }
                }
            });
          }
        }
      };

      socket.onclose = (e) => {
        logEvent(`Socket disconnected.`);
        if(e.code !== 1000 && e.code !== 1001) {
             statusIndicator.className = "red";
             statusIndicator.textContent = "CONNECTION LOST";
        }
        terminateSessionUI();
      };

      socket.onerror = (error) => {
        logEvent("CRITICAL ERROR: Connection to backend failed.");
        statusIndicator.className = "red";
        statusIndicator.textContent = "ENGINE FAULT";
        terminateSessionUI();
      };

    } catch (error) {
      statusIndicator.className = "red";
      statusIndicator.textContent = "SYSTEM FAULT (SEE CONSOLE)";
      logEvent("CRITICAL ERROR: Media access denied or system crash.");
      terminateSessionUI();
    }
  }

  function terminateSessionUI() {
    isSessionActive = false;
    sessionToggle.textContent = "START SESSION";
    statusIndicator.className = "white";
    statusIndicator.textContent = "SYSTEM IDLE";
    idlePanel.style.display = "flex";
    activeSessionPanel.style.display = "none";

    stopAudioCapture();
    window.stopAgentAudio();
    
    if (window.vadInterval) {
        clearInterval(window.vadInterval);
        window.vadInterval = null;
    }
    if (window.audioCtx) {
        window.audioCtx.close();
        window.audioCtx = null;
    }
    if (window.videoAuditInterval) {
        clearInterval(window.videoAuditInterval);
        window.videoAuditInterval = null;
    }
    
    if (socket && socket.readyState === WebSocket.OPEN) socket.close();
    if (activeStream) {
      activeStream.getTracks().forEach(track => track.stop());
      videoFeed.srcObject = null;
    }
  }

  sessionToggle.addEventListener("click", () => {
    if (isSessionActive) {
      logEvent("Manual termination initiated...");
      terminateSessionUI();
    } else {
      startSession();
    }
  });
});